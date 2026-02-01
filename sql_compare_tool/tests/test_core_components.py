"""Unit tests for core SQL Compare Tool components."""
from __future__ import annotations

import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from core.database import DatabaseConnection
from core.comparator import SchemaComparator, STATUS
from core.diff_generator import DiffGenerator
from utils.config import Config


class TestDatabaseConnection(unittest.TestCase):
    """Test database connection functionality."""
    
    def test_server_validation_rejects_invalid_characters(self):
        """Test that invalid characters in server name are rejected."""
        with self.assertRaises(ValueError):
            conn = DatabaseConnection(
                server="server;DROP TABLE",
                database="test",
                auth_type="sql"
            )
            conn._conn_str()
    
    def test_server_validation_accepts_valid_names(self):
        """Test that valid server names are accepted."""
        conn = DatabaseConnection(
            server="localhost",
            database="test",
            auth_type="sql",
            username="sa",
            password="test"
        )
        conn_str = conn._conn_str()
        self.assertIn("tcp:localhost", conn_str)
    
    def test_empty_server_raises_error(self):
        """Test that empty server name raises ValueError."""
        with self.assertRaises(ValueError):
            conn = DatabaseConnection(
                server="",
                database="test",
                auth_type="sql"
            )
            conn._conn_str()
    
    def test_connection_string_includes_encryption(self):
        """Test that connection string includes encryption settings."""
        conn = DatabaseConnection(
            server="localhost",
            database="test",
            auth_type="sql",
            username="sa",
            password="test123"
        )
        conn_str = conn._conn_str()
        self.assertIn("Encrypt=yes", conn_str)
        self.assertIn("UID=sa", conn_str)


class TestSchemaComparator(unittest.TestCase):
    """Test schema comparison logic."""
    
    def test_identical_schemas(self):
        """Test comparison of identical schemas."""
        source = {
            "tables": {"dbo.Users": {"columns": [{"name": "ID", "type": "int"}]}},
            "views": {}
        }
        target = source.copy()
        
        comparator = SchemaComparator(source, target)
        results = comparator.compare()
        
        # All items should be identical
        for obj_type, items in results.items():
            for item in items:
                self.assertEqual(item["status"], STATUS["IDENTICAL"])
    
    def test_missing_table_in_target(self):
        """Test detection of table missing in target."""
        source = {
            "tables": {"dbo.Users": {"columns": []}},
        }
        target = {
            "tables": {},
        }
        
        comparator = SchemaComparator(source, target)
        results = comparator.compare()
        
        self.assertEqual(len(results["tables"]), 1)
        self.assertEqual(results["tables"][0]["status"], STATUS["MISSING_IN_TARGET"])
    
    def test_missing_table_in_source(self):
        """Test detection of table missing in source."""
        source = {
            "tables": {},
        }
        target = {
            "tables": {"dbo.Users": {"columns": []}},
        }
        
        comparator = SchemaComparator(source, target)
        results = comparator.compare()
        
        self.assertEqual(len(results["tables"]), 1)
        self.assertEqual(results["tables"][0]["status"], STATUS["MISSING_IN_SOURCE"])
    
    def test_summary_counts(self):
        """Test that summary provides correct counts."""
        source = {
            "tables": {
                "dbo.Table1": {"columns": []},
                "dbo.Table2": {"columns": [{"name": "ID"}]}
            }
        }
        target = {
            "tables": {
                "dbo.Table1": {"columns": []},
                "dbo.Table2": {"columns": [{"name": "ID", "type": "int"}]}
            }
        }
        
        comparator = SchemaComparator(source, target)
        results = comparator.compare()
        summary = comparator.summarize(results)
        
        self.assertEqual(summary[STATUS["IDENTICAL"]], 1)
        self.assertEqual(summary[STATUS["DIFFERENT"]], 1)


class TestDiffGenerator(unittest.TestCase):
    """Test diff generation functionality."""
    
    def test_identical_content(self):
        """Test diff of identical content."""
        source = "CREATE TABLE Test (ID INT)"
        target = "CREATE TABLE Test (ID INT)"
        
        generator = DiffGenerator(source, target)
        diff = generator.side_by_side()
        
        # All lines should be marked as 'same'
        for left, right, tag in diff:
            self.assertEqual(tag, "same")
    
    def test_added_lines(self):
        """Test detection of added lines."""
        source = "Line 1"
        target = "Line 1\nLine 2"
        
        generator = DiffGenerator(source, target)
        diff = generator.side_by_side()
        
        self.assertEqual(len(diff), 2)
        self.assertEqual(diff[1][2], "del")  # Line added in target
    
    def test_deleted_lines(self):
        """Test detection of deleted lines."""
        source = "Line 1\nLine 2"
        target = "Line 1"
        
        generator = DiffGenerator(source, target)
        diff = generator.side_by_side()
        
        self.assertEqual(len(diff), 2)
        self.assertEqual(diff[1][2], "add")  # Line removed from target


class TestConfig(unittest.TestCase):
    """Test configuration management."""
    
    def test_default_config_loaded(self):
        """Test that default configuration is loaded."""
        config = Config(config_file="test_config.json")
        
        self.assertIn("app", config.config)
        self.assertIn("database", config.config)
    
    def test_get_value(self):
        """Test getting configuration values."""
        config = Config(config_file="test_config.json")
        
        value = config.get("database", "default_timeout", 30)
        self.assertEqual(value, 30)
    
    def test_set_value(self):
        """Test setting configuration values."""
        config = Config(config_file="test_config.json")
        
        config.set("database", "default_timeout", 60)
        value = config.get("database", "default_timeout")
        self.assertEqual(value, 60)
    
    def test_get_section(self):
        """Test getting entire configuration section."""
        config = Config(config_file="test_config.json")
        
        db_config = config.get_section("database")
        self.assertIsInstance(db_config, dict)
        self.assertIn("default_timeout", db_config)


if __name__ == "__main__":
    unittest.main()
