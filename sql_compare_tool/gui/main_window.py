from __future__ import annotations

import json

import customtkinter as ctk
from tkinter import messagebox, filedialog
from tkinter import ttk
from pathlib import Path

from core.database import DatabaseConnection
from core.metadata_extractor import MetadataExtractor
from core.comparator import SchemaComparator
from core.diff_generator import DiffGenerator
from core.script_generator import ScriptGenerator
from core.snapshot import load_snapshot, save_snapshot
from utils.report_generator import export_csv, export_html, export_json, export_excel, export_pdf
from utils.project_manager import ProjectManager
from utils.sql_parser import load_script_folder
from cache_manager import CacheManager


AUTH_CHOICES = ["SQL Login", "Windows", "Entra MFA"]
CONFIG_FILE = Path("config") / "connection_history.json"


class ConnectionPanel(ctk.CTkFrame):
    def __init__(self, master, title: str):
        super().__init__(master, fg_color="transparent")
        self.columnconfigure(1, weight=1)

        header_font = ctk.CTkFont(size=18, weight="bold")
        label_font = ctk.CTkFont(size=13)

        self.title_label = ctk.CTkLabel(self, text=title, font=header_font)
        self.title_label.grid(row=0, column=0, columnspan=2, pady=(0, 8), sticky="w")

        # Server dropdown with history
        ctk.CTkLabel(self, text="Server", font=label_font).grid(row=1, column=0, sticky="e", padx=6, pady=4)
        server_frame = ctk.CTkFrame(self, fg_color="transparent")
        server_frame.grid(row=1, column=1, sticky="ew", padx=6, pady=4)
        server_frame.grid_columnconfigure(0, weight=1)
        
        self.server_var = ctk.StringVar()
        self.server_combo = ctk.CTkComboBox(
            server_frame,
            variable=self.server_var,
            values=self._load_server_history(),
            width=260,
            command=self._on_server_changed
        )
        self.server_combo.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ctk.CTkButton(server_frame, text="↻", width=40, command=self._refresh_databases).grid(row=0, column=1)

        # Database dropdown (auto-populated)
        ctk.CTkLabel(self, text="Database", font=label_font).grid(row=2, column=0, sticky="e", padx=6, pady=4)
        self.database_var = ctk.StringVar()
        self.database_combo = ctk.CTkComboBox(self, variable=self.database_var, values=[], width=260)
        self.database_combo.grid(row=2, column=1, sticky="ew", padx=6, pady=4)

        ctk.CTkLabel(self, text="Auth type", font=label_font).grid(row=3, column=0, sticky="e", padx=6, pady=4)
        self.auth_var = ctk.StringVar(value=AUTH_CHOICES[2])  # Default to "Entra MFA"
        self.auth_menu = ctk.CTkOptionMenu(self, values=AUTH_CHOICES, variable=self.auth_var, command=self._auth_changed)
        self.auth_menu.grid(row=3, column=1, sticky="w", padx=6, pady=4)

        ctk.CTkLabel(self, text="Username", font=label_font).grid(row=4, column=0, sticky="e", padx=6, pady=4)
        self.username_entry = ctk.CTkEntry(self, width=260)
        self.username_entry.grid(row=4, column=1, sticky="ew", padx=6, pady=4)

        ctk.CTkLabel(self, text="Password", font=label_font).grid(row=5, column=0, sticky="e", padx=6, pady=4)
        self.password_entry = ctk.CTkEntry(self, width=260, show="*")
        self.password_entry.grid(row=5, column=1, sticky="ew", padx=6, pady=4)

        # Source type: Database vs Scripts folder
        ctk.CTkLabel(self, text="Source type", font=label_font).grid(row=6, column=0, sticky="e", padx=6, pady=4)
        self.source_type_var = ctk.StringVar(value="Database")
        self.source_type_menu = ctk.CTkOptionMenu(
            self,
            values=["Database", "Scripts folder", "Snapshot"],
            variable=self.source_type_var,
            command=self._source_type_changed,
        )
        self.source_type_menu.grid(row=6, column=1, sticky="w", padx=6, pady=4)

        # Scripts folder selection row (only used when Source type = Scripts folder)
        self.folder_label = ctk.CTkLabel(self, text="Scripts folder", font=label_font)
        self.folder_label.grid(row=7, column=0, sticky="e", padx=6, pady=4)
        self.folder_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.folder_frame.grid(row=7, column=1, sticky="ew", padx=6, pady=4)
        self.folder_frame.grid_columnconfigure(0, weight=1)
        self.folder_entry = ctk.CTkEntry(self.folder_frame)
        self.folder_entry.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.folder_browse_btn = ctk.CTkButton(self.folder_frame, text="Browse...", width=90, command=self._browse_folder)
        self.folder_browse_btn.grid(row=0, column=1)

        self.test_btn = ctk.CTkButton(self, text="Test", command=self.test_connection)
        self.test_btn.grid(row=8, column=0, columnspan=2, pady=(10, 0))

        self.status_label = ctk.CTkLabel(self, text="")
        self.status_label.grid(row=9, column=0, columnspan=2, pady=6)

        self._auth_changed(self.auth_var.get())

    def _load_server_history(self) -> list[str]:
        """Load server history from config file."""
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    return data.get("servers", [])
        except Exception:
            pass
        return []

    def _save_server_to_history(self, server: str) -> None:
        """Add server to history and save to config."""
        if not server or not server.strip():
            return
        
        server = server.strip()
        history = self._load_server_history()
        
        # Add to front if not already there
        if server in history:
            history.remove(server)
        history.insert(0, server)
        
        # Keep only last 20
        history = history[:20]
        
        try:
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w") as f:
                json.dump({"servers": history}, f, indent=2)
            
            # Update dropdown
            self.server_combo.configure(values=history)
        except Exception as e:
            print(f"Failed to save server history: {e}")

    def _on_server_changed(self, choice: str) -> None:
        """Called when server selection changes."""
        # Auto-refresh databases when server changes
        if choice and choice.strip() and self.source_type_var.get().lower() == "database":
            self.after(100, self._refresh_databases)

    def _refresh_databases(self) -> None:
        """Fetch list of databases from selected server."""
        server = self.server_var.get().strip()
        if not server or self.source_type_var.get().lower() != "database":
            return
        
        try:
            # Save server to history
            self._save_server_to_history(server)
            
            # Build connection to master database
            auth_map = {
                "sql login": "sql",
                "windows": "windows",
                "entra mfa": "entra",
            }
            auth_type = auth_map[self.auth_var.get().lower()]
            
            conn = DatabaseConnection(
                server=server,
                database="master",
                auth_type=auth_type,
                username=self.username_entry.get().strip() or None,
                password=self.password_entry.get() if auth_type == "sql" else None,
            )
            
            # Query for databases
            query = "SELECT name FROM sys.databases WHERE state = 0 ORDER BY name"
            result = conn.execute_query(query)
            
            if result:
                db_names = [row[0] for row in result]
                self.database_combo.configure(values=db_names)
                
                # Auto-select first if none selected
                if not self.database_var.get() and db_names:
                    self.database_combo.set(db_names[0])
            else:
                messagebox.showinfo("Databases", "No databases found or unable to retrieve list.")
                
        except Exception as e:
            messagebox.showerror("Database List", f"Failed to retrieve databases:\n{str(e)}")

    def _source_type_changed(self, choice: str) -> None:
        choice_lower = choice.lower()
        if choice_lower == "database":
            # Enable database fields and disable file/folder selection
            self.server_combo.configure(state="normal")
            self.database_combo.configure(state="normal")
            self.auth_menu.configure(state="normal")
            self._auth_changed(self.auth_var.get())
            self.folder_entry.configure(state="disabled")
            self.folder_browse_btn.configure(state="disabled")
            self.folder_label.configure(text="Scripts folder")
            self.test_btn.configure(state="normal")
        elif choice_lower == "scripts folder":
            # Scripts folder mode: disable database-related fields
            self.server_combo.configure(state="disabled")
            self.database_combo.configure(state="disabled")
            self.auth_menu.configure(state="disabled")
            self.username_entry.configure(state="disabled")
            self.password_entry.configure(state="disabled")
            self.folder_entry.configure(state="normal")
            self.folder_browse_btn.configure(state="normal")
            self.folder_label.configure(text="Scripts folder")
            self.test_btn.configure(state="disabled")
        else:
            # Snapshot mode: choose a .snp (or JSON) file
            self.server_combo.configure(state="disabled")
            self.database_combo.configure(state="disabled")
            self.auth_menu.configure(state="disabled")
            self.username_entry.configure(state="disabled")
            self.password_entry.configure(state="disabled")
            self.folder_entry.configure(state="normal")
            self.folder_browse_btn.configure(state="normal")
            self.folder_label.configure(text="Snapshot file")
            self.test_btn.configure(state="disabled")

    def _auth_changed(self, choice: str) -> None:
        choice_lower = choice.lower()
        if choice_lower == "sql login":
            self.username_entry.configure(state="normal")
            self.password_entry.configure(state="normal")
        elif choice_lower == "windows":
            self.username_entry.configure(state="disabled")
            self.password_entry.configure(state="disabled")
        else:  # Entra MFA
            self.username_entry.configure(state="normal")
            self.password_entry.configure(state="disabled")

        # In scripts-folder mode, username/password stay disabled
        if self.source_type_var.get().lower() != "database":
            self.username_entry.configure(state="disabled")
            self.password_entry.configure(state="disabled")

    def _build_conn(self) -> DatabaseConnection:
        # Only valid when source type is Database
        auth_map = {
            "sql login": "sql",
            "windows": "windows",
            "entra mfa": "entra",
        }
        auth_type = auth_map[self.auth_var.get().lower()]
        return DatabaseConnection(
            server=self.server_var.get().strip(),
            database=self.database_var.get().strip(),
            auth_type=auth_type,
            username=self.username_entry.get().strip() or None,
            password=self.password_entry.get() if auth_type == "sql" else None,
        )

    def _browse_folder(self) -> None:
        mode = self.source_type_var.get().lower()
        if mode == "scripts folder":
            folder = filedialog.askdirectory(title="Select scripts folder")
            if folder:
                self.folder_entry.delete(0, "end")
                self.folder_entry.insert(0, folder)
        elif mode == "snapshot":
            file_path = filedialog.askopenfilename(
                title="Select snapshot file",
                filetypes=[("Snapshot Files", "*.snp"), ("JSON Files", "*.json"), ("All Files", "*.*")],
            )
            if file_path:
                self.folder_entry.delete(0, "end")
                self.folder_entry.insert(0, file_path)

    def test_connection(self) -> None:
        if self.source_type_var.get().lower() != "database":
            messagebox.showinfo("Connection", "Test is only available for database sources.")
            return

        # Save server to history on successful test
        server = self.server_var.get().strip()
        if server:
            self._save_server_to_history(server)

        conn = self._build_conn()
        ok, msg = conn.test_connection()
        self.status_label.configure(text=msg, text_color="green" if ok else "red")
        if ok:
            messagebox.showinfo("Connection", msg)
        else:
            messagebox.showerror("Connection failed", msg)

    def get_params(self) -> dict:
        return {
            "server": self.server_var.get().strip(),
            "database": self.database_var.get().strip(),
            "auth": self.auth_var.get(),
            "username": self.username_entry.get().strip(),
            "password": self.password_entry.get(),
            "source_type": self.source_type_var.get(),
            "scripts_folder": self.folder_entry.get().strip(),
        }

    def get_source_type(self) -> str:
        return self.source_type_var.get()

    def get_scripts_folder(self) -> str:
        return self.folder_entry.get().strip()

    def get_snapshot_path(self) -> str:
        return self.folder_entry.get().strip()


class MainWindow(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("SQL Compare Tool")
        # Larger default size for comfortable layout and diff viewing
        self.geometry("1600x900")
        self.minsize(1400, 750)
        # Start maximized for best experience
        self.state('zoomed')

        # Root uses a single cell that hosts the main tab view
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Modern professional color scheme
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        
        # Configure custom colors for better aesthetics
        self.configure(fg_color=("#F5F6FA", "#1E1E2E"))  # Soft blue-gray background
        
        # Main area is split into two tabs: Setup and Results
        self.main_tabs = ctk.CTkTabview(self)
        self.main_tabs.grid(row=0, column=0, padx=8, pady=8, sticky="nsew")

        self.setup_tab = self.main_tabs.add("Setup")
        self.results_tab = self.main_tabs.add("Results")

        # --- Setup tab: connections and compare controls ---
        self.setup_tab.grid_columnconfigure(0, weight=1)
        self.setup_tab.grid_columnconfigure(1, weight=1)

        self.source_panel = ConnectionPanel(self.setup_tab, "Source")
        self.source_panel.grid(row=0, column=0, padx=12, pady=12, sticky="nsew")

        self.target_panel = ConnectionPanel(self.setup_tab, "Target")
        self.target_panel.grid(row=0, column=1, padx=12, pady=12, sticky="nsew")

        filter_panel = ctk.CTkFrame(self.setup_tab, fg_color="transparent")
        filter_panel.grid(row=1, column=0, columnspan=2, padx=12, pady=(0, 6), sticky="ew")
        ctk.CTkLabel(filter_panel, text="Schema filter (optional):").grid(row=0, column=0, padx=6)
        self.schema_filter_entry = ctk.CTkEntry(filter_panel, width=200, placeholder_text="e.g., dbo")
        self.schema_filter_entry.grid(row=0, column=1, padx=6)

        self.compare_btn = ctk.CTkButton(self.setup_tab, text="Compare", command=self.compare_schemas)
        self.compare_btn.grid(row=2, column=0, columnspan=2, pady=(0, 6))

        self.progress_label = ctk.CTkLabel(self.setup_tab, text="", font=ctk.CTkFont(size=11))
        self.progress_label.grid(row=3, column=0, columnspan=2, pady=(0, 12))

        # Core state used across the results UI
        self._last_results = None
        self._last_source_metadata = None
        self._last_target_db = None
        self._tree_data = []
        self._show_identical = ctk.BooleanVar(value=True)
        self._show_diff = ctk.BooleanVar(value=True)
        self._show_missing_tgt = ctk.BooleanVar(value=True)
        self._show_missing_src = ctk.BooleanVar(value=True)
        self._name_filter = ctk.StringVar(value="")
        self._project_mgr = ProjectManager()
        self._current_diff_text = ""
        self._compare_options = {
            "ignore_users": False,
            "ignore_roles": False,
            "ignore_schemas": False,
            "ignore_extended_properties": False,
            "ignore_indexes": False,
            "ignore_triggers": False,
        }
        self._custom_filters: list[dict] = []
        self._deploy_options = {
            "wrap_in_transaction": True,
            "include_drop_phase": True,
            "include_table_phase": True,
            "include_constraint_phase": True,
            "include_programmability_phase": True,
            "include_misc_phase": True,
            "include_rollback_section": True,
        }

        # Cache manager for storing and retrieving comparison data
        self.cache_manager = CacheManager()

        # --- Results tab: projects, options, exports, grid and diff ---
        self.results_tab.grid_columnconfigure(0, weight=1)

        proj_frame = ctk.CTkFrame(self.results_tab, fg_color="transparent")
        proj_frame.grid(row=0, column=0, pady=(0, 4), padx=12, sticky="ew")
        proj_frame.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkButton(proj_frame, text="Save Project", height=26, command=self.save_project).grid(row=0, column=0, padx=4, sticky="ew")
        ctk.CTkButton(proj_frame, text="Load Project", height=26, command=self.load_project).grid(row=0, column=1, padx=4, sticky="ew")
        ctk.CTkButton(proj_frame, text="Save Source Snapshot", height=26, command=self.save_source_snapshot).grid(row=0, column=2, padx=4, sticky="ew")
        
        # Separator line
        ctk.CTkFrame(self.results_tab, height=2, fg_color=("#BDC3C7", "#34495E")).grid(row=1, column=0, sticky="ew", padx=12, pady=(4, 8))

        options_frame = ctk.CTkFrame(self.results_tab, fg_color="transparent")
        options_frame.grid(row=2, column=0, pady=(0, 4), padx=12, sticky="e")
        options_frame.grid_columnconfigure((0, 1, 2), weight=0)
        ctk.CTkButton(options_frame, text="Options", width=90, height=26, command=self.open_options_dialog).grid(row=0, column=0, padx=4, sticky="e")
        ctk.CTkButton(options_frame, text="Filters", width=90, height=26, command=self.open_filter_dialog).grid(row=0, column=1, padx=4, sticky="e")
        ctk.CTkButton(options_frame, text="Deploy Options", width=110, height=26, command=self.open_deploy_options_dialog).grid(row=0, column=2, padx=4, sticky="e")

        # Script/deploy actions specific to the current comparison
        actions_frame = ctk.CTkFrame(self.results_tab, fg_color="transparent")
        actions_frame.grid(row=3, column=0, pady=(0, 4), padx=12, sticky="w")
        self.script_btn = ctk.CTkButton(actions_frame, text="Preview Script", height=26, command=self.preview_script)
        self.script_btn.grid(row=0, column=0, padx=4, pady=0)
        self.deploy_btn = ctk.CTkButton(actions_frame, text="Deployment Wizard", height=26, command=self.open_deploy_wizard)
        self.deploy_btn.grid(row=0, column=1, padx=4, pady=0)

        export_frame = ctk.CTkFrame(self.results_tab, fg_color="transparent")
        export_frame.grid(row=4, column=0, pady=(0, 4), padx=12, sticky="ew")
        export_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)
        self.export_csv_btn = ctk.CTkButton(export_frame, text="Export CSV", height=26, command=self.export_csv_report)
        self.export_csv_btn.grid(row=0, column=0, padx=4, pady=0, sticky="ew")
        self.export_html_btn = ctk.CTkButton(export_frame, text="Export HTML", height=26, command=self.export_html_report)
        self.export_html_btn.grid(row=0, column=1, padx=4, pady=0, sticky="ew")
        self.export_json_btn = ctk.CTkButton(export_frame, text="Export JSON", height=26, command=self.export_json_report)
        self.export_json_btn.grid(row=0, column=2, padx=4, pady=0, sticky="ew")
        self.export_xlsx_btn = ctk.CTkButton(export_frame, text="Export Excel", height=26, command=self.export_excel_report)
        self.export_xlsx_btn.grid(row=0, column=3, padx=4, pady=0, sticky="ew")
        self.export_pdf_btn = ctk.CTkButton(export_frame, text="Export PDF", height=26, command=self.export_pdf_report)
        self.export_pdf_btn.grid(row=0, column=4, padx=4, pady=0, sticky="ew")
        
        # Separator line
        ctk.CTkFrame(self.results_tab, height=2, fg_color=("#BDC3C7", "#34495E")).grid(row=5, column=0, sticky="ew", padx=12, pady=(4, 8))

        # Summary banner for last comparison - larger and more prominent
        summary_frame = ctk.CTkFrame(self.results_tab, fg_color=("#ECF0F1", "#2C3E50"), corner_radius=8)
        summary_frame.grid(row=6, column=0, sticky="ew", padx=12, pady=(0, 8))
        
        self.results_summary_label = ctk.CTkLabel(
            summary_frame,
            text="Run Compare to see a summary of differences.",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=("#2C3E50", "#ECF0F1"),
            anchor="w",
            justify="left",
        )
        self.results_summary_label.pack(fill="both", expand=True, padx=16, pady=12)
        
        # Separator line
        ctk.CTkFrame(self.results_tab, height=2, fg_color=("#BDC3C7", "#34495E")).grid(row=7, column=0, sticky="ew", padx=12, pady=(0, 8))

        # Full-width results grid - no split panel
        grid_container = ctk.CTkFrame(self.results_tab, fg_color="transparent")
        grid_container.grid(row=8, column=0, sticky="nsew", padx=12, pady=(0, 8))
        self.results_tab.grid_rowconfigure(8, weight=1)
        grid_container.grid_rowconfigure(0, weight=1)
        grid_container.grid_columnconfigure(0, weight=1)

        # Results grid takes the full space
        self._build_results_grid(grid_container)

    def compare_schemas(self) -> None:
        try:
            # Disable buttons during compare
            self.compare_btn.configure(state="disabled")
            self.script_btn.configure(state="disabled")
            self.deploy_btn.configure(state="disabled")
            self.export_csv_btn.configure(state="disabled")
            self.export_html_btn.configure(state="disabled")
            self.export_json_btn.configure(state="disabled")
            self.export_xlsx_btn.configure(state="disabled")
            self.export_pdf_btn.configure(state="disabled")

            src_type = self.source_panel.get_source_type().lower()
            tgt_type = self.target_panel.get_source_type().lower()

            schema_filter = self.schema_filter_entry.get().strip() or None

            def update_progress(msg: str):
                self.progress_label.configure(text=msg)
                self.update_idletasks()

            def load_metadata_from_panel(panel: ConnectionPanel, kind: str):
                source_type = panel.get_source_type().lower()
                if source_type == "database":
                    update_progress(f"Connecting to {kind} database...")
                    conn = panel._build_conn()
                    return MetadataExtractor(conn).extract(
                        progress_callback=update_progress,
                        schema_filter=schema_filter,
                    )
                elif source_type == "scripts folder":
                    folder = panel.get_scripts_folder()
                    if not folder:
                        raise ValueError(f"No scripts folder selected for {kind}.")
                    update_progress(f"Loading scripts for {kind} from {folder}...")
                    meta = load_script_folder(folder)
                    # Apply schema filter (if any) by pruning object names
                    if schema_filter:
                        prefix = schema_filter.lower() + "."

                        def _prune(obj_dict: dict):
                            for name in list(obj_dict.keys()):
                                if not str(name).lower().startswith(prefix):
                                    obj_dict.pop(name, None)

                        for key in ["tables", "views", "procedures", "functions", "triggers", "synonyms"]:
                            d = meta.get(key)
                            if isinstance(d, dict):
                                _prune(d)
                    return meta
                elif source_type == "snapshot":
                    snap_path = panel.get_snapshot_path()
                    if not snap_path:
                        raise ValueError(f"No snapshot file selected for {kind}.")
                    update_progress(f"Loading snapshot for {kind} from {snap_path}...")
                    return load_snapshot(snap_path)
                else:
                    raise ValueError(f"Unsupported source type for {kind}: {source_type}")

            src_meta = load_metadata_from_panel(self.source_panel, "source")
            tgt_meta = load_metadata_from_panel(self.target_panel, "target")

            update_progress("Comparing schemas...")

            # Apply comparison options by pruning metadata for ignored object types
            if self._compare_options.get("ignore_users"):
                src_meta.pop("users", None)
                tgt_meta.pop("users", None)
            if self._compare_options.get("ignore_roles"):
                src_meta.pop("roles", None)
                tgt_meta.pop("roles", None)
            if self._compare_options.get("ignore_schemas"):
                src_meta.pop("schemas", None)
                tgt_meta.pop("schemas", None)
            if self._compare_options.get("ignore_extended_properties"):
                src_meta.pop("extended_properties", None)
                tgt_meta.pop("extended_properties", None)
            if self._compare_options.get("ignore_triggers"):
                src_meta.pop("triggers", None)
                tgt_meta.pop("triggers", None)
            if self._compare_options.get("ignore_indexes"):
                for tables in (src_meta.get("tables", {}), tgt_meta.get("tables", {})):
                    if not isinstance(tables, dict):
                        continue
                    for tbl in tables.values():
                        if isinstance(tbl, dict):
                            tbl.pop("indexes", None)

            comparator = SchemaComparator(src_meta, tgt_meta)
            results = comparator.compare()
            summary = comparator.summarize(results)
            self._last_results = results
            self._last_source_metadata = src_meta
            self._last_target_db = self.target_panel.database_var.get().strip()

            summary_text = (
                f"Identical: {summary['IDENTICAL']} | "
                f"Different: {summary['DIFFERENT']} | "
                f"Missing in target: {summary['MISSING_IN_TARGET']} | "
                f"Missing in source: {summary['MISSING_IN_SOURCE']}\n"
            )
            # Update summary banner on Results tab
            if hasattr(self, "results_summary_label"):
                self.results_summary_label.configure(text=summary_text.strip())

            self._populate_grid(results)
            
            update_progress("Compare complete!")
            # Automatically switch to the Results tab after a successful compare
            try:
                self.main_tabs.set("Results")
            except Exception:
                pass
        except Exception as exc:
            messagebox.showerror("Error", str(exc))
            self.progress_label.configure(text="Error during compare.")
        finally:
            # Re-enable buttons
            self.compare_btn.configure(state="normal")
            self.script_btn.configure(state="normal")
            self.deploy_btn.configure(state="normal")
            self.export_csv_btn.configure(state="normal")
            self.export_html_btn.configure(state="normal")
            self.export_json_btn.configure(state="normal")
            self.export_xlsx_btn.configure(state="normal")
            self.export_pdf_btn.configure(state="normal")

    def open_options_dialog(self) -> None:
        dialog = ctk.CTkToplevel(self)
        dialog.title("Comparison Options")
        dialog.geometry("420x260")
        dialog.grab_set()

        frame = ctk.CTkFrame(dialog)
        frame.pack(fill="both", expand=True, padx=12, pady=12)
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            frame,
            text="Select which object categories to ignore during comparison.\n"
                 "Options are applied on the next Compare run.",
            justify="left",
        ).grid(row=0, column=0, sticky="w", padx=4, pady=(0, 8))

        ignore_users_var = ctk.BooleanVar(value=self._compare_options.get("ignore_users", False))
        ignore_roles_var = ctk.BooleanVar(value=self._compare_options.get("ignore_roles", False))
        ignore_schemas_var = ctk.BooleanVar(value=self._compare_options.get("ignore_schemas", False))
        ignore_extprops_var = ctk.BooleanVar(value=self._compare_options.get("ignore_extended_properties", False))
        ignore_triggers_var = ctk.BooleanVar(value=self._compare_options.get("ignore_triggers", False))
        ignore_indexes_var = ctk.BooleanVar(value=self._compare_options.get("ignore_indexes", False))

        row = 1
        ctk.CTkCheckBox(frame, text="Ignore users", variable=ignore_users_var).grid(row=row, column=0, sticky="w", pady=2)
        row += 1
        ctk.CTkCheckBox(frame, text="Ignore roles", variable=ignore_roles_var).grid(row=row, column=0, sticky="w", pady=2)
        row += 1
        ctk.CTkCheckBox(frame, text="Ignore schemas", variable=ignore_schemas_var).grid(row=row, column=0, sticky="w", pady=2)
        row += 1
        ctk.CTkCheckBox(frame, text="Ignore extended properties", variable=ignore_extprops_var).grid(row=row, column=0, sticky="w", pady=2)
        row += 1
        ctk.CTkCheckBox(frame, text="Ignore triggers", variable=ignore_triggers_var).grid(row=row, column=0, sticky="w", pady=2)
        row += 1
        ctk.CTkCheckBox(frame, text="Ignore table indexes (compare & scripts)", variable=ignore_indexes_var).grid(row=row, column=0, sticky="w", pady=2)

        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.grid(row=row + 1, column=0, sticky="e", pady=(8, 0))

        def on_ok() -> None:
            self._compare_options["ignore_users"] = ignore_users_var.get()
            self._compare_options["ignore_roles"] = ignore_roles_var.get()
            self._compare_options["ignore_schemas"] = ignore_schemas_var.get()
            self._compare_options["ignore_extended_properties"] = ignore_extprops_var.get()
            self._compare_options["ignore_triggers"] = ignore_triggers_var.get()
            self._compare_options["ignore_indexes"] = ignore_indexes_var.get()
            dialog.destroy()

        def on_cancel() -> None:
            dialog.destroy()

        ctk.CTkButton(btn_frame, text="OK", width=80, command=on_ok).pack(side="right", padx=4)
        ctk.CTkButton(btn_frame, text="Cancel", width=80, command=on_cancel).pack(side="right", padx=4)

    def open_deploy_options_dialog(self) -> None:
        dialog = ctk.CTkToplevel(self)
        dialog.title("Deployment Options")
        dialog.geometry("460x280")
        dialog.grab_set()

        frame = ctk.CTkFrame(dialog)
        frame.pack(fill="both", expand=True, padx=12, pady=12)
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            frame,
            text=(
                "Configure how deployment scripts are generated.\n"
                "These options affect both Script Preview and the Deployment Wizard."
            ),
            justify="left",
        ).grid(row=0, column=0, sticky="w", padx=4, pady=(0, 8))

        wrap_tx_var = ctk.BooleanVar(value=self._deploy_options.get("wrap_in_transaction", True))
        drop_phase_var = ctk.BooleanVar(value=self._deploy_options.get("include_drop_phase", True))
        table_phase_var = ctk.BooleanVar(value=self._deploy_options.get("include_table_phase", True))
        constraint_phase_var = ctk.BooleanVar(value=self._deploy_options.get("include_constraint_phase", True))
        prog_phase_var = ctk.BooleanVar(value=self._deploy_options.get("include_programmability_phase", True))
        misc_phase_var = ctk.BooleanVar(value=self._deploy_options.get("include_misc_phase", True))
        rollback_var = ctk.BooleanVar(value=self._deploy_options.get("include_rollback_section", True))

        row = 1
        ctk.CTkCheckBox(frame, text="Wrap deployment in a transaction", variable=wrap_tx_var).grid(row=row, column=0, sticky="w", pady=2)
        row += 1
        ctk.CTkCheckBox(frame, text="Include DROP phase (objects missing in source)", variable=drop_phase_var).grid(row=row, column=0, sticky="w", pady=2)
        row += 1
        ctk.CTkCheckBox(frame, text="Include tables/columns phase", variable=table_phase_var).grid(row=row, column=0, sticky="w", pady=2)
        row += 1
        ctk.CTkCheckBox(frame, text="Include constraints/indexes phase", variable=constraint_phase_var).grid(row=row, column=0, sticky="w", pady=2)
        row += 1
        ctk.CTkCheckBox(frame, text="Include programmability phase (views/procs/functions/triggers)", variable=prog_phase_var).grid(row=row, column=0, sticky="w", pady=2)
        row += 1
        ctk.CTkCheckBox(frame, text="Include miscellaneous phase (synonyms, etc.)", variable=misc_phase_var).grid(row=row, column=0, sticky="w", pady=2)
        row += 1
        ctk.CTkCheckBox(frame, text="Append generated rollback script section", variable=rollback_var).grid(row=row, column=0, sticky="w", pady=2)

        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.grid(row=row + 1, column=0, sticky="e", pady=(8, 0))

        def on_ok() -> None:
            self._deploy_options["wrap_in_transaction"] = wrap_tx_var.get()
            self._deploy_options["include_drop_phase"] = drop_phase_var.get()
            self._deploy_options["include_table_phase"] = table_phase_var.get()
            self._deploy_options["include_constraint_phase"] = constraint_phase_var.get()
            self._deploy_options["include_programmability_phase"] = prog_phase_var.get()
            self._deploy_options["include_misc_phase"] = misc_phase_var.get()
            self._deploy_options["include_rollback_section"] = rollback_var.get()
            dialog.destroy()

        def on_cancel() -> None:
            dialog.destroy()

        ctk.CTkButton(btn_frame, text="OK", width=80, command=on_ok).pack(side="right", padx=4)
        ctk.CTkButton(btn_frame, text="Cancel", width=80, command=on_cancel).pack(side="right", padx=4)

    def preview_script(self) -> None:
        if not self._last_results or not self._last_target_db or not self._last_source_metadata:
            messagebox.showinfo("Info", "Run Compare first to generate a script preview.")
            return
        script = ScriptGenerator(
            self._last_results,
            self._last_source_metadata,
            self._last_target_db,
            deploy_options=self._deploy_options,
        ).generate()
        # Show script in a separate window
        self._show_script_window(script)
    
    def _show_script_window(self, script: str):
        """Show SQL script in a separate window."""
        window = ctk.CTkToplevel(self)
        window.title("Generated SQL Script")
        window.geometry("1000x700")
        window.transient(self)
        window.grab_set()
        
        # Script text area
        mono_font = ctk.CTkFont(family="Consolas", size=10)
        script_text = ctk.CTkTextbox(window, font=mono_font, wrap="none")
        script_text.pack(fill="both", expand=True, padx=12, pady=12)
        script_text.insert("1.0", script)
        script_text.configure(state="disabled")
        
        # Close button
        button_frame = ctk.CTkFrame(window, fg_color="transparent")
        button_frame.pack(fill="x", padx=12, pady=(0, 12))
        ctk.CTkButton(button_frame, text="Close", width=100, command=window.destroy).pack(side="right")

    def open_deploy_wizard(self) -> None:
        if not self._last_results or not self._last_target_db or not self._last_source_metadata:
            messagebox.showinfo("Info", "Run Compare first to open the deployment wizard.")
            return
        script = ScriptGenerator(
            self._last_results,
            self._last_source_metadata,
            self._last_target_db,
            deploy_options=self._deploy_options,
        ).generate()
        DeploymentWizard(self, self._last_results, script, self._last_target_db)

    def export_csv_report(self) -> None:
        if not self._last_results:
            messagebox.showinfo("Info", "Run Compare first to export.")
            return
        out_path = Path("exports") / "compare_results.csv"
        try:
            export_csv(self._last_results, out_path)
            messagebox.showinfo("Export", f"CSV saved to {out_path}")
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc))

    def export_html_report(self) -> None:
        if not self._last_results:
            messagebox.showinfo("Info", "Run Compare first to export.")
            return
        out_path = Path("exports") / "compare_results.html"
        try:
            export_html(self._last_results, out_path)
            messagebox.showinfo("Export", f"HTML saved to {out_path}")
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc))

    def export_json_report(self) -> None:
        if not self._last_results:
            messagebox.showinfo("Info", "Run Compare first to export.")
            return
        out_path = Path("exports") / "compare_results.json"
        try:
            export_json(self._last_results, out_path)
            messagebox.showinfo("Export", f"JSON saved to {out_path}")
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc))

    def export_excel_report(self) -> None:
        if not self._last_results:
            messagebox.showinfo("Info", "Run Compare first to export.")
            return
        out_path = Path("exports") / "compare_results.xlsx"
        try:
            export_excel(self._last_results, out_path)
            messagebox.showinfo("Export", f"Excel saved to {out_path}")
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc))

    def export_pdf_report(self) -> None:
        if not self._last_results:
            messagebox.showinfo("Info", "Run Compare first to export.")
            return
        out_path = Path("exports") / "compare_results.pdf"
        try:
            export_pdf(self._last_results, out_path)
            messagebox.showinfo("Export", f"PDF saved to {out_path}")
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc))

    def save_source_snapshot(self) -> None:
        """Save the last source metadata snapshot to a .snp file.

        Requires that a comparison has been run so that _last_source_metadata
        is populated. The snapshot can later be used as a source/target of
        type "Snapshot".
        """

        if self._last_source_metadata is None:
            messagebox.showinfo("Snapshot", "Run a comparison first to capture source metadata.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".snp",
            filetypes=[("Snapshot Files", "*.snp"), ("All Files", "*.*")],
            title="Save source snapshot",
        )
        if not file_path:
            return
        try:
            save_snapshot(Path(file_path), self._last_source_metadata)
            messagebox.showinfo("Snapshot", f"Source snapshot saved to {file_path}")
        except Exception as exc:
            messagebox.showerror("Snapshot", str(exc))

    def open_filter_dialog(self) -> None:
        dialog = ctk.CTkToplevel(self)
        dialog.title("Custom Filters")
        dialog.geometry("520x380")
        dialog.grab_set()

        frame = ctk.CTkFrame(dialog)
        frame.pack(fill="both", expand=True, padx=12, pady=12)
        frame.grid_rowconfigure(2, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            frame,
            text=(
                "Define additional filters for the results grid.\n"
                "Mode: include = keep matches, exclude = hide matches.\n"
                "Field: apply filter to name, schema, type, or status."
            ),
            justify="left",
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        tree = ttk.Treeview(frame, columns=("mode", "field", "pattern"), show="headings", height=6)
        tree.heading("mode", text="Mode")
        tree.heading("field", text="Field")
        tree.heading("pattern", text="Pattern")
        tree.column("mode", width=80, anchor="w")
        tree.column("field", width=90, anchor="w")
        tree.column("pattern", width=300, anchor="w")
        tree.grid(row=2, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=2, column=1, sticky="ns")

        def refresh_tree() -> None:
            for row in tree.get_children():
                tree.delete(row)
            for filt in self._custom_filters:
                mode = (filt.get("mode") or "include").lower()
                field = (filt.get("field") or "name").lower()
                pattern = filt.get("pattern") or ""
                tree.insert("", "end", values=(mode.title(), field.title(), pattern))

        refresh_tree()

        controls = ctk.CTkFrame(frame, fg_color="transparent")
        controls.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        controls.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(controls, text="Pattern:").grid(row=0, column=0, padx=(0, 6))
        pattern_var = ctk.StringVar(value="")
        pattern_entry = ctk.CTkEntry(controls, textvariable=pattern_var)
        pattern_entry.grid(row=0, column=1, sticky="ew", padx=(0, 6))

        mode_var = ctk.StringVar(value="include")
        mode_menu = ctk.CTkOptionMenu(controls, values=["include", "exclude"], variable=mode_var, width=110)
        mode_menu.grid(row=0, column=2, padx=(0, 6))

        field_var = ctk.StringVar(value="name")
        field_menu = ctk.CTkOptionMenu(controls, values=["name", "schema", "type", "status"], variable=field_var, width=110)
        field_menu.grid(row=0, column=3, padx=(0, 6))

        def add_filter() -> None:
            pattern = pattern_var.get().strip()
            if not pattern:
                messagebox.showinfo("Custom Filters", "Enter a pattern before adding a filter.")
                return
            mode = (mode_var.get() or "include").lower()
            field = (field_var.get() or "name").lower()
            self._custom_filters.append({"mode": mode, "field": field, "pattern": pattern})
            pattern_var.set("")
            refresh_tree()
            if self._last_results:
                self._refresh_grid()

        def remove_selected() -> None:
            selected = tree.selection()
            if not selected:
                return
            for item_id in selected:
                values = tree.item(item_id, "values")
                if not values:
                    continue
                mode_label = str(values[0]).strip().lower()
                field_label = str(values[1]).strip().lower()
                pattern_text = str(values[2])
                idx = next(
                    (i for i, f in enumerate(self._custom_filters)
                     if (f.get("mode") or "include").lower() == mode_label
                     and (f.get("field") or "name").lower() == field_label
                     and str(f.get("pattern")) == pattern_text),
                    None,
                )
                if idx is not None:
                    self._custom_filters.pop(idx)
            refresh_tree()
            if self._last_results:
                self._refresh_grid()

        def clear_all() -> None:
            if not self._custom_filters:
                return
            self._custom_filters = []
            refresh_tree()
            if self._last_results:
                self._refresh_grid()

        btns = ctk.CTkFrame(frame, fg_color="transparent")
        btns.grid(row=3, column=0, columnspan=2, sticky="e", pady=(8, 0))

        ctk.CTkButton(controls, text="Add filter", width=90, command=add_filter).grid(row=0, column=3, padx=(0, 4))
        ctk.CTkButton(controls, text="Remove selected", width=120, command=remove_selected).grid(row=0, column=4, padx=(0, 4))
        ctk.CTkButton(controls, text="Clear all", width=80, command=clear_all).grid(row=0, column=5, padx=(0, 0))

        def close_dialog() -> None:
            dialog.destroy()

        ctk.CTkButton(btns, text="Close", width=80, command=close_dialog).pack(side="right", padx=4)

    def save_project(self) -> None:
        params = {
            "source": self.source_panel.get_params(),
            "target": self.target_panel.get_params(),
            "filters": {
                "show_identical": self._show_identical.get(),
                "show_diff": self._show_diff.get(),
                "show_missing_target": self._show_missing_tgt.get(),
                "show_missing_source": self._show_missing_src.get(),
                "name_contains": self._name_filter.get(),
                # Comparison options
                "ignore_users": self._compare_options.get("ignore_users", False),
                "ignore_roles": self._compare_options.get("ignore_roles", False),
                "ignore_schemas": self._compare_options.get("ignore_schemas", False),
                "ignore_extended_properties": self._compare_options.get("ignore_extended_properties", False),
                "ignore_triggers": self._compare_options.get("ignore_triggers", False),
                "ignore_indexes": self._compare_options.get("ignore_indexes", False),
                # Deployment options
                "deploy_wrap_in_transaction": self._deploy_options.get("wrap_in_transaction", True),
                "deploy_include_drop_phase": self._deploy_options.get("include_drop_phase", True),
                "deploy_include_table_phase": self._deploy_options.get("include_table_phase", True),
                "deploy_include_constraint_phase": self._deploy_options.get("include_constraint_phase", True),
                "deploy_include_programmability_phase": self._deploy_options.get("include_programmability_phase", True),
                "deploy_include_misc_phase": self._deploy_options.get("include_misc_phase", True),
                "deploy_include_rollback_section": self._deploy_options.get("include_rollback_section", True),
                # Custom filters (stored as JSON string)
                "custom_filters": json.dumps(self._custom_filters or []),
            },
        }
        file_path = filedialog.asksaveasfilename(defaultextension=".xml", filetypes=[("Project Files", "*.xml"), ("All Files", "*.*")])
        if not file_path:
            return
        try:
            self._project_mgr.save(params, Path(file_path))
            messagebox.showinfo("Project", f"Saved to {file_path}")
        except Exception as exc:
            messagebox.showerror("Save failed", str(exc))

    def load_project(self) -> None:
        file_path = filedialog.askopenfilename(filetypes=[("Project Files", "*.xml"), ("All Files", "*.*")])
        if not file_path:
            return
        try:
            data = self._project_mgr.load(Path(file_path))
        except Exception as exc:
            messagebox.showerror("Load failed", str(exc))
            return

        src = data.get("source", {})
        tgt = data.get("target", {})
        self.source_panel.server_var.set(src.get("server", ""))
        self.source_panel.database_var.set(src.get("database", ""))
        self.source_panel.auth_var.set(src.get("auth", AUTH_CHOICES[0]))
        self.source_panel._auth_changed(self.source_panel.auth_var.get())
        self.source_panel.username_entry.delete(0, "end")
        self.source_panel.username_entry.insert(0, src.get("username", ""))

        self.target_panel.server_var.set(tgt.get("server", ""))
        self.target_panel.database_var.set(tgt.get("database", ""))
        self.target_panel.auth_var.set(tgt.get("auth", AUTH_CHOICES[0]))
        self.target_panel._auth_changed(self.target_panel.auth_var.get())
        self.target_panel.username_entry.delete(0, "end")
        self.target_panel.username_entry.insert(0, tgt.get("username", ""))

        filters = data.get("filters", {})
        self._show_identical.set(str(filters.get("show_identical", "True")) == "True")
        self._show_diff.set(str(filters.get("show_diff", "True")) == "True")
        self._show_missing_tgt.set(str(filters.get("show_missing_target", "True")) == "True")
        self._show_missing_src.set(str(filters.get("show_missing_source", "True")) == "True")
        self._name_filter.set(filters.get("name_contains", ""))

        # Restore comparison options
        self._compare_options["ignore_users"] = str(filters.get("ignore_users", "False")) == "True"
        self._compare_options["ignore_roles"] = str(filters.get("ignore_roles", "False")) == "True"
        self._compare_options["ignore_schemas"] = str(filters.get("ignore_schemas", "False")) == "True"
        self._compare_options["ignore_extended_properties"] = str(filters.get("ignore_extended_properties", "False")) == "True"
        self._compare_options["ignore_triggers"] = str(filters.get("ignore_triggers", "False")) == "True"
        self._compare_options["ignore_indexes"] = str(filters.get("ignore_indexes", "False")) == "True"

        # Restore deployment options
        self._deploy_options["wrap_in_transaction"] = str(filters.get("deploy_wrap_in_transaction", "True")) == "True"
        self._deploy_options["include_drop_phase"] = str(filters.get("deploy_include_drop_phase", "True")) == "True"
        self._deploy_options["include_table_phase"] = str(filters.get("deploy_include_table_phase", "True")) == "True"
        self._deploy_options["include_constraint_phase"] = str(filters.get("deploy_include_constraint_phase", "True")) == "True"
        self._deploy_options["include_programmability_phase"] = str(filters.get("deploy_include_programmability_phase", "True")) == "True"
        self._deploy_options["include_misc_phase"] = str(filters.get("deploy_include_misc_phase", "True")) == "True"
        self._deploy_options["include_rollback_section"] = str(filters.get("deploy_include_rollback_section", "True")) == "True"

        # Restore custom filters
        raw_custom_filters = filters.get("custom_filters")
        if raw_custom_filters:
            try:
                if isinstance(raw_custom_filters, str):
                    self._custom_filters = json.loads(raw_custom_filters) or []
                else:
                    self._custom_filters = list(raw_custom_filters)  # type: ignore[arg-type]
            except Exception:
                self._custom_filters = []
        else:
            self._custom_filters = []
        self._refresh_grid()

    def _first_diff_preview(self, results):
        for obj_type in ["tables", "views", "procedures", "functions", "triggers"]:
            for item in results.get(obj_type, []):
                if item["status"] == "DIFFERENT":
                    details = item.get("details", {})
                    source_def = None
                    target_def = None
                    if obj_type == "tables":
                        source_def = str(details.get("source", {}))
                        target_def = str(details.get("target", {}))
                    else:
                        source_def = (details.get("source", {}) or {}).get("definition", "")
                        target_def = (details.get("target", {}) or {}).get("definition", "")
                    return DiffGenerator(source_def, target_def).side_by_side()
        return []

    def _copy_current_diff(self) -> None:
        if not self._current_diff_text:
            messagebox.showinfo("Copy Diff", "No diff available to copy. Run a comparison and select an object first.")
            return
        try:
            self.clipboard_clear()
            self.clipboard_append(self._current_diff_text)
            self.update_idletasks()
        except Exception as exc:
            messagebox.showerror("Copy Diff", str(exc))

    def _export_current_diff(self) -> None:
        if not self._current_diff_text:
            messagebox.showinfo("Export Diff", "No diff available to export. Run a comparison and select an object first.")
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            title="Export Diff to File",
        )
        if not file_path:
            return
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self._current_diff_text)
            messagebox.showinfo("Export Diff", f"Diff exported to {file_path}")
        except Exception as exc:
            messagebox.showerror("Export Diff", str(exc))

    def _build_results_grid(self, parent) -> None:
        """Create the results grid (filters + tree + diff actions) inside parent.

        The parent is typically the Results tab, so this keeps the noisy
        comparison UI separate from the connection/setup area.
        """
        
        # Configure ttk style for ExamDiff-like appearance
        style = ttk.Style()
        style.theme_use('clam')  # Modern, flat theme
        
        # Configure Treeview style with modern colors
        style.configure('Treeview',
            background='#FFFFFF',
            foreground='#2C3E50',
            fieldbackground='#FFFFFF',
            borderwidth=0,
            relief='flat',
            rowheight=26,
            font=('Segoe UI', 9)
        )
        
        style.configure('Treeview.Heading',
            background='#34495E',
            foreground='#FFFFFF',
            borderwidth=0,
            relief='flat',
            font=('Segoe UI', 10, 'bold')
        )
        
        style.map('Treeview.Heading',
            background=[('active', '#2C3E50')]
        )
        
        # Modern hover and selection effects
        style.map('Treeview',
            background=[('selected', '#3498DB')],
            foreground=[('selected', '#FFFFFF')]
        )

        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        filter_frame = ctk.CTkFrame(parent)
        filter_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 6))
        ctk.CTkCheckBox(filter_frame, text="Show identical", variable=self._show_identical, command=self._refresh_grid).grid(row=0, column=0, sticky="w", padx=4, pady=4)
        ctk.CTkCheckBox(filter_frame, text="Show differences", variable=self._show_diff, command=self._refresh_grid).grid(row=0, column=1, sticky="w", padx=4, pady=4)
        ctk.CTkCheckBox(filter_frame, text="Show missing in target", variable=self._show_missing_tgt, command=self._refresh_grid).grid(row=0, column=2, sticky="w", padx=4, pady=4)
        ctk.CTkCheckBox(filter_frame, text="Show missing in source", variable=self._show_missing_src, command=self._refresh_grid).grid(row=0, column=3, sticky="w", padx=4, pady=4)
        ctk.CTkLabel(filter_frame, text="Name contains:").grid(row=1, column=0, sticky="e", padx=4, pady=4)
        name_entry = ctk.CTkEntry(filter_frame, textvariable=self._name_filter)
        name_entry.grid(row=1, column=1, columnspan=2, sticky="ew", padx=4, pady=4)
        name_entry.bind("<KeyRelease>", lambda _evt: self._refresh_grid())

        container = ctk.CTkFrame(parent)
        container.grid(row=1, column=0, sticky="nsew", padx=0, pady=(0, 0))
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        # ExamDiff-style side-by-side comparison grid
        columns = ("type", "source", "divider", "target", "status")
        self.tree = ttk.Treeview(container, columns=columns, show="headings", height=8)
        self.tree.heading("type", text="Type")
        self.tree.heading("source", text="◄ SOURCE")
        self.tree.heading("divider", text="│")
        self.tree.heading("target", text="TARGET ►")
        self.tree.heading("status", text="Status")
        self.tree.column("type", width=80, anchor="w")
        self.tree.column("source", width=400, anchor="w")
        self.tree.column("divider", width=3, anchor="center", stretch=False)
        self.tree.column("target", width=400, anchor="w")
        self.tree.column("status", width=120, anchor="center")

        # Modern sophisticated color palette
        self.tree.tag_configure("IDENTICAL", background="#FFFFFF", foreground="#95A5A6")  # Clean white with muted gray
        self.tree.tag_configure("DIFFERENT", background="#FFF9E6", foreground="#2C3E50")  # Soft amber
        self.tree.tag_configure("MISSING_IN_TARGET", background="#D5F4E6", foreground="#27AE60")  # Mint green
        self.tree.tag_configure("MISSING_IN_SOURCE", background="#FFE5E5", foreground="#E74C3C")  # Soft coral red
        
        # Alternating row colors with subtle contrast
        self.tree.tag_configure("IDENTICAL_alt", background="#F8F9FA", foreground="#95A5A6")
        self.tree.tag_configure("DIFFERENT_alt", background="#FFF4D9", foreground="#2C3E50")
        self.tree.tag_configure("MISSING_IN_TARGET_alt", background="#C8EDD9", foreground="#27AE60")
        self.tree.tag_configure("MISSING_IN_SOURCE_alt", background="#FFD6D6", foreground="#E74C3C")

        vsb = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=vsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        # Both single-click and double-click open full-screen diff viewer
        self.tree.bind("<<TreeviewSelect>>", self._open_fullscreen_diff)
        self.tree.bind("<Double-1>", self._open_fullscreen_diff)
    
    def _open_fullscreen_diff(self, event=None):
        """Open full-screen ExamDiff-style diff viewer."""
        selected = self.tree.selection()
        if not selected:
            return
        
        iid = selected[0]
        # Find the item in our stored tree data
        match = next((entry for entry in self._tree_data if entry[0] == iid), None)
        if not match:
            return
        
        _, obj_type, item = match
        obj_name = item["name"]
        status = item["status"]
        details = item.get("details", {})
        
        # Get source and target definitions from the details
        # Always show both sides, even for identical objects
        source_def = ""
        target_def = ""
        
        if status != "MISSING_IN_SOURCE":
            src_obj = details.get("source", {})
            if src_obj:
                source_def = self._format_object(obj_type, src_obj)
            else:
                source_def = "(no source data)"
        else:
            source_def = "(missing in source)"
        
        if status != "MISSING_IN_TARGET":
            tgt_obj = details.get("target", {})
            if tgt_obj:
                target_def = self._format_object(obj_type, tgt_obj)
            else:
                target_def = "(no target data)"
        else:
            target_def = "(missing in target)"
        
        # Launch full-screen diff viewer
        FullScreenDiffViewer(self, obj_type, obj_name, status, source_def, target_def)
    
    def _format_column(self, col: dict) -> str:
        """Format a single column with all its properties."""
        dtype = col.get("data_type", "")
        max_len = col.get("max_length")
        prec = col.get("precision")
        scale = col.get("scale")
        nullable = "NULL" if col.get("is_nullable") else "NOT NULL"
        
        # Build type specification
        type_spec = dtype
        if max_len and max_len > 0 and dtype.lower() in ("varchar", "nvarchar", "char", "nchar", "varbinary", "binary"):
            type_spec += f"({max_len if max_len != -1 else 'MAX'})"
        elif prec and prec > 0:
            if scale and scale > 0:
                type_spec += f"({prec},{scale})"
            else:
                type_spec += f"({prec})"
        
        # Build column definition line
        line = f"  {col['name']:<40} {type_spec:<25} {nullable:<10}"
        
        # Add special properties
        props = []
        if col.get("is_identity"):
            props.append(f"IDENTITY({col.get('identity_seed', 1)},{col.get('identity_increment', 1)})")
        if col.get("is_computed"):
            computed_def = col.get("computed_definition", "")
            persisted = " PERSISTED" if col.get("is_persisted") else ""
            props.append(f"AS {computed_def}{persisted}")
        if col.get("is_sparse"):
            props.append("SPARSE")
        if col.get("is_rowguidcol"):
            props.append("ROWGUIDCOL")
        if col.get("collation"):
            props.append(f"COLLATE {col['collation']}")
        if col.get("default_value"):
            props.append(f"DEFAULT {col['default_value']}")
        
        if props:
            line += " " + " ".join(props)
        
        return line + "\n"
    
    def _format_object(self, obj_type: str, obj: dict) -> str:
        """Format object for display in diff viewer."""
        if obj_type == "tables":
            # Format table structure
            lines = [f"Table: {obj.get('name', '')}\n\n"]
            lines.append("Columns:\n")
            for col in obj.get("columns", []):
                dtype = col.get("data_type", "")
                max_len = col.get("max_length")
                prec = col.get("precision")
                scale = col.get("scale")
                nullable = "NULL" if str(col.get("is_nullable", "")).upper() in ("YES", "TRUE", "1") else "NOT NULL"
                
                type_spec = dtype
                if max_len and max_len > 0 and dtype.lower() in ("varchar", "nvarchar", "char", "nchar", "varbinary", "binary"):
                    type_spec += f"({max_len if max_len != -1 else 'MAX'})"
                elif prec and prec > 0:
                    if scale and scale > 0:
                        type_spec += f"({prec},{scale})"
                    else:
                        type_spec += f"({prec})"
                
                lines.append(f"  {col['name']:<40} {type_spec:<20} {nullable}\n")
            
            # Add indexes if any
            if obj.get("indexes"):
                lines.append("\nIndexes:\n")
                for idx in obj["indexes"]:
                    idx_type = "CLUSTERED" if idx.get("is_clustered") else "NONCLUSTERED"
                    unique = "UNIQUE " if idx.get("is_unique") else ""
                    lines.append(f"  {unique}{idx_type}: {idx['name']}\n")
            
            return "".join(lines)
        else:
            # For programmable objects, use definition field
            if isinstance(obj, dict) and "definition" in obj:
                return obj.get("definition", "")
            else:
                return str(obj)

    def _populate_grid(self, results) -> None:
        # clear
        for row in self.tree.get_children():
            self.tree.delete(row)
        self._tree_data = []
        self._last_results = results
        row_count = 0
        for obj_type, items in results.items():
            for item in items:
                if not self._passes_filters(item):
                    continue
                # Alternate row colors for better readability (ExamDiff style)
                status = item.get("status", "")
                if row_count % 2 == 0:
                    tag = (status,)
                else:
                    tag = (f"{status}_alt",)
                
                # Format source and target columns for side-by-side display
                obj_name = item["name"]
                source_display = obj_name if status != "MISSING_IN_SOURCE" else "(missing)"
                target_display = obj_name if status != "MISSING_IN_TARGET" else "(missing)"
                
                # Add status indicator symbols
                if status == "IDENTICAL":
                    status_symbol = "="
                elif status == "DIFFERENT":
                    status_symbol = "≠"
                elif status == "MISSING_IN_TARGET":
                    status_symbol = "→"
                elif status == "MISSING_IN_SOURCE":
                    status_symbol = "←"
                else:
                    status_symbol = "?"
                
                iid = self.tree.insert("", "end", 
                    values=(obj_type, source_display, "│", target_display, status_symbol), 
                    tags=tag)
                self._tree_data.append((iid, obj_type, item))
                row_count += 1

    def _refresh_grid(self) -> None:
        if self._last_results:
            self._populate_grid(self._last_results)

    def _passes_filters(self, item: dict) -> bool:
        status = item.get("status")
        if status == "IDENTICAL" and not self._show_identical.get():
            return False
        if status == "DIFFERENT" and not self._show_diff.get():
            return False
        if status == "MISSING_IN_TARGET" and not self._show_missing_tgt.get():
            return False
        if status == "MISSING_IN_SOURCE" and not self._show_missing_src.get():
            return False
        name_filter = self._name_filter.get().strip().lower()
        if name_filter and name_filter not in item.get("name", "").lower():
            return False
        # Apply custom include/exclude filters (name/schema/type/status)
        if self._custom_filters:
            full_name = (item.get("name") or "").lower()
            obj_type = (item.get("type") or "").lower()  # may be empty; tree supplies type separately
            obj_status = (item.get("status") or "").lower()
            schema_name = ""
            if "." in full_name:
                schema_name = full_name.split(".", 1)[0]

            def value_for_field(field: str) -> str:
                f = field.lower()
                if f == "schema":
                    return schema_name
                if f == "type":
                    return obj_type
                if f == "status":
                    return obj_status
                return full_name

            includes = [
                f for f in self._custom_filters
                if (f.get("mode") or "include").lower() == "include" and f.get("pattern")
            ]
            excludes = [
                f for f in self._custom_filters
                if (f.get("mode") or "include").lower() == "exclude" and f.get("pattern")
            ]

            def rule_matches(rule: dict) -> bool:
                field = (rule.get("field") or "name").lower()
                pattern = str(rule.get("pattern", "")).lower()
                target_val = value_for_field(field)
                return bool(pattern) and pattern in target_val

            if includes:
                if not any(rule_matches(r) for r in includes):
                    return False

            if excludes:
                if any(rule_matches(r) for r in excludes):
                    return False
        return True

    def _on_tree_select(self, event) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        iid = selection[0]
        match = next((entry for entry in self._tree_data if entry[0] == iid), None)
        if not match:
            return
        _, obj_type, item = match
        details = item.get("details", {})
        source_def = ""
        target_def = ""
        if obj_type == "tables":
            # For tables, format the structure in a readable way
            # Handle MISSING_IN_TARGET: details contains the source object directly
            if item["status"] == "MISSING_IN_TARGET":
                src_tbl = details
                if src_tbl and isinstance(src_tbl, dict):
                    lines = [f"Table: {item['name']}\n\n"]
                    lines.append("Columns:\n")
                    for col in src_tbl.get("columns", []):
                        lines.append(self._format_column(col))
                    
                    # Add primary keys
                    if src_tbl.get("primary_key"):
                        lines.append("\nPrimary Key:\n")
                        pk = src_tbl["primary_key"]
                        lines.append(f"  {pk.get('name', 'PK')}: {', '.join(pk.get('columns', []))}\n")
                    
                    # Add foreign keys
                    if src_tbl.get("foreign_keys"):
                        lines.append("\nForeign Keys:\n")
                        for fk in src_tbl["foreign_keys"]:
                            lines.append(f"  {fk['name']}: {', '.join(fk['columns'])} -> {fk['referenced_table']}({', '.join(fk['referenced_columns'])})\n")
                    
                    # Add indexes
                    if src_tbl.get("indexes"):
                        lines.append("\nIndexes:\n")
                        for idx in src_tbl["indexes"]:
                            idx_type = "CLUSTERED" if idx.get("is_clustered") else "NONCLUSTERED"
                            unique = "UNIQUE " if idx.get("is_unique") else ""
                            cols = ', '.join(idx.get("columns", []))
                            lines.append(f"  {unique}{idx_type}: {idx['name']} ({cols})\n")
                    
                    source_def = "".join(lines)
                target_def = "(missing in target)"
            # Handle MISSING_IN_SOURCE: details contains the target object directly
            elif item["status"] == "MISSING_IN_SOURCE":
                tgt_tbl = details
                if tgt_tbl and isinstance(tgt_tbl, dict):
                    lines = [f"Table: {item['name']}\n\n"]
                    lines.append("Columns:\n")
                    for col in tgt_tbl.get("columns", []):
                        lines.append(self._format_column(col))
                    
                    # Add primary keys
                    if tgt_tbl.get("primary_key"):
                        lines.append("\nPrimary Key:\n")
                        pk = tgt_tbl["primary_key"]
                        lines.append(f"  {pk.get('name', 'PK')}: {', '.join(pk.get('columns', []))}\n")
                    
                    # Add foreign keys
                    if tgt_tbl.get("foreign_keys"):
                        lines.append("\nForeign Keys:\n")
                        for fk in tgt_tbl["foreign_keys"]:
                            lines.append(f"  {fk['name']}: {', '.join(fk['columns'])} -> {fk['referenced_table']}({', '.join(fk['referenced_columns'])})\n")
                    
                    # Add indexes
                    if tgt_tbl.get("indexes"):
                        lines.append("\nIndexes:\n")
                        for idx in tgt_tbl["indexes"]:
                            idx_type = "CLUSTERED" if idx.get("is_clustered") else "NONCLUSTERED"
                            unique = "UNIQUE " if idx.get("is_unique") else ""
                            cols = ', '.join(idx.get("columns", []))
                            lines.append(f"  {unique}{idx_type}: {idx['name']} ({cols})\n")
                    
                    target_def = "".join(lines)
                source_def = "(missing in source)"
            # Handle IDENTICAL or DIFFERENT: details has source and target nested
            else:
                src_tbl = details.get("source", {})
                if src_tbl:
                    lines = [f"Table: {item['name']}\n\n"]
                    lines.append("Columns:\n")
                    for col in src_tbl.get("columns", []):
                        lines.append(self._format_column(col))
                    
                    # Add primary keys
                    if src_tbl.get("primary_key"):
                        lines.append("\nPrimary Key:\n")
                        pk = src_tbl["primary_key"]
                        lines.append(f"  {pk.get('name', 'PK')}: {', '.join(pk.get('columns', []))}\n")
                    
                    # Add foreign keys
                    if src_tbl.get("foreign_keys"):
                        lines.append("\nForeign Keys:\n")
                        for fk in src_tbl["foreign_keys"]:
                            lines.append(f"  {fk['name']}: {', '.join(fk['columns'])} -> {fk['referenced_table']}({', '.join(fk['referenced_columns'])})\n")
                    
                    # Add indexes
                    if src_tbl.get("indexes"):
                        lines.append("\nIndexes:\n")
                        for idx in src_tbl["indexes"]:
                            idx_type = "CLUSTERED" if idx.get("is_clustered") else "NONCLUSTERED"
                            unique = "UNIQUE " if idx.get("is_unique") else ""
                            cols = ', '.join(idx.get("columns", []))
                            lines.append(f"  {unique}{idx_type}: {idx['name']} ({cols})\n")
                    
                    source_def = "".join(lines)
                else:
                    source_def = "(table missing)"
                
                tgt_tbl = details.get("target", {})
                if tgt_tbl:
                    lines = [f"Table: {item['name']}\n\n"]
                    lines.append("Columns:\n")
                    for col in tgt_tbl.get("columns", []):
                        lines.append(self._format_column(col))
                    
                    # Add primary keys
                    if tgt_tbl.get("primary_key"):
                        lines.append("\nPrimary Key:\n")
                        pk = tgt_tbl["primary_key"]
                        lines.append(f"  {pk.get('name', 'PK')}: {', '.join(pk.get('columns', []))}\n")
                    
                    # Add foreign keys
                    if tgt_tbl.get("foreign_keys"):
                        lines.append("\nForeign Keys:\n")
                        for fk in tgt_tbl["foreign_keys"]:
                            lines.append(f"  {fk['name']}: {', '.join(fk['columns'])} -> {fk['referenced_table']}({', '.join(fk['referenced_columns'])})\n")
                    
                    # Add indexes
                    if tgt_tbl.get("indexes"):
                        lines.append("\nIndexes:\n")
                        for idx in tgt_tbl["indexes"]:
                            idx_type = "CLUSTERED" if idx.get("is_clustered") else "NONCLUSTERED"
                            unique = "UNIQUE " if idx.get("is_unique") else ""
                            cols = ', '.join(idx.get("columns", []))
                            lines.append(f"  {unique}{idx_type}: {idx['name']} ({cols})\n")
                    
                    target_def = "".join(lines)
                else:
                    target_def = "(table missing)"
        else:
            # For programmable objects (views/procs/functions/triggers) we
            # prefer the stored SQL definition. For other object types that
            # do not expose a single definition string (users, roles,
            # constraints, user-defined types, sequences, etc.), fall back
            # to a readable string representation of the metadata dict so
            # users can still see what changed.
            
            # Handle MISSING_IN_TARGET: details contains the source object directly
            if item["status"] == "MISSING_IN_TARGET":
                src_obj = details or {}
                if isinstance(src_obj, dict) and "definition" in src_obj:
                    source_def = src_obj.get("definition", "")
                else:
                    source_def = str(src_obj) if src_obj else ""
                target_def = "(missing in target)"
            # Handle MISSING_IN_SOURCE: details contains the target object directly
            elif item["status"] == "MISSING_IN_SOURCE":
                tgt_obj = details or {}
                if isinstance(tgt_obj, dict) and "definition" in tgt_obj:
                    target_def = tgt_obj.get("definition", "")
                else:
                    target_def = str(tgt_obj) if tgt_obj else ""
                source_def = "(missing in source)"
            # Handle IDENTICAL or DIFFERENT: details has source and target nested
            else:
                src_obj = details.get("source", {}) or {}
                if isinstance(src_obj, dict) and "definition" in src_obj:
                    source_def = src_obj.get("definition", "")
                else:
                    source_def = str(src_obj) if src_obj else ""
                    
                tgt_obj = details.get("target", {}) or {}
                if isinstance(tgt_obj, dict) and "definition" in tgt_obj:
                    target_def = tgt_obj.get("definition", "")
                else:
                    target_def = str(tgt_obj) if tgt_obj else ""

        diff = DiffGenerator(source_def, target_def).side_by_side()

        # Always show Diff tab when selecting an item
        try:
            self.diff_tabs.set("Diff")
        except Exception:
            pass

        # Configure tags for color highlighting - ExamDiff style colors
        for widget in (self.sql_left_text, self.sql_right_text):
            widget.configure(state="normal")
            widget.delete("1.0", "end")
            widget.tag_config("same", foreground="#666666")
            widget.tag_config("add", foreground="#000000", background="#C8F7C5")  # Light green
            widget.tag_config("del", foreground="#000000", background="#FFB3B3")  # Light red
            widget.tag_config("chg", foreground="#000000", background="#FFE4B3")  # Light orange
            widget.tag_config("separator", foreground="#888888", background="#E0E0E0")  # Separator line

        # Object header
        obj_title = f"{obj_type.upper()}: {item['name']} [{item['status']}]"
        header_line = "─" * 80
        
        self.sql_left_text.insert("1.0", f"{obj_title}\n{header_line}\n\n")
        self.sql_right_text.insert("1.0", f"{obj_title}\n{header_line}\n\n")

        rendered_lines: list[str] = [f"{obj_title}\n"]

        if not diff:
            line = "No differences found (objects are identical or one is missing)."
            self.sql_left_text.insert("end", line)
            self.sql_right_text.insert("end", line)
            rendered_lines.append(line + "\n")
        else:
            # Track change blocks for visual separation
            prev_tag = None
            change_block = 0
            
            for idx, (left, right, tag) in enumerate(diff, start=1):
                # Add separator line between different change blocks
                if prev_tag is not None and prev_tag != tag and tag != "same":
                    if prev_tag != "same":
                        sep_line = "─" * 80 + "\n"
                        self.sql_left_text.insert("end", sep_line, "separator")
                        self.sql_right_text.insert("end", sep_line, "separator")
                        change_block += 1
                
                # Format with line numbers
                ln = f"{idx:4d}│ "
                left_display = ln + left
                right_display = ln + right

                # Determine tag for each side
                left_tag = tag if tag in ("same", "add", "chg") else "del"
                right_tag = tag if tag in ("same", "del", "chg") else "add"

                # Insert left side with tag
                start_pos = self.sql_left_text.index("end-1c")
                self.sql_left_text.insert("end", left_display + "\n")
                end_pos = self.sql_left_text.index("end-1c")
                if left.strip():
                    self.sql_left_text.tag_add(left_tag, start_pos, end_pos)

                # Insert right side with tag
                start_pos = self.sql_right_text.index("end-1c")
                self.sql_right_text.insert("end", right_display + "\n")
                end_pos = self.sql_right_text.index("end-1c")
                if right.strip():
                    self.sql_right_text.tag_add(right_tag, start_pos, end_pos)

                rendered_lines.append(f"{left_display} | {right_display}\n")
                prev_tag = tag

        full_text = "".join(rendered_lines)
        self._current_diff_text = full_text

        self.sql_left_text.configure(state="disabled")
        self.sql_right_text.configure(state="disabled")

        # Build semantic summary for Summary View
        self._update_summary_view(obj_type, item)

    def _update_summary_view(self, obj_type: str, item: dict) -> None:
        """Populate the Summary View tab with a semantic summary.

        For tables this shows column-level changes (added/removed/changed),
        falling back to a simple message for other object types.
        """
        self.summary_text.configure(state="normal")
        self.summary_text.delete("1.0", "end")

        status = item.get("status")
        name = item.get("name", "")

        if status == "IDENTICAL":
            self.summary_text.insert("1.0", f"{obj_type}: {name}\nStatus: IDENTICAL (no changes).")
            self.summary_text.configure(state="disabled")
            return

        details = item.get("details", {}) or {}

        if obj_type == "tables":
            src = details.get("source") or {}
            tgt = details.get("target") or {}
            src_cols = {c["name"]: c for c in src.get("columns", [])}
            tgt_cols = {c["name"]: c for c in tgt.get("columns", [])}

            all_names = sorted(set(src_cols.keys()) | set(tgt_cols.keys()))

            lines: list[str] = []
            lines.append(f"Table: {name}\n")
            lines.append(f"Overall status: {status}\n\n")
            lines.append("Columns:\n")
            lines.append(f"{'Name':<32} {'Source':<30} {'Target':<30} Status\n")
            lines.append(f"{'-'*32} {'-'*30} {'-'*30} {'-'*10}\n")

            def fmt(col: dict | None) -> str:
                if not col:
                    return "(missing)"
                dtype = col.get("data_type", "")
                max_len = col.get("max_length")
                prec = col.get("precision")
                scale = col.get("scale")
                nullable = col.get("is_nullable")
                pieces = [dtype]
                if max_len is not None:
                    pieces.append(f"({max_len})")
                elif prec is not None:
                    if scale is not None:
                        pieces.append(f"({prec},{scale})")
                    else:
                        pieces.append(f"({prec})")
                if nullable is not None:
                    pieces.append(" NULL" if str(nullable).upper() in ("YES", "TRUE", "1") else " NOT NULL")
                return "".join(str(p) for p in pieces if p is not None)

            for col_name in all_names:
                s = src_cols.get(col_name)
                t = tgt_cols.get(col_name)
                if s and not t:
                    col_status = "REMOVED (missing in target)"
                elif t and not s:
                    col_status = "ADDED (missing in source)"
                else:
                    src_sig = fmt(s)
                    tgt_sig = fmt(t)
                    if src_sig == tgt_sig:
                        col_status = "SAME"
                    else:
                        col_status = "CHANGED"
                lines.append(f"{col_name:<32} {fmt(s):<30} {fmt(t):<30} {col_status}\n")

            self.summary_text.insert("1.0", "".join(lines))
        else:
            # Fallback summary for non-table objects
            self.summary_text.insert(
                "1.0",
                f"{obj_type}: {name}\nStatus: {status}\n\nDetailed diff is available in the SQL View tab.",
            )

        self.summary_text.configure(state="disabled")


class FullScreenDiffViewer(ctk.CTkToplevel):
    """ExamDiff-style full-screen diff viewer."""
    
    def __init__(self, master, obj_type: str, obj_name: str, status: str, source_def: str, target_def: str):
        super().__init__(master)
        self.title(f"Diff: {obj_name}")
        self.geometry("1600x900")
        self.minsize(1200, 600)
        
        # Make it feel like a modal dialog
        self.transient(master)
        self.grab_set()
        
        self.obj_type = obj_type
        self.obj_name = obj_name
        self.status = status
        self.source_lines = source_def.split("\n") if source_def else ["(empty)"]
        self.target_lines = target_def.split("\n") if target_def else ["(empty)"]
        
        # Calculate diff
        self.diff_data = self._compute_diff()
        
        self._build_ui()
        
    def _compute_diff(self):
        """Compute line-by-line diff similar to DiffGenerator."""
        from core.diff_generator import DiffGenerator
        
        source_text = "\n".join(self.source_lines)
        target_text = "\n".join(self.target_lines)
        
        return DiffGenerator(source_text, target_text).side_by_side()
    
    def _build_ui(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Modern header bar
        info_bar = ctk.CTkFrame(self, fg_color=("#34495E", "#2C3E50"), height=35)
        info_bar.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        info_bar.grid_columnconfigure(0, weight=1)
        info_bar.grid_columnconfigure(1, weight=1)
        
        # Left file info
        left_info = ctk.CTkLabel(
            info_bar,
            text=f"◄ SOURCE: {self.obj_type} - {self.obj_name}",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#ECF0F1",
            anchor="w"
        )
        left_info.grid(row=0, column=0, sticky="w", padx=12, pady=6)
        
        # Right file info
        right_info = ctk.CTkLabel(
            info_bar,
            text=f"TARGET ►: {self.obj_type} - {self.obj_name}",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#ECF0F1",
            anchor="w"
        )
        right_info.grid(row=0, column=1, sticky="w", padx=12, pady=6)
        
        # Main diff area
        diff_container = ctk.CTkFrame(self, fg_color="transparent")
        diff_container.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        diff_container.grid_rowconfigure(0, weight=1)
        diff_container.grid_columnconfigure(0, weight=1)
        diff_container.grid_columnconfigure(1, weight=1)
        
        # Create text widgets with ExamDiff styling
        mono_font = ctk.CTkFont(family="Consolas", size=10)
        
        # Left pane (SOURCE)
        self.left_text = ctk.CTkTextbox(
            diff_container,
            font=mono_font,
            wrap="none",
            fg_color=("#FAFBFC", "#1E1E2E"),
            text_color=("#2C3E50", "#ECF0F1")
        )
        self.left_text.grid(row=0, column=0, sticky="nsew", padx=(0, 2), pady=0)
        
        # Right pane (TARGET)
        self.right_text = ctk.CTkTextbox(
            diff_container,
            font=mono_font,
            wrap="none",
            fg_color=("#FAFBFC", "#1E1E2E"),
            text_color=("#2C3E50", "#ECF0F1")
        )
        self.right_text.grid(row=0, column=1, sticky="nsew", padx=(2, 0), pady=0)
        
        # Configure ExamDiff-style color tags
        self._configure_tags()
        
        # Populate with diff
        self._populate_diff()
        
        # Bind synchronized scrolling
        self.left_text._textbox.bind("<MouseWheel>", lambda e: self._sync_scroll(e, "left"))
        self.right_text._textbox.bind("<MouseWheel>", lambda e: self._sync_scroll(e, "right"))
        self.left_text._textbox.bind("<Key>", lambda e: self._sync_scroll(e, "left"))
        self.right_text._textbox.bind("<Key>", lambda e: self._sync_scroll(e, "right"))
        
        # Modern status bar
        status_bar = ctk.CTkFrame(self, fg_color=("#ECF0F1", "#2C3E50"), height=32)
        status_bar.grid(row=2, column=0, sticky="ew", padx=0, pady=0)
        
        diff_count = sum(1 for _, _, tag in self.diff_data if tag != "same")
        status_text = f"  {diff_count} differences found  |  Status: {self.status}"
        
        ctk.CTkLabel(
            status_bar,
            text=status_text,
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=("#2C3E50", "#ECF0F1"),
            anchor="w"
        ).pack(side="left", padx=12, pady=6)
        
        # Copy buttons
        button_frame = ctk.CTkFrame(status_bar, fg_color="transparent")
        button_frame.pack(side="right", padx=10, pady=2)
        
        ctk.CTkButton(
            button_frame,
            text="Copy Source",
            width=100,
            height=26,
            command=self._copy_source
        ).pack(side="left", padx=2)
        
        ctk.CTkButton(
            button_frame,
            text="Copy Target",
            width=100,
            height=26,
            command=self._copy_target
        ).pack(side="left", padx=2)
        
        ctk.CTkButton(
            button_frame,
            text="Copy Both",
            width=100,
            height=26,
            command=self._copy_both
        ).pack(side="left", padx=2)
        
        # Close button
        ctk.CTkButton(
            button_frame,
            text="Close",
            width=80,
            height=26,
            command=self.destroy
        ).pack(side="left", padx=2)
    
    def _configure_tags(self):
        """Configure modern sophisticated color tags."""
        # Modern color scheme with better contrast and aesthetics
        for widget in (self.left_text, self.right_text):
            widget.tag_config("same", foreground="#7F8C8D", background="#FFFFFF")
            widget.tag_config("add", foreground="#27AE60", background="#D5F4E6")      # Modern mint green
            widget.tag_config("del", foreground="#E74C3C", background="#FFE5E5")      # Soft coral red  
            widget.tag_config("chg", foreground="#E67E22", background="#FFF4E6")      # Warm amber
            widget.tag_config("line_num", foreground="#95A5A6", background="#ECF0F1") # Muted gray
    
    def _populate_diff(self):
        """Populate both panes with the diff data."""
        self.left_text.configure(state="normal")
        self.right_text.configure(state="normal")
        
        for idx, (left, right, tag) in enumerate(self.diff_data, start=1):
            # Line numbers with padding
            ln = f"{idx:5d} "
            
            # Determine background color for each side
            left_tag = "same"
            right_tag = "same"
            
            if tag == "add":
                left_tag = "same"
                right_tag = "add"
            elif tag == "del":
                left_tag = "del"
                right_tag = "same"
            elif tag == "chg":
                left_tag = "chg"
                right_tag = "chg"
            
            # Insert left side
            ln_start = self.left_text.index("end-1c")
            self.left_text.insert("end", ln)
            ln_end = self.left_text.index("end-1c")
            self.left_text.tag_add("line_num", ln_start, ln_end)
            
            content_start = self.left_text.index("end-1c")
            self.left_text.insert("end", left + "\n")
            content_end = self.left_text.index("end-1c")
            if left.strip():
                self.left_text.tag_add(left_tag, content_start, content_end)
            
            # Insert right side
            ln_start = self.right_text.index("end-1c")
            self.right_text.insert("end", ln)
            ln_end = self.right_text.index("end-1c")
            self.right_text.tag_add("line_num", ln_start, ln_end)
            
            content_start = self.right_text.index("end-1c")
            self.right_text.insert("end", right + "\n")
            content_end = self.right_text.index("end-1c")
            if right.strip():
                self.right_text.tag_add(right_tag, content_start, content_end)
        
        self.left_text.configure(state="disabled")
        self.right_text.configure(state="disabled")
    
    def _copy_source(self):
        """Copy source content to clipboard."""
        try:
            content = self.left_text.get("1.0", "end-1c")
            self.clipboard_clear()
            self.clipboard_append(content)
            self.update()  # Force clipboard update
        except Exception as e:
            print(f"Failed to copy source: {e}")
    
    def _copy_target(self):
        """Copy target content to clipboard."""
        try:
            content = self.right_text.get("1.0", "end-1c")
            self.clipboard_clear()
            self.clipboard_append(content)
            self.update()
        except Exception as e:
            print(f"Failed to copy target: {e}")
    
    def _copy_both(self):
        """Copy both source and target to clipboard."""
        try:
            source = self.left_text.get("1.0", "end-1c")
            target = self.right_text.get("1.0", "end-1c")
            content = f"=== SOURCE ===\n{source}\n\n=== TARGET ===\n{target}"
            self.clipboard_clear()
            self.clipboard_append(content)
            self.update()
        except Exception as e:
            print(f"Failed to copy both: {e}")
    
    def _sync_scroll(self, event, source):
        """Synchronize scrolling between panes."""
        try:
            other = self.right_text if source == "left" else self.left_text
            src = self.left_text if source == "left" else self.right_text
            
            yview = src._textbox.yview()
            other._textbox.yview_moveto(yview[0])
        except Exception:
            pass
        
        return "break"


def launch():
    app = MainWindow()
    app.mainloop()


class DeploymentWizard(ctk.CTkToplevel):
    """Simple multi-step deployment wizard.

    Step 1: Review summary of changes.
    Step 2: Review detected warnings/notes from the deployment script.
    Step 3: Preview final deployment script with options to copy/save.
    """

    def __init__(self, master: MainWindow, results, script_text: str, target_db: str) -> None:
        super().__init__(master)
        self.title("Deployment Wizard")
        self.geometry("900x600")
        self.results = results
        self.script_text = script_text
        self.target_db = target_db
        self.step = 1

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.content_frame = ctk.CTkFrame(self)
        self.content_frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=(12, 0))
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)

        self.text = ctk.CTkTextbox(self.content_frame)
        self.text.grid(row=0, column=0, sticky="nsew")

        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.grid(row=1, column=0, sticky="ew", padx=12, pady=8)
        nav.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.back_btn = ctk.CTkButton(nav, text="< Back", command=self._back)
        self.back_btn.grid(row=0, column=0, padx=4)
        self.next_btn = ctk.CTkButton(nav, text="Next >", command=self._next)
        self.next_btn.grid(row=0, column=1, padx=4)
        self.finish_btn = ctk.CTkButton(nav, text="Finish", command=self._finish)
        self.finish_btn.grid(row=0, column=2, padx=4)
        self.cancel_btn = ctk.CTkButton(nav, text="Cancel", command=self.destroy)
        self.cancel_btn.grid(row=0, column=3, padx=4)

        self._show_step()

    def _set_text(self, header: str, body: str) -> None:
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", header + "\n\n" + body)
        self.text.configure(state="disabled")

    def _build_summary_body(self) -> str:
        # Basic counts by status and object type
        lines: list[str] = []
        lines.append(f"Target database: {self.target_db}\n")
        status_counts = {"IDENTICAL": 0, "DIFFERENT": 0, "MISSING_IN_TARGET": 0, "MISSING_IN_SOURCE": 0}
        for obj_type, items in self.results.items():
            for item in items:
                st = item.get("status")
                if st in status_counts:
                    status_counts[st] += 1
        lines.append("Overall status counts:\n")
        for key, val in status_counts.items():
            lines.append(f"  - {key}: {val}\n")

        lines.append("\nObjects to be scripted (by type):\n")
        for obj_type, items in self.results.items():
            to_script = [i for i in items if i.get("status") in ("MISSING_IN_TARGET", "DIFFERENT")]
            if to_script:
                lines.append(f"  - {obj_type}: {len(to_script)}\n")

        return "".join(lines)

    def _build_warnings_body(self) -> str:
        lines: list[str] = []
        for line in self.script_text.splitlines():
            if "WARNING" in line or "NOTE:" in line:
                lines.append(line + "\n")
        if not lines:
            lines.append("No warnings or notes were detected in the generated script.\n")
        return "".join(lines)

    def _show_step(self) -> None:
        if self.step <= 1:
            self.step = 1
            header = "Step 1 of 3: Review Changes"
            body = self._build_summary_body()
        elif self.step == 2:
            header = "Step 2 of 3: Warnings and Notes"
            body = self._build_warnings_body()
        else:
            self.step = 3
            header = "Step 3 of 3: Deployment Script Preview"
            body = self.script_text

        self._set_text(header, body)

        # Enable/disable navigation buttons appropriately
        self.back_btn.configure(state="disabled" if self.step == 1 else "normal")
        self.next_btn.configure(state="disabled" if self.step == 3 else "normal")

    def _back(self) -> None:
        if self.step > 1:
            self.step -= 1
            self._show_step()

    def _next(self) -> None:
        if self.step < 3:
            self.step += 1
            self._show_step()

    def _finish(self) -> None:
        # On finish we simply close; script has already been generated
        # and can be copied/saved from the final step.
        self.destroy()
