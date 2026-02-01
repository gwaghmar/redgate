"""Database connection helper for SQL Server.
Supports SQL login, Windows integrated, and Microsoft Entra with Chrome launcher.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pyodbc
import msal

from utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseConnection:
    def __init__(
        self,
        server: str,
        database: str,
        auth_type: str,
        username: str | None = None,
        password: str | None = None,
        encrypt: bool = True,
        trust_cert: bool = False,
        driver: str = "ODBC Driver 18 for SQL Server",
    ) -> None:
        self.server = server
        self.database = database
        self.auth_type = auth_type.lower()
        self.username = username
        self.password = password
        self.encrypt = encrypt
        self.trust_cert = trust_cert
        self.driver = driver
        self.client_id = "04b07795-8ddb-461a-bbee-02f9e1bf7b46"
        self.scope = ["https://database.windows.net/.default"]
        self.chrome_path = self._find_chrome()
        self.token_cache_path = Path.home() / ".sql_compare_token_cache.bin"

    def _conn_str(self) -> str:
        # Normalise server value to prefer TCP, matching SSMS/Azure guidance.
        server = (self.server or "").strip()
        if not server:
            raise ValueError("Server name cannot be empty")
        
        # Basic validation: prevent obviously invalid server names
        import re
        if re.search(r'[;<>"\\]', server):
            raise ValueError(f"Invalid characters in server name: {server}")
        
        if server and not server.lower().startswith(("tcp:", "np:")):
            # Prefix with tcp: so the driver uses TCP directly instead of
            # falling back to Named Pipes, which can cause 53 errors on
            # Azure SQL / Synapse even when SSMS works.
            server = f"tcp:{server}"

        parts = [
            f"Driver={{{self.driver}}};",
            f"Server={server};",
            f"Database={self.database};",
        ]
        if self.encrypt:
            parts.append("Encrypt=yes;")
        else:
            parts.append("Encrypt=no;")
        parts.append(f"TrustServerCertificate={'yes' if self.trust_cert else 'no'};")

        # For Entra with access token, do NOT specify Authentication in connection string
        # Token is passed via attrs_before only
        if self.auth_type == "windows":
            parts.append("Trusted_Connection=yes;")
        elif self.auth_type == "sql":
            if self.username:
                parts.append(f"UID={self.username};")
            if self.password:
                parts.append(f"PWD={self.password};")
        # entra: no auth keywords in connection string
        return "".join(parts)

    def test_connection(self, timeout: int = 5) -> tuple[bool, str]:
        try:
            logger.info(f"Testing connection to {self.server}/{self.database} using {self.auth_type} auth")
            if self.auth_type == "entra":
                token = self._acquire_token()
                conn_str = self._conn_str()
                with pyodbc.connect(conn_str, attrs_before={1256: token}, timeout=timeout, autocommit=True):
                    logger.info("Connection test succeeded")
                    return True, "Connection succeeded"
            else:
                conn_str = self._conn_str()
                with pyodbc.connect(conn_str, timeout=timeout, autocommit=True):
                    logger.info("Connection test succeeded")
                    return True, "Connection succeeded"
        except Exception as exc:
            logger.error(f"Connection test failed: {exc}", exc_info=True)
            return False, str(exc)

    def execute_query(self, query: str, timeout: int = 300) -> list[tuple]:
        if self.auth_type == "entra":
            token = self._acquire_token()
            conn_str = self._conn_str()
            with pyodbc.connect(conn_str, attrs_before={1256: token}, timeout=timeout, autocommit=True) as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                return cursor.fetchall()
        else:
            conn_str = self._conn_str()
            with pyodbc.connect(conn_str, timeout=timeout, autocommit=True) as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                return cursor.fetchall()

    def _acquire_token(self) -> bytes:
        cache = msal.SerializableTokenCache()
        if self.token_cache_path.exists():
            cache.deserialize(self.token_cache_path.read_text())

        app = msal.PublicClientApplication(
            self.client_id,
            authority="https://login.microsoftonline.com/common",
            token_cache=cache
        )

        # Set Chrome as browser if available
        if self.chrome_path:
            os.environ["BROWSER"] = str(self.chrome_path)

        accounts = app.get_accounts(username=self.username) if self.username else app.get_accounts()
        result = None
        if accounts:
            result = app.acquire_token_silent(self.scope, account=accounts[0])

        if not result:
            result = app.acquire_token_interactive(
                scopes=self.scope,
                login_hint=self.username,
                parent_window_handle=None
            )

        if cache.has_state_changed:
            self.token_cache_path.write_text(cache.serialize())

        if not result or "access_token" not in result:
            error_desc = result.get("error_description", "Unknown error") if result else "No result"
            raise RuntimeError(f"Token acquisition failed: {error_desc}")

        # Encode token as required by SQL_COPT_SS_ACCESS_TOKEN (ACCESSTOKEN struct)
        token_str = result["access_token"]
        # Token must be UTF-16LE encoded (each ASCII byte followed by zero)
        token_utf16 = token_str.encode("utf-16-le")
        # Prepend 4-byte length (DWORD) in little-endian
        token_length = len(token_utf16)
        token_bytes = token_length.to_bytes(4, byteorder="little") + token_utf16
        return token_bytes

    @staticmethod
    def _find_chrome() -> Path | None:
        candidates = [
            Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
        ]
        for path in candidates:
            if path.exists():
                return path
        return None
