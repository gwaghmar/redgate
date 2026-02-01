"""Configuration management for SQL Compare Tool."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional


class Config:
    """Application configuration management using JSON."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize configuration.
        
        Args:
            config_path: Path to configuration file. If None, uses default location.
        """
        if config_path is None:
            # Default to config directory in project root
            self.config_path = Path(__file__).parent.parent.parent / "config" / "settings.json"
        else:
            self.config_path = Path(config_path)
        
        self._config: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from file or create with defaults."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading config: {e}. Using defaults.")
                self._config = self._get_defaults()
        else:
            # Create config file with defaults
            self._config = self._get_defaults()
            self._save_config()
    
    def _save_config(self) -> None:
        """Save current configuration to file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self._config, f, indent=2)
    
    def _get_defaults(self) -> Dict[str, Any]:
        """Get default configuration values."""
        return {
            "app": {
                "name": "SQL Compare Tool",
                "version": "1.0.0",
                "theme": "dark-blue"
            },
            "database": {
                "connection_timeout": 30,
                "command_timeout": 300,
                "default_auth_type": "Windows"
            },
            "comparison": {
                "ignore_case": False,
                "ignore_whitespace": True,
                "ignore_comments": True,
                "compare_permissions": True
            },
            "cache": {
                "enabled": True,
                "max_age_days": 7,
                "max_size_mb": 100
            },
            "logging": {
                "level": "INFO",
                "max_file_size_mb": 10,
                "backup_count": 5
            }
        }
    
    def get(self, section: str, key: Optional[str] = None, default: Any = None) -> Any:
        """Get configuration value.
        
        Args:
            section: Configuration section name
            key: Optional key within section. If None, returns entire section.
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        if section not in self._config:
            return default
        
        if key is None:
            return self._config[section]
        
        return self._config[section].get(key, default)
    
    def set(self, section: str, key: str, value: Any) -> None:
        """Set configuration value.
        
        Args:
            section: Configuration section name
            key: Key within section
            value: Value to set
        """
        if section not in self._config:
            self._config[section] = {}
        
        self._config[section][key] = value
        self._save_config()
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get entire configuration section.
        
        Args:
            section: Section name
            
        Returns:
            Section dictionary or empty dict if not found
        """
        return self._config.get(section, {})
    
    def reload(self) -> None:
        """Reload configuration from file."""
        self._load_config()
