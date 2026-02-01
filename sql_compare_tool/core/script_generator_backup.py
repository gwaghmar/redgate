from __future__ import annotations

from typing import Dict, List, Any, Tuple


































































































































from utils.logger import get_logger

logger = get_logger(__name__)


class ScriptGenerator:
    """Advanced deployment script generator with proper ALTER TABLE support.
    
    Generates deployment scripts for schema differences including:
    - ALTER TABLE for column modifications
    - Constraint handling (PK, FK, Check, Default, Unique)
    - Index creation/modification/deletion
    - View/Procedure/Function CREATE/ALTER
    - Proper dependency ordering
    
    Behaviour can be controlled via *deployment options*, allowing the
    caller to toggle drop phases, constraint/index creation, misc
    objects, transaction wrapping, and rollback generation.
    """

    def __init__(
        self,
        comparison_result: Dict[str, List[Dict]],
        source_metadata: Dict[str, Any],
        target_db: str,
        deploy_options: Dict[str, Any] | None = None,
    ) -> None:
        self.results = comparison_result
        self.source_metadata = source_metadata
        self.target_db = target_db
        # Default deployment options; callers can override selectively.
        defaults = {
            "wrap_in_transaction": True,
            "include_drop_phase": True,
            "include_table_phase": True,
            "include_constraint_phase": True,
            "include_programmability_phase": True,
            "include_misc_phase": True,
            "include_rollback_section": True,
        }
        self.deploy_options: Dict[str, Any] = defaults
        if deploy_options:
            self.deploy_options.update(deploy_options)

    def generate(self) -> str:
        """Generate complete deployment script."""
        logger.info(f"Generating deployment script for database: {self.target_db}")
        lines: List[str] = [
            "-- ==============================================================================",
            "-- SQL Compare Tool - Deployment Script",
            f"-- Target Database: {self.target_db}",
            "-- ==============================================================================",
            "",
            f"USE [{self.target_db}];",
            "GO",
            "",
            "SET NOCOUNT ON;",
            "SET XACT_ABORT ON;",
            "SET ANSI_NULLS ON;",
            "SET QUOTED_IDENTIFIER ON;",
            "",
            "PRINT 'Starting deployment...';",
            "PRINT '';",
            "",
        ]

        if self.deploy_options.get("wrap_in_transaction", True):
            lines.append("BEGIN TRANSACTION;")
            lines.append("")

        # Phase 1: Drop objects that exist only in target (cleanup)
        if self.deploy_options.get("include_drop_phase", True):
            lines.extend(self._generate_drop_phase())
        
        # Phase 2: Create/Alter tables and columns
        if self.deploy_options.get("include_table_phase", True):
            lines.extend(self._generate_table_phase())
        
        # Phase 3: Create/modify constraints and indexes
        if self.deploy_options.get("include_constraint_phase", True):
            lines.extend(self._generate_constraint_phase())
        
        # Phase 4: Create/alter views, functions, procedures, triggers
        if self.deploy_options.get("include_programmability_phase", True):
            lines.extend(self._generate_programmability_phase())
        
        # Phase 5: Synonyms, extended properties, etc.
        if self.deploy_options.get("include_misc_phase", True):
            lines.extend(self._generate_misc_phase())

        if self.deploy_options.get("wrap_in_transaction", True):
            lines.extend([
                "",
                "COMMIT TRANSACTION;",
                "PRINT 'Deployment completed successfully.';",
                "GO",
            ])
        else:
            lines.extend([
                "",
                "PRINT 'Deployment script generation completed (no transaction wrapping).';",
                "GO",
            ])

        # Append rollback script section (generated from the same diff),
        # so users have a ready-made way to revert structural changes.
        rollback_lines: List[str] = []
        if self.deploy_options.get("include_rollback_section", True):
            rollback_lines = self._generate_rollback()

        return "\n".join(lines + (["", ""] + rollback_lines if rollback_lines else []))

    def _generate_drop_phase(self) -> List[str]:
        """Phase 1: Drop objects that exist only in target."""
        lines = [
            "-- ==============================================================================",
            "-- PHASE 1: DROP EXTRA OBJECTS (MISSING_IN_SOURCE)",
            "-- ==============================================================================",
            ""
        ]
        
        # First, drop foreign keys from tables (must be first due to dependencies)
        tables = self.results.get("tables", [])
        fks_to_drop = []
        for table_item in tables:
            if table_item.get("status") == "MISSING_IN_SOURCE":
                # This whole table will be dropped, its FKs will go with it
                continue
            elif table_item.get("status") == "DIFFERENT":
                # Check if there are FKs in target that don't exist in source
                table_name = table_item.get("name", "")
                details = table_item.get("details", {})
                source = details.get("source", {})
                target = details.get("target", {})
                source_fks = {fk.get("name"): fk for fk in source.get("foreign_keys", [])}
                target_fks = {fk.get("name"): fk for fk in target.get("foreign_keys", [])}
                
                for fk_name, fk in target_fks.items():
                    if fk_name not in source_fks:
                        fks_to_drop.append({"table": table_name, "fk_name": fk_name})
        
        if fks_to_drop:
            lines.append(f"-- Dropping {len(fks_to_drop)} foreign keys")
            for fk_info in fks_to_drop:
                lines.append(f"ALTER TABLE {fk_info['table']} DROP CONSTRAINT [{fk_info['fk_name']}];")
            lines.append("")
        
        # Drop other objects in reverse dependency order
        for obj_type in ["triggers", "views", "procedures", "functions", "synonyms"]:
            items = [item for item in self.results.get(obj_type, []) if item.get("status") == "MISSING_IN_SOURCE"]
            if items:
                lines.append(f"-- Dropping {len(items)} {obj_type}")
                for item in items:
                    name = item.get("name", "")
                    lines.extend(self._drop_statement(obj_type, name))
                lines.append("")
        
        return lines

    def _generate_table_phase(self) -> List[str]:
        """Phase 2: Create new tables and modify existing columns."""
        lines = [
            "-- ==============================================================================",
            "-- PHASE 2: TABLES AND COLUMNS",
            "-- ==============================================================================",
            ""
        ]
        
        tables = self.results.get("tables", [])
        
        # Create new tables
        new_tables = [t for t in tables if t.get("status") == "MISSING_IN_TARGET"]
        if new_tables:
            lines.append(f"-- Creating {len(new_tables)} new tables")
            for table in new_tables:
                name = table.get("name", "")
                lines.extend(self._create_table_statement(name))
            lines.append("")
        
        # Alter existing tables (column changes)
        modified_tables = [t for t in tables if t.get("status") == "DIFFERENT"]
        if modified_tables:
            lines.append(f"-- Modifying {len(modified_tables)} existing tables")
            for table in modified_tables:
                name = table.get("name", "")
                details = table.get("details", {})
                lines.extend(self._alter_table_columns(name, details))
            lines.append("")
        
        return lines

    def _generate_constraint_phase(self) -> List[str]:
        """Phase 3: Create/modify constraints and indexes."""
        lines = [
            "-- ==============================================================================",
            "-- PHASE 3: CONSTRAINTS AND INDEXES",
            "-- ==============================================================================",
            ""
        ]
        
        # Optimize: Single pass through tables to extract PKs, indexes, and FKs
        tables = self.results.get("tables", [])
        pks_to_create = []
        indexes_to_create = []
        fks_to_create = []
        
        for table_item in tables:
            if table_item.get("status") in ("MISSING_IN_TARGET", "DIFFERENT"):
                table_name = table_item.get("name", "")
                details = table_item.get("details", {})
                
                # Extract source data based on status
                if table_item.get("status") == "MISSING_IN_TARGET":
                    # For new tables, details contains the source directly
                    pk = details.get("primary_key")
                    indexes = details.get("indexes", [])
                    fks = details.get("foreign_keys", [])
                else:
                    # For different tables, extract from source
                    source = details.get("source", {})
                    pk = source.get("primary_key")
                    indexes = source.get("indexes", [])
                    fks = source.get("foreign_keys", [])
                
                # Collect primary key
                if pk:
                    pks_to_create.append({"table_name": table_name, "pk": pk})
                
                # Collect indexes
                for idx in indexes:
                    indexes_to_create.append({"table_name": table_name, "index": idx})
                
                # Collect foreign keys
                for fk in fks:
                    fks_to_create.append({"table_name": table_name, "fk": fk})
        
        # Primary Keys
        if pks_to_create:
            lines.append(f"-- Adding/modifying {len(pks_to_create)} primary keys")
            for pk_info in pks_to_create:
                lines.extend(self._create_primary_key_from_table_metadata(pk_info["table_name"], pk_info["pk"]))
            lines.append("")
        
        # Unique Constraints
        unique_constraints = self.results.get("unique_constraints", [])
        if unique_constraints:
            new_uq = [u for u in unique_constraints if u.get("status") == "MISSING_IN_TARGET"]
            if new_uq:
                lines.append(f"-- Adding {len(new_uq)} unique constraints")
                for uq in new_uq:
                    lines.extend(self._create_unique_constraint_statement(uq))
                lines.append("")
        
        # Check Constraints
        check_constraints = self.results.get("check_constraints", [])
        if check_constraints:
            new_cc = [c for c in check_constraints if c.get("status") == "MISSING_IN_TARGET"]
            if new_cc:
                lines.append(f"-- Adding {len(new_cc)} check constraints")
                for cc in new_cc:
                    lines.extend(self._create_check_constraint_statement(cc))
                lines.append("")
        
        # Default Constraints
        default_constraints = self.results.get("default_constraints", [])
        if default_constraints:
            new_def = [d for d in default_constraints if d.get("status") == "MISSING_IN_TARGET"]
            if new_def:
                lines.append(f"-- Adding {len(new_def)} default constraints")
                for df in new_def:
                    lines.extend(self._create_default_constraint_statement(df))
                lines.append("")
        
        # Indexes (already collected in single pass above)
        if indexes_to_create:
            lines.append(f"-- Creating/modifying {len(indexes_to_create)} indexes")
            for idx_info in indexes_to_create:
                lines.extend(self._create_index_from_table_metadata(idx_info["table_name"], idx_info["index"]))
            lines.append("")
        
        # Foreign Keys (last due to dependencies, already collected above)
        if fks_to_create:
            lines.append(f"-- Adding {len(fks_to_create)} foreign keys")
            for fk_info in fks_to_create:
                lines.extend(self._create_foreign_key_from_table_metadata(fk_info["table_name"], fk_info["fk"]))
            lines.append("")
        
        return lines

    def _generate_programmability_phase(self) -> List[str]:
        """Phase 4: Create/alter views, procedures, functions, triggers."""
        lines = [
            "-- ==============================================================================",
            "-- PHASE 4: PROGRAMMABILITY OBJECTS",
            "-- ==============================================================================",
            ""
        ]
        
        for obj_type, items in self._ordered_programmability_items():
            if items:
                lines.append(f"-- Creating/modifying {len(items)} {obj_type}")
                for item in items:
                    name = item.get("name", "")
                    details = item.get("details", {})
                    lines.extend(self._create_programmability_statement(obj_type, name, details))
                lines.append("")
        
        return lines

    def _generate_misc_phase(self) -> List[str]:
        """Phase 5: Synonyms, extended properties, etc."""
        lines = [
            "-- ==============================================================================",
            "-- PHASE 5: MISCELLANEOUS OBJECTS",
            "-- ==============================================================================",
            ""
        ]
        
        # Create synonyms that are missing in target
        synonyms = self.results.get("synonyms", [])
        new_synonyms = [s for s in synonyms if s.get("status") == "MISSING_IN_TARGET"]
        if new_synonyms:
            lines.append(f"-- Creating {len(new_synonyms)} synonyms")
            for syn in new_synonyms:
                name = syn.get("name", "")
                details = syn.get("details", {})
                source_syn = details.get("source", {})
                base_obj = source_syn.get("base_object_name", "")
                if base_obj:
                    lines.append(f"CREATE SYNONYM {name} FOR {base_obj};")
                    lines.append("GO")
            lines.append("")
        
        return lines

    def _create_table_statement(self, table_name: str) -> List[str]:
        """Generate CREATE TABLE statement with full column property support."""
        lines = [f"PRINT 'Creating table {table_name}...';"]
        
        # Get table metadata from source
        tables_metadata = self.source_metadata.get("tables", {})
        table_data = tables_metadata.get(table_name, {})
        columns = table_data.get("columns", [])
        
        if not columns:
            return [f"-- TODO: CREATE TABLE {table_name} (no column metadata available)"]
        
        lines.append(f"CREATE TABLE {table_name} (")
        
        col_defs = []
        for col in columns:
            col_def = self._format_full_column_definition(col)
            col_defs.append(f"    {col_def}")
        
        lines.append(",\n".join(col_defs))
        lines.append(");")
        lines.append("GO")
        lines.append("")
        
        return lines
    
    def _format_full_column_definition(self, col: Dict[str, Any]) -> str:
        """Generate complete column definition including all properties."""
        col_name = col.get("name", "")
        parts = [f"[{col_name}]"]
        
        # Handle computed columns differently
        if col.get("is_computed"):
            computed_def = col.get("computed_definition", "")
            persisted = " PERSISTED" if col.get("is_persisted") else ""
            return f"[{col_name}] AS {computed_def}{persisted}"
        
        # Regular column: data type
        type_str = self._format_column_type(col)
        parts.append(type_str)
        
        # Collation (before NULL/NOT NULL)
        if col.get("collation"):
            parts.append(f"COLLATE {col.get('collation')}")
        
        # SPARSE
        if col.get("is_sparse"):
            parts.append("SPARSE")
        
        # NULL/NOT NULL
        nullable_str = "NULL" if self._is_nullable(col) else "NOT NULL"
        parts.append(nullable_str)
        
        # IDENTITY
        if col.get("is_identity"):
            seed = col.get("identity_seed", 1)
            incr = col.get("identity_increment", 1)
            parts.append(f"IDENTITY({seed},{incr})")
        
        # ROWGUIDCOL
        if col.get("is_rowguidcol"):
            parts.append("ROWGUIDCOL")
        
        # DEFAULT constraint
        default_val = col.get("default_value")
        if default_val:
            parts.append(f"DEFAULT {default_val}")
        
        return " ".join(parts)
    
    def _create_table_statement(self, table_name: str) -> List[str]:
        """Generate CREATE TABLE statement with full column property support."""
        lines = [f"PRINT 'Creating table {table_name}...';"]
        
        # Get table metadata from source
        tables_metadata = self.source_metadata.get("tables", {})
        table_data = tables_metadata.get(table_name, {})
        columns = table_data.get("columns", [])
        
        if not columns:
            return [f"-- TODO: CREATE TABLE {table_name} (no column metadata available)"]
        
        lines.append(f"CREATE TABLE {table_name} (")
        
        col_defs = []
        for col in columns:
            col_def = self._format_full_column_definition(col)
            col_defs.append(f"    {col_def}")
        
        lines.append(",\n".join(col_defs))
        lines.append(");")
        lines.append("GO")
        lines.append("")
        
        return lines

    def _alter_table_columns(self, table_name: str, details: Dict) -> List[str]:
        """Generate ALTER TABLE statements for column modifications."""
        lines = [f"PRINT 'Modifying table {table_name}...';"]

        parts = table_name.split(".")
        if len(parts) != 2:
            return [f"-- Unable to ALTER TABLE {table_name} (invalid name format)"]

        source_table = (details.get("source") or {})
        target_table = (details.get("target") or {})

        added, removed, changed = self._compare_columns(source_table, target_table)

        if not added and not removed and not changed:
            lines.append(f"-- No column-level differences detected for {table_name}")
            lines.append("")
            return lines

        # New columns in source -> ADD COLUMN on target
        for col in added:
            col_def = self._format_full_column_definition(col)
            lines.append(f"ALTER TABLE {table_name} ADD {col_def};")

        # Columns missing in source (only in target) -> DROP COLUMN (data loss!)
        for col in removed:
            col_name = col.get("name", "")
            lines.append(
                f"-- WARNING: Dropping column [{col_name}] from {table_name} may cause data loss.")
            lines.append(f"ALTER TABLE {table_name} DROP COLUMN [{col_name}];")

        # Columns present in both but with different signatures -> ALTER/DROP+ADD
        for src_col, tgt_col in changed:
            col_name = src_col.get("name", "")
            
            # Check if this is an identity or computed column change (can't ALTER these)
            src_identity = src_col.get("is_identity", False)
            tgt_identity = tgt_col.get("is_identity", False)
            src_computed = src_col.get("is_computed", False)
            tgt_computed = tgt_col.get("is_computed", False)
            
            if src_identity != tgt_identity or src_computed != tgt_computed:
                # Must use DROP + ADD for identity/computed changes
                lines.append(
                    f"-- WARNING: Cannot ALTER identity/computed column [{col_name}]. Using DROP + ADD pattern.")
                lines.append(f"-- This may cause data loss. Consider manual migration if data preservation is needed.")
                lines.append(f"ALTER TABLE {table_name} DROP COLUMN [{col_name}];")
                col_def = self._format_full_column_definition(src_col)
                lines.append(f"ALTER TABLE {table_name} ADD {col_def};")
            else:
                # Regular ALTER COLUMN
                type_str = self._format_column_type(src_col)
                nullable_str = "NULL" if self._is_nullable(src_col) else "NOT NULL"
                
                # Check for collation change
                collation_changed = src_col.get("collation") != tgt_col.get("collation")
                collate_clause = f" COLLATE {src_col.get('collation')}" if src_col.get("collation") and collation_changed else ""
                
                lines.append(
                    f"-- NOTE: Changing definition of column [{col_name}] on {table_name}. Review for potential data impact."
                )
                lines.append(
                    f"ALTER TABLE {table_name} ALTER COLUMN [{col_name}] {type_str}{collate_clause} {nullable_str};"
                )

        lines.append("")
        return lines

    def _create_primary_key_from_table_metadata(self, table_name: str, pk: Dict) -> List[str]:
        """Generate ALTER TABLE ADD PRIMARY KEY statement from table metadata.
        
        Args:
            table_name: Full table name (e.g., 'dbo.TableName')
            pk: Primary key dictionary with 'name' and 'columns' keys
        """
        pk_name = pk.get("name", "")
        columns = pk.get("columns", [])
        
        if not columns:
            return [f"-- TODO: CREATE PRIMARY KEY on {table_name} (no column information)"]
        
        col_list = ", ".join([f"[{col}]" for col in columns])
        
        return [
            f"PRINT 'Adding primary key {pk_name} on {table_name}...';",
            f"ALTER TABLE {table_name} ADD CONSTRAINT [{pk_name}] PRIMARY KEY ({col_list});",
            "GO",
            ""
        ]

    def _create_unique_constraint_statement(self, uq_item: Dict) -> List[str]:
        """Generate ALTER TABLE ADD UNIQUE CONSTRAINT statement."""
        name = uq_item.get("name", "")
        details = uq_item.get("details", {})
        source_uq = details.get("source", {})
        columns = source_uq.get("columns", [])
        
        if not columns:
            return [f"-- TODO: CREATE UNIQUE CONSTRAINT {name} (no column information)"]
        
        parts = name.rsplit(".", 1)
        if len(parts) != 2:
            return [f"-- TODO: CREATE UNIQUE CONSTRAINT {name} (invalid name format)"]
        
        table_name, uq_name = parts
        col_list = ", ".join([f"[{col}]" for col in columns])
        
        return [
            f"ALTER TABLE {table_name} ADD CONSTRAINT [{uq_name}] UNIQUE ({col_list});",
            ""
        ]

    def _create_check_constraint_statement(self, chk_item: Dict) -> List[str]:
        """Generate ALTER TABLE ADD CHECK CONSTRAINT statement."""
        name = chk_item.get("name", "")
        details = chk_item.get("details", {})
        source_chk = details.get("source", {})
        definition = source_chk.get("definition", "")
        
        if not definition:
            return [f"-- TODO: CREATE CHECK CONSTRAINT {name} (no definition)"]
        
        parts = name.rsplit(".", 1)
        if len(parts) != 2:
            return [f"-- TODO: CREATE CHECK CONSTRAINT {name} (invalid name format)"]
        
        table_name, chk_name = parts
        
        return [
            f"ALTER TABLE {table_name} ADD CONSTRAINT [{chk_name}] CHECK {definition};",
            ""
        ]

    def _create_default_constraint_statement(self, df_item: Dict) -> List[str]:
        """Generate ALTER TABLE ADD DEFAULT CONSTRAINT statement."""
        name = df_item.get("name", "")
        details = df_item.get("details", {})
        source_df = details.get("source", {})
        column = source_df.get("column", "")
        definition = source_df.get("definition", "")
        
        if not column or not definition:
            return [f"-- TODO: CREATE DEFAULT CONSTRAINT {name} (missing information)"]
        
        parts = name.rsplit(".", 1)
        if len(parts) != 2:
            return [f"-- TODO: CREATE DEFAULT CONSTRAINT {name} (invalid name format)"]
        
        table_name, df_name = parts
        
        return [
            f"ALTER TABLE {table_name} ADD CONSTRAINT [{df_name}] DEFAULT {definition} FOR [{column}];",
            ""
        ]

    def _create_foreign_key_statement(self, fk_item: Dict) -> List[str]:
        """Generate ALTER TABLE ADD FOREIGN KEY statement (legacy - for constraints list)."""
        name = fk_item.get("name", "")
        details = fk_item.get("details", {})
        source_fk = details.get("source", {})
        columns = source_fk.get("columns", [])
        ref_table = source_fk.get("referenced_table", "")
        ref_columns = source_fk.get("referenced_columns", [])
        delete_rule = source_fk.get("delete_rule", "NO_ACTION")
        update_rule = source_fk.get("update_rule", "NO_ACTION")
        
        if not columns or not ref_columns:
            return [f"-- TODO: CREATE FOREIGN KEY {name} (missing column information)"]
        
        parts = name.rsplit(".", 1)
        if len(parts) != 2:
            return [f"-- TODO: CREATE FOREIGN KEY {name} (invalid name format)"]
        
        table_name, fk_name = parts
        col_list = ", ".join([f"[{col}]" for col in columns])
        ref_col_list = ", ".join([f"[{col}]" for col in ref_columns])
        
        # Format rules
        delete_clause = "" if delete_rule == "NO_ACTION" else f" ON DELETE {delete_rule.replace('_', ' ')}"
        update_clause = "" if update_rule == "NO_ACTION" else f" ON UPDATE {update_rule.replace('_', ' ')}"
        
        return [
            f"ALTER TABLE {table_name} ADD CONSTRAINT [{fk_name}] ",
            f"    FOREIGN KEY ({col_list})",
            f"    REFERENCES {ref_table} ({ref_col_list}){delete_clause}{update_clause};",
            "GO",
            ""
        ]

    def _create_foreign_key_from_table_metadata(self, table_name: str, fk: Dict) -> List[str]:
        """Generate ALTER TABLE ADD FOREIGN KEY statement from table metadata.
        
        Args:
            table_name: Full table name (e.g., 'dbo.TableName')
            fk: Foreign key dictionary from table metadata
        """
        fk_name = fk.get("name", "")
        columns = fk.get("columns", [])
        ref_table = fk.get("referenced_table", "")
        ref_columns = fk.get("referenced_columns", [])
        delete_rule = fk.get("delete_rule", "NO_ACTION")
        update_rule = fk.get("update_rule", "NO_ACTION")
        
        if not columns or not ref_columns:
            return [f"-- TODO: CREATE FOREIGN KEY {fk_name} on {table_name} (missing column information)"]
        
        col_list = ", ".join([f"[{col}]" for col in columns])
        ref_col_list = ", ".join([f"[{col}]" for col in ref_columns])
        
        # Format rules
        delete_clause = "" if delete_rule == "NO_ACTION" else f" ON DELETE {delete_rule.replace('_', ' ')}"
        update_clause = "" if update_rule == "NO_ACTION" else f" ON UPDATE {update_rule.replace('_', ' ')}"
        
        return [
            f"ALTER TABLE {table_name} ADD CONSTRAINT [{fk_name}] ",
            f"    FOREIGN KEY ({col_list})",
            f"    REFERENCES {ref_table} ({ref_col_list}){delete_clause}{update_clause};",
            "GO",
            ""
        ]

    def _create_index_statement(self, idx_item: Dict) -> List[str]:
        """Generate CREATE INDEX statement (legacy - for separate index list)."""
        name = idx_item.get("name", "")
        details = idx_item.get("details", {})
        source_idx = details.get("source", {})
        columns = source_idx.get("columns", [])
        included_columns = source_idx.get("included_columns", [])
        is_unique = source_idx.get("is_unique", False)
        type_desc = source_idx.get("type_desc", "NONCLUSTERED")
        
        if not columns:
            return [f"-- TODO: CREATE INDEX {name} (no column information)"]
        
        parts = name.rsplit(".", 1)
        if len(parts) != 2:
            return [f"-- TODO: CREATE INDEX {name} (invalid name format)"]
        
        table_name, idx_name = parts
        col_list = ", ".join([f"[{col}]" for col in columns])
        
        unique_str = "UNIQUE " if is_unique else ""
        include_str = ""
        if included_columns:
            include_cols = ", ".join([f"[{col}]" for col in included_columns])
            include_str = f" INCLUDE ({include_cols})"
        
        return [
            f"CREATE {unique_str}{type_desc} INDEX [{idx_name}] ON {table_name} ({col_list}){include_str};",
            ""
        ]

    def _create_index_from_table_metadata(self, table_name: str, idx: Dict) -> List[str]:
        """Generate CREATE INDEX statement from table metadata.
        
        Args:
            table_name: Full table name (e.g., 'dbo.TableName')
            idx: Index dictionary from table metadata
        """
        idx_name = idx.get("name", "")
        columns = idx.get("columns", [])
        included_columns = idx.get("included_columns", [])
        is_unique = idx.get("is_unique", False)
        is_primary_key = idx.get("is_primary_key", False)
        type_desc = idx.get("type_desc", "NONCLUSTERED")
        
        # Skip primary key indexes (handled separately)
        if is_primary_key:
            return []
        
        if not columns:
            return [f"-- TODO: CREATE INDEX {idx_name} on {table_name} (no column information)"]
        
        col_list = ", ".join([f"[{col}]" for col in columns])
        
        unique_str = "UNIQUE " if is_unique else ""
        include_str = ""
        if included_columns:
            include_cols = ", ".join([f"[{col}]" for col in included_columns])
            include_str = f" INCLUDE ({include_cols})"
        
        return [
            f"CREATE {unique_str}{type_desc} INDEX [{idx_name}] ON {table_name} ({col_list}){include_str};",
            ""
        ]

    def _create_programmability_statement(self, obj_type: str, name: str, details: Dict) -> List[str]:
        """Generate CREATE/ALTER statement for views, procedures, functions, triggers."""
        source = details.get("source", {})
        definition = source.get("definition", "")
        
        if not definition:
            return [f"-- TODO: CREATE {obj_type[:-1].upper()} {name} (no definition available)"]
        
        lines = [
            f"PRINT 'Creating/modifying {obj_type[:-1]} {name}...';",
            definition,
            "GO",
            ""
        ]
        
        return lines

    def _drop_statement(self, obj_type: str, name: str) -> List[str]:
        """Generate DROP statement for an object."""
        if obj_type == "views":
            return [f"IF OBJECT_ID('{name}', 'V') IS NOT NULL DROP VIEW {name};", "GO", ""]
        if obj_type == "procedures":
            return [f"IF OBJECT_ID('{name}', 'P') IS NOT NULL DROP PROCEDURE {name};", "GO", ""]
        if obj_type == "functions":
            return [f"IF OBJECT_ID('{name}', 'FN') IS NOT NULL DROP FUNCTION {name};", "GO", ""]
        if obj_type == "triggers":
            return [f"IF OBJECT_ID('{name}', 'TR') IS NOT NULL DROP TRIGGER {name};", "GO", ""]
        if obj_type == "synonyms":
            return [f"IF OBJECT_ID('{name}', 'SN') IS NOT NULL DROP SYNONYM {name};", "GO", ""]
        if obj_type == "tables":
            return [f"IF OBJECT_ID('{name}', 'U') IS NOT NULL DROP TABLE {name};", "GO", ""]
        return [f"-- TODO: drop {obj_type[:-1]} {name}", ""]

    # ------------------------------------------------------------------
    # Helpers: dependency ordering, column comparison, rollback script
    # ------------------------------------------------------------------

    def _ordered_programmability_items(self) -> List[Tuple[str, List[Dict[str, Any]]]]:
        """Return programmability objects ordered by inferred dependencies.

        Builds a simple dependency graph between programmable objects
        (functions, views, procedures, triggers) based on textual
        references in their SQL definitions, then performs a topological
        sort. This provides a practical dependency resolver without the
        complexity of a full T-SQL parser.
        """
        # Collect candidate objects to script
        node_by_name: Dict[str, Tuple[str, Dict[str, Any]]] = {}
        for obj_type in ["functions", "views", "procedures", "triggers"]:
            for item in self.results.get(obj_type, []):
                if item.get("status") not in ("MISSING_IN_TARGET", "DIFFERENT"):
                    continue
                name = item.get("name")
                if not name:
                    continue
                key = name.lower()
                node_by_name[key] = (obj_type, item)

        if not node_by_name:
            return []

        # Extract definitions for simple textual dependency scanning
        def_by_name: Dict[str, str] = {}
        for key, (_obj_type, item) in node_by_name.items():
            details = item.get("details", {}) or {}
            source = details.get("source", {}) or {}
            definition = (source.get("definition") or "").lower()
            def_by_name[key] = definition

        names = list(node_by_name.keys())
        adjacency: Dict[str, set[str]] = {n: set() for n in names}
        indegree: Dict[str, int] = {n: 0 for n in names}

        # Naive dependency detection: if definition of A contains the
        # fully-qualified name of B, treat A as depending on B.
        for a in names:
            def_a = def_by_name.get(a, "")
            if not def_a:
                continue
            for b in names:
                if a == b:
                    continue
                if b in def_a:
                    if b not in adjacency[a]:
                        adjacency[a].add(b)
                        indegree[b] += 1

        # Topological sort (Kahn's algorithm)
        ordered_keys: List[str] = []
        queue: List[str] = [n for n in names if indegree[n] == 0]

        while queue:
            node = queue.pop(0)
            ordered_keys.append(node)
            for dep in adjacency[node]:
                indegree[dep] -= 1
                if indegree[dep] == 0:
                    queue.append(dep)

        # If we detected a cycle or missed nodes, append remaining
        # in their original order as a safe fallback.
        if len(ordered_keys) < len(names):
            for n in names:
                if n not in ordered_keys:
                    ordered_keys.append(n)

        # Convert to the expected (obj_type, [item]) structure, keeping
        # the precise object ordering from the topological sort.
        ordered_items: List[Tuple[str, List[Dict[str, Any]]]] = []
        for key in ordered_keys:
            obj_type, item = node_by_name[key]
            ordered_items.append((obj_type, [item]))

        return ordered_items

    @staticmethod
    def _is_nullable(col: Dict[str, Any]) -> bool:
        nullable = col.get("is_nullable")
        if nullable is None:
            return True
        text = str(nullable).strip().upper()
        return text in ("YES", "Y", "TRUE", "1")

    def _format_column_type(self, col: Dict[str, Any]) -> str:
        data_type = (col.get("data_type") or "").lower()
        max_len = col.get("max_length")
        precision = col.get("precision")
        scale = col.get("scale")

        type_str = data_type.upper()

        if data_type in ("varchar", "nvarchar", "char", "nchar", "binary", "varbinary"):
            if max_len == -1:
                type_str += "(MAX)"
            elif max_len and max_len > 0:
                type_str += f"({max_len})"
        elif data_type in ("decimal", "numeric") and precision:
            if scale is not None:
                type_str += f"({precision},{scale})"
            else:
                type_str += f"({precision})"

        return type_str

    def _compare_columns(
        self, source_table: Dict[str, Any], target_table: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Tuple[Dict[str, Any], Dict[str, Any]]]]:
        """Compare columns between source and target table metadata.

        Returns (added, removed, changed) where:
        - added: columns present only in source
        - removed: columns present only in target
        - changed: columns present in both but with different signatures
        """
        src_cols = {c.get("name"): c for c in source_table.get("columns", []) if c.get("name")}
        tgt_cols = {c.get("name"): c for c in target_table.get("columns", []) if c.get("name")}

        added: List[Dict[str, Any]] = []
        removed: List[Dict[str, Any]] = []
        changed: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []

        for name, col in src_cols.items():
            if name not in tgt_cols:
                added.append(col)
            else:
                tgt_col = tgt_cols[name]
                if self._column_signature(col) != self._column_signature(tgt_col):
                    changed.append((col, tgt_col))

        for name, col in tgt_cols.items():
            if name not in src_cols:
                removed.append(col)

        return added, removed, changed

    def _column_signature(self, col: Dict[str, Any]) -> Tuple[Any, ...]:
        """Build a tuple representing the complete column definition including all properties."""
        return (
            (col.get("data_type") or "").lower(),
            col.get("max_length"),
            col.get("precision"),
            col.get("scale"),
            self._is_nullable(col),
            str(col.get("default_value")) if col.get("default_value") is not None else None,
            # Include new advanced properties
            col.get("is_identity", False),
            col.get("identity_seed") if col.get("is_identity") else None,
            col.get("identity_increment") if col.get("is_identity") else None,
            col.get("is_computed", False),
            col.get("computed_definition") if col.get("is_computed") else None,
            col.get("is_persisted", False) if col.get("is_computed") else None,
            col.get("collation"),
            col.get("is_sparse", False),
            col.get("is_rowguidcol", False),
        )

    def _generate_rollback(self) -> List[str]:
        """
        src_cols = {c.get("name"): c for c in source_table.get("columns", []) if c.get("name")}
        tgt_cols = {c.get("name"): c for c in target_table.get("columns", []) if c.get("name")}

        added: List[Dict[str, Any]] = []
        removed: List[Dict[str, Any]] = []
        changed: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []

        for name, col in src_cols.items():
            if name not in tgt_cols:
                added.append(col)
            else:
                tgt_col = tgt_cols[name]
                if self._column_signature(col) != self._column_signature(tgt_col):
                    changed.append((col, tgt_col))

        for name, col in tgt_cols.items():
            if name not in src_cols:
                removed.append(col)

        return added, removed, changed

    def _column_signature(self, col: Dict[str, Any]) -> Tuple[Any, ...]:
        """Build a tuple representing the complete column definition including all properties."""
        return (
            (col.get("data_type") or "").lower(),
            col.get("max_length"),
            col.get("precision"),
            col.get("scale"),
            self._is_nullable(col),
            str(col.get("default_value")) if col.get("default_value") is not None else None,
            # Include new advanced properties
            col.get("is_identity", False),
            col.get("identity_seed") if col.get("is_identity") else None,
            col.get("identity_increment") if col.get("is_identity") else None,
            col.get("is_computed", False),
            col.get("computed_definition") if col.get("is_computed") else None,
            col.get("is_persisted", False) if col.get("is_computed") else None,
            col.get("collation"),
            col.get("is_sparse", False),
            col.get("is_rowguidcol", False),
        )

    def _generate_rollback(self) -> List[str]:
        """Generate a companion rollback script based on the same diff.

        This focuses on table/column-level changes, giving users a
        practical way to revert structural changes after deployment.
        """
        lines: List[str] = [
            "-- ==============================================================================",
            "-- ROLLBACK SCRIPT (Generated)",
            "-- NOTE: Review carefully before running in production.",
            "-- This script attempts to reverse table and column changes.",
            "-- ==============================================================================",
            "",
            f"USE [{self.target_db}];",
            "GO",
            "",
            "SET NOCOUNT ON;",
            "SET XACT_ABORT ON;",
            "",
            "PRINT 'Starting rollback...';",
            "PRINT '';",
            "",
            "BEGIN TRANSACTION;",
            "",
        ]

        # Roll back table structures (reverse of _generate_table_phase)
        tables = self.results.get("tables", [])

        # 1) Modified tables: reverse column changes
        modified_tables = [t for t in tables if t.get("status") == "DIFFERENT"]
        for table in modified_tables:
            name = table.get("name", "")
            details = table.get("details", {})
            lines.extend(self._rollback_table_columns(name, details))

        # 2) New tables created during deployment -> drop them
        new_tables = [t for t in tables if t.get("status") == "MISSING_IN_TARGET"]
        for table in new_tables:
            name = table.get("name", "")
            if name:
                lines.append(f"PRINT 'Dropping newly-created table {name} as part of rollback...';")
                lines.append(f"IF OBJECT_ID('{name}', 'U') IS NOT NULL DROP TABLE {name};")
                lines.append("GO")
                lines.append("")

        lines.extend(
            [
                "",
                "COMMIT TRANSACTION;",
                "PRINT 'Rollback script completed.';",
                "GO",
            ]
        )

        return lines

    def _rollback_table_columns(self, table_name: str, details: Dict[str, Any]) -> List[str]:
        """Generate rollback ALTER TABLE statements for a modified table."""
        lines: List[str] = []

        parts = table_name.split(".")
        if len(parts) != 2:
            return lines

        source_table = (details.get("source") or {})
        target_table = (details.get("target") or {})

        # For rollback we treat "target" as the original definition we
        # want to restore, and "source" as the new definition.
        added, removed, changed = self._compare_columns(source_table, target_table)

        if not added and not removed and not changed:
            return lines

        lines.append(f"PRINT 'Reverting column changes on {table_name}...';")

        # Columns that were added in forward script -> DROP them
        for col in added:
            col_name = col.get("name", "")
            lines.append(f"ALTER TABLE {table_name} DROP COLUMN [{col_name}];")

        # Columns that were removed in forward script -> re-add using
        # original target definition
        tgt_cols = {c.get("name"): c for c in target_table.get("columns", []) if c.get("name")}
        for col in removed:
            col_name = col.get("name", "")
            orig = tgt_cols.get(col_name)
            if not orig:
                continue
            type_str = self._format_column_type(orig)
            nullable_str = "NULL" if self._is_nullable(orig) else "NOT NULL"
            default_val = orig.get("default_value")
            default_str = f" DEFAULT {default_val}" if default_val else ""
            lines.append(
                f"ALTER TABLE {table_name} ADD [{col_name}] {type_str} {nullable_str}{default_str};"
            )

        # Columns that were altered in forward script -> restore original
        for _src_col, tgt_col in changed:
            col_name = tgt_col.get("name", "")
            type_str = self._format_column_type(tgt_col)
            nullable_str = "NULL" if self._is_nullable(tgt_col) else "NOT NULL"
            lines.append(
                f"ALTER TABLE {table_name} ALTER COLUMN [{col_name}] {type_str} {nullable_str};"
            )

        lines.append("")
        return lines
