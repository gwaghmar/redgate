import json
import os
import sys

# Ensure project root is on sys.path so "sql_compare_tool" package is importable
CURRENT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sql_compare_tool.core.comparator import SchemaComparator
from sql_compare_tool.core.diff_generator import DiffGenerator
from sql_compare_tool.core.script_generator import ScriptGenerator


def test_schema_comparator_basic_statuses():
    source = {
        "tables": {
            "dbo.Table1": {"columns": ["id"]},
            "dbo.TableOnlyInSource": {"columns": []},
        }
    }
    target = {
        "tables": {
            "dbo.Table1": {"columns": ["id"]},
            "dbo.TableOnlyInTarget": {"columns": []},
        }
    }

    comp = SchemaComparator(source, target)
    results = comp.compare()
    tables = {item["name"]: item for item in results["tables"]}

    assert tables["dbo.Table1"]["status"] == "IDENTICAL"
    assert tables["dbo.TableOnlyInSource"]["status"] == "MISSING_IN_TARGET"
    assert tables["dbo.TableOnlyInTarget"]["status"] == "MISSING_IN_SOURCE"

    # DeepDiff JSON for identical objects should be empty string
    assert not tables["dbo.Table1"].get("details", {}).get("diff")


def test_schema_comparator_summary_counts():
    source = {"tables": {"dbo.A": {"v": 1}, "dbo.B": {"v": 2}}}
    target = {"tables": {"dbo.A": {"v": 1}, "dbo.B": {"v": 3}}}
    comp = SchemaComparator(source, target)
    results = comp.compare()
    summary = SchemaComparator.summarize(results)

    assert summary["IDENTICAL"] == 1
    assert summary["DIFFERENT"] == 1


def test_diff_generator_side_by_side_tags():
    left = "CREATE TABLE dbo.T(\n id int,\n name nvarchar(50)\n)"
    right = "CREATE TABLE dbo.T(\n id int,\n full_name nvarchar(50)\n)"

    diff = DiffGenerator(left, right).side_by_side()

    # There should be at least one 'chg' line for the column rename
    assert any(tag == "chg" for _l, _r, tag in diff)


def test_script_generator_deploy_options_toggle_phases():
    # Minimal comparison result that would normally trigger all phases
    results = {
        "tables": [
            {"name": "dbo.NewTable", "status": "MISSING_IN_TARGET", "details": {
                "columns": [],
                "indexes": [],
                "primary_key": None,
                "foreign_keys": []
            }},
        ],
        "unique_constraints": [],
        "check_constraints": [],
        "default_constraints": [],
        "views": [],
        "procedures": [],
        "functions": [],
        "triggers": [],
        "synonyms": [],
    }
    source_meta = {"tables": {"dbo.NewTable": {
        "columns": [
            {"name": "id", "data_type": "int", "max_length": None, "precision": None, "scale": None, "is_nullable": False},
        ],
        "indexes": [],
        "primary_key": None,
        "foreign_keys": []
    }}}

    # Disable drop and misc phases, and disable rollback
    opts = {
        "include_drop_phase": False,
        "include_misc_phase": False,
        "include_rollback_section": False,
    }

    script = ScriptGenerator(results, source_meta, "TestDb", deploy_options=opts).generate()

    # Phase 1 and 5 headers should not appear
    assert "PHASE 1: DROP EXTRA OBJECTS" not in script
    assert "PHASE 5: MISCELLANEOUS OBJECTS" not in script

    # Table creation header should still be present
    assert "PHASE 2: TABLES AND COLUMNS" in script

    # Rollback section header should be omitted
    assert "ROLLBACK SCRIPT (Generated)" not in script


def test_script_generator_wrap_in_transaction_flag():
    results = {"tables": []}
    source_meta = {"tables": {}}

    script_tx = ScriptGenerator(results, source_meta, "Db1", deploy_options={"wrap_in_transaction": True}).generate()
    script_no_tx = ScriptGenerator(results, source_meta, "Db1", deploy_options={"wrap_in_transaction": False}).generate()

    # Deployment section should be wrapped in a transaction when flag is True
    assert "BEGIN TRANSACTION;" in script_tx
    assert "COMMIT TRANSACTION;" in script_tx

    # For wrap_in_transaction=False, the main deployment section should not
    # start a transaction, but the rollback section may still use one.
    deploy_only = script_no_tx.split("-- ROLLBACK SCRIPT (Generated)")[0]
    assert "BEGIN TRANSACTION;" not in deploy_only
    assert "COMMIT TRANSACTION;" not in deploy_only
    assert "no transaction wrapping" in deploy_only
