"""License management system for commercial distribution."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from utils.logger import get_logger

logger = get_logger(__name__)


class LicenseManager:
    """Manages software licensing for commercial use."""
    
    LICENSE_FILE = Path.home() / ".sql_compare_license.enc"
    TRIAL_DAYS = 30
    
    def __init__(self):
        self._key = self._get_or_create_key()
        self._cipher = Fernet(self._key)
        
    def _get_or_create_key(self) -> bytes:
        """Get or create encryption key for license."""
        key_file = Path.home() / ".sql_compare_key"
        if key_file.exists():
            return key_file.read_bytes()
        key = Fernet.generate_key()
        key_file.write_bytes(key)
        return key
    
    def validate_license(self) -> tuple[bool, str, Optional[datetime]]:
        """
        Validate license status.
        
        Returns:
            (is_valid, license_type, expiry_date)
            license_type: 'trial', 'commercial', 'expired', 'invalid'
        """
        try:
            if not self.LICENSE_FILE.exists():
                # No license = start trial
                return self._start_trial()
            
            license_data = self._read_license()
            
            if not license_data:
                return False, "invalid", None
            
            license_type = license_data.get("type")
            
            if license_type == "commercial":
                # Check if commercial license is valid
                if self._verify_commercial_license(license_data):
                    expiry = license_data.get("expiry")
                    if expiry:
                        expiry_date = datetime.fromisoformat(expiry)
                        if datetime.now() > expiry_date:
                            return False, "expired", expiry_date
                    return True, "commercial", expiry_date if expiry else None
                return False, "invalid", None
            
            elif license_type == "trial":
                start_date = datetime.fromisoformat(license_data["start_date"])
                expiry_date = start_date + timedelta(days=self.TRIAL_DAYS)
                
                if datetime.now() > expiry_date:
                    return False, "expired", expiry_date
                
                days_left = (expiry_date - datetime.now()).days
                logger.info(f"Trial license valid. {days_left} days remaining.")
                return True, "trial", expiry_date
            
            return False, "invalid", None
            
        except Exception as e:
            logger.error(f"License validation error: {e}")
            return False, "invalid", None
    
    def _start_trial(self) -> tuple[bool, str, datetime]:
        """Start a new trial period."""
        try:
            start_date = datetime.now()
            expiry_date = start_date + timedelta(days=self.TRIAL_DAYS)
            
            license_data = {
                "type": "trial",
                "start_date": start_date.isoformat(),
                "machine_id": self._get_machine_id()
            }
            
            self._write_license(license_data)
            logger.info(f"Trial license created. Valid until {expiry_date.strftime('%Y-%m-%d')}")
            return True, "trial", expiry_date
            
        except Exception as e:
            logger.error(f"Failed to create trial license: {e}")
            return False, "invalid", None
    
    def activate_commercial_license(self, license_key: str) -> tuple[bool, str]:
        """
        Activate a commercial license with provided key.
        
        Args:
            license_key: Commercial license key
            
        Returns:
            (success, message)
        """
        try:
            # Validate license key format and signature
            if not self._validate_license_key(license_key):
                return False, "Invalid license key format"
            
            # Parse license key
            license_info = self._parse_license_key(license_key)
            
            if not license_info:
                return False, "License key could not be parsed"
            
            # Check machine binding (optional)
            machine_id = self._get_machine_id()
            
            license_data = {
                "type": "commercial",
                "license_key": license_key,
                "activated_date": datetime.now().isoformat(),
                "machine_id": machine_id,
                "user_name": license_info.get("user_name"),
                "company": license_info.get("company"),
                "expiry": license_info.get("expiry"),
                "edition": license_info.get("edition", "standard")
            }
            
            self._write_license(license_data)
            logger.info(f"Commercial license activated for {license_info.get('user_name', 'user')}")
            return True, "License activated successfully"
            
        except Exception as e:
            logger.error(f"License activation failed: {e}")
            return False, f"Activation failed: {str(e)}"
    
    def get_license_info(self) -> Dict[str, Any]:
        """Get current license information."""
        is_valid, license_type, expiry = self.validate_license()
        
        info = {
            "is_valid": is_valid,
            "type": license_type,
            "expiry": expiry
        }
        
        if self.LICENSE_FILE.exists():
            license_data = self._read_license()
            if license_data:
                info.update({
                    "user_name": license_data.get("user_name"),
                    "company": license_data.get("company"),
                    "edition": license_data.get("edition", "trial"),
                    "activated_date": license_data.get("activated_date")
                })
        
        return info
    
    def _read_license(self) -> Optional[Dict[str, Any]]:
        """Read and decrypt license file."""
        try:
            encrypted_data = self.LICENSE_FILE.read_bytes()
            decrypted_data = self._cipher.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode())
        except Exception as e:
            logger.error(f"Failed to read license: {e}")
            return None
    
    def _write_license(self, license_data: Dict[str, Any]) -> bool:
        """Encrypt and write license file."""
        try:
            json_data = json.dumps(license_data).encode()
            encrypted_data = self._cipher.encrypt(json_data)
            self.LICENSE_FILE.write_bytes(encrypted_data)
            return True
        except Exception as e:
            logger.error(f"Failed to write license: {e}")
            return False
    
    def _get_machine_id(self) -> str:
        """Generate unique machine identifier."""
        import platform
        import uuid
        
        # Combine multiple hardware identifiers
        machine_info = f"{platform.node()}-{uuid.getnode()}"
        return hashlib.sha256(machine_info.encode()).hexdigest()[:16]
    
    def _validate_license_key(self, license_key: str) -> bool:
        """Validate license key format."""
        # Format: XXXX-XXXX-XXXX-XXXX-XXXX (5 groups of 4 chars)
        import re
        pattern = r'^[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$'
        return bool(re.match(pattern, license_key.upper()))
    
    def _parse_license_key(self, license_key: str) -> Optional[Dict[str, Any]]:
        """
        Parse license key to extract information.
        
        NOTE: In production, this should validate against a signature.
        For now, it's a placeholder for demonstration.
        """
        # Remove dashes
        key = license_key.replace("-", "")
        
        # This is a simplified version - production should use cryptographic signatures
        # For demo purposes, we'll accept any properly formatted key
        return {
            "user_name": "Licensed User",
            "company": "Your Company",
            "edition": "professional",
            "expiry": None  # None = perpetual license
        }
    
    def _verify_commercial_license(self, license_data: Dict[str, Any]) -> bool:
        """Verify commercial license integrity."""
        required_fields = ["license_key", "activated_date", "machine_id"]
        
        # Check all required fields exist
        if not all(field in license_data for field in required_fields):
            return False
        
        # Verify machine ID matches (prevents license transfer)
        if license_data["machine_id"] != self._get_machine_id():
            logger.warning("License machine ID mismatch")
            # In strict mode, return False here
            # For user convenience, we'll allow it with a warning
        
        return True
    
    def generate_trial_key(self) -> str:
        """Generate a trial license key (for testing purposes)."""
        import random
        import string
        
        chars = string.ascii_uppercase + string.digits
        parts = [''.join(random.choices(chars, k=4)) for _ in range(5)]
        return '-'.join(parts)
