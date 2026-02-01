from __future__ import annotations

from typing import Dict, Any, List, Callable, Optional

from core.database import DatabaseConnection
from utils.logger import get_logger

logger = get_logger(__name__)


class MetadataExtractor:
    """Pulls schema metadata needed for comparison."""

    def __init__(self, connection: DatabaseConnection) -> None:
        self.connection = connection

    def extract(self, progress_callback: Optional[Callable[[str], None]] = None, schema_filter: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """Extract metadata with optional progress updates and schema filtering."""
        logger.info(f"Starting metadata extraction with schema_filter={schema_filter}")
        if progress_callback:
            progress_callback("Extracting table structures...")
        tables = self._extract_tables(schema_filter)
        
        if progress_callback:
            progress_callback("Extracting views...")
        views = self._extract_views(schema_filter)
        
        if progress_callback:
            progress_callback("Extracting stored procedures...")
        procedures = self._extract_procs(schema_filter)
        
        if progress_callback:
            progress_callback("Extracting functions...")
        functions = self._extract_functions(schema_filter)
        
        if progress_callback:
            progress_callback("Extracting triggers...")
        triggers = self._extract_triggers(schema_filter)
        
        if progress_callback:
            progress_callback("Extracting users...")
        users = self._extract_users()
        
        if progress_callback:
            progress_callback("Extracting roles...")
        roles = self._extract_roles()
        
        if progress_callback:
            progress_callback("Extracting schemas...")
        schemas = self._extract_schemas()
        
        if progress_callback:
            progress_callback("Extracting synonyms...")
        synonyms = self._extract_synonyms(schema_filter)
        
        if progress_callback:
            progress_callback("Extracting extended properties...")
        extended_properties = self._extract_extended_properties(schema_filter)
        
        if progress_callback:
            progress_callback("Extracting check constraints...")
        check_constraints = self._extract_check_constraints(schema_filter)
        
        if progress_callback:
            progress_callback("Extracting default constraints...")
        default_constraints = self._extract_default_constraints(schema_filter)
        
        if progress_callback:
            progress_callback("Extracting unique constraints...")
        unique_constraints = self._extract_unique_constraints(schema_filter)

        if progress_callback:
            progress_callback("Extracting user-defined types...")
        user_defined_types = self._extract_user_defined_types(schema_filter)

        if progress_callback:
            progress_callback("Extracting sequences...")
        sequences = self._extract_sequences(schema_filter)
        
        logger.info(f"Metadata extraction complete: {len(tables)} tables, {len(views)} views, "
                   f"{len(procedures)} procedures, {len(functions)} functions")
        
        return {
            "tables": tables,
            "views": views,
            "procedures": procedures,
            "functions": functions,
            "triggers": triggers,
            "users": users,
            "roles": roles,
            "schemas": schemas,
            "synonyms": synonyms,
            "extended_properties": extended_properties,
            "check_constraints": check_constraints,
            "default_constraints": default_constraints,
            "unique_constraints": unique_constraints,
            "user_defined_types": user_defined_types,
            "sequences": sequences,
        }

    def _extract_tables(self, schema_filter: Optional[str] = None) -> Dict[str, Any]:
        tables: Dict[str, Any] = {}
        # Validate schema_filter to prevent SQL injection
        if schema_filter:
            # Only allow alphanumeric, underscore, and basic characters
            import re
            if not re.match(r'^[a-zA-Z0-9_]+$', schema_filter):
                raise ValueError(f"Invalid schema filter: {schema_filter}. Only alphanumeric characters and underscores allowed.")
        schema_where = f" AND s.name = '{schema_filter}'" if schema_filter else ""

        # Use sys.columns for comprehensive column metadata
        columns_q = (
            "SELECT s.name AS schema_name, t.name AS table_name, "
            "c.name AS column_name, c.column_id, "
            "ty.name AS data_type, c.max_length, c.precision, c.scale, "
            "c.is_nullable, c.is_identity, c.is_computed, c.is_sparse, c.is_rowguidcol, "
            "CAST(dc.definition AS NVARCHAR(MAX)) AS default_value, "
            "CAST(cc.definition AS NVARCHAR(MAX)) AS computed_definition, "
            "CAST(cc.is_persisted AS BIT) AS is_persisted, "
            "CAST(c.collation_name AS NVARCHAR(128)) AS collation_name, "
            "CAST(ic.seed_value AS BIGINT) AS identity_seed, "
            "CAST(ic.increment_value AS BIGINT) AS identity_increment "
            "FROM sys.tables t "
            "JOIN sys.schemas s ON t.schema_id = s.schema_id "
            "JOIN sys.columns c ON t.object_id = c.object_id "
            "JOIN sys.types ty ON c.user_type_id = ty.user_type_id "
            "LEFT JOIN sys.default_constraints dc ON c.object_id = dc.parent_object_id AND c.column_id = dc.parent_column_id "
            "LEFT JOIN sys.computed_columns cc ON c.object_id = cc.object_id AND c.column_id = cc.column_id "
            "LEFT JOIN sys.identity_columns ic ON c.object_id = ic.object_id AND c.column_id = ic.column_id "
            f"WHERE t.is_ms_shipped = 0{schema_where} "
            "ORDER BY s.name, t.name, c.column_id"
        )
        
        for row in self.connection.execute_query(columns_q):
            (schema, table, col_name, col_id, dtype, max_len, prec, scale, 
             is_nullable, is_identity, is_computed, is_sparse, is_rowguidcol,
             default_val, computed_def, is_persisted, collation, 
             identity_seed, identity_increment) = row
            
            key = f"{schema}.{table}"
            tables.setdefault(key, {"columns": [], "indexes": [], "primary_key": None, "foreign_keys": []})
            
            col_info = {
                "name": col_name,
                "ordinal_position": col_id,
                "data_type": dtype,
                "max_length": max_len,
                "precision": prec,
                "scale": scale,
                "is_nullable": bool(is_nullable),
            }
            
            # Add optional properties only if they exist
            if default_val:
                col_info["default_value"] = default_val
            if collation:
                col_info["collation"] = collation
            if is_identity:
                col_info["is_identity"] = True
                col_info["identity_seed"] = identity_seed
                col_info["identity_increment"] = identity_increment
            if is_computed:
                col_info["is_computed"] = True
                col_info["computed_definition"] = computed_def
                col_info["is_persisted"] = bool(is_persisted)
            if is_sparse:
                col_info["is_sparse"] = True
            if is_rowguidcol:
                col_info["is_rowguidcol"] = True
            
            tables[key]["columns"].append(col_info)

        # Primary Key extraction - store as single object, not array
        schema_pk_where = f" AND s.name = '{schema_filter}'" if schema_filter else ""
        pk_q = (
            "SELECT s.name AS schema_name, t.name AS table_name, kc.name AS pk_name, "
            "c.name AS column_name, ic.key_ordinal "
            "FROM sys.key_constraints kc "
            "JOIN sys.tables t ON kc.parent_object_id = t.object_id "
            "JOIN sys.schemas s ON t.schema_id = s.schema_id "
            "JOIN sys.index_columns ic ON kc.parent_object_id = ic.object_id AND kc.unique_index_id = ic.index_id "
            "JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id "
            f"WHERE kc.type = 'PK'{schema_pk_where} "
            "ORDER BY s.name, t.name, ic.key_ordinal"
        )
        for row in self.connection.execute_query(pk_q):
            schema, table, pk_name, col_name, ordinal = row
            key = f"{schema}.{table}"
            tables.setdefault(key, {"columns": [], "indexes": [], "primary_key": None, "foreign_keys": []})
            if tables[key]["primary_key"] is None:
                tables[key]["primary_key"] = {"name": pk_name, "columns": []}
            tables[key]["primary_key"]["columns"].append(col_name)

        # Foreign keys (may not be supported in Synapse)
        try:
            schema_fk_where = f" WHERE ps.name = '{schema_filter}'" if schema_filter else ""
            fk_q = (
                "SELECT ps.name AS schema_name, pt.name AS table_name, fk.name AS fk_name, "
                "cs.name AS column_name, rs.name AS ref_schema, rt.name AS ref_table, rc.name AS ref_column, "
                "fk.delete_referential_action_desc, fk.update_referential_action_desc, fkc.constraint_column_id "
                "FROM sys.foreign_keys fk "
                "JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id "
                "JOIN sys.tables pt ON fkc.parent_object_id = pt.object_id "
                "JOIN sys.schemas ps ON pt.schema_id = ps.schema_id "
                "JOIN sys.columns cs ON fkc.parent_object_id = cs.object_id AND fkc.parent_column_id = cs.column_id "
                "JOIN sys.tables rt ON fkc.referenced_object_id = rt.object_id "
                "JOIN sys.schemas rs ON rt.schema_id = rs.schema_id "
                "JOIN sys.columns rc ON fkc.referenced_object_id = rc.object_id AND fkc.referenced_column_id = rc.column_id "
                f"{schema_fk_where} "
                "ORDER BY ps.name, pt.name, fk.name, fkc.constraint_column_id"
            )
            for row in self.connection.execute_query(fk_q):
                schema, table, fk_name, col_name, ref_schema, ref_table, ref_col, del_rule, upd_rule, ordinal = row
                key = f"{schema}.{table}"
                tables.setdefault(key, {"columns": [], "indexes": [], "primary_key": None, "foreign_keys": []})
                existing = next((fk for fk in tables[key]["foreign_keys"] if fk["name"] == fk_name), None)
                if not existing:
                    tables[key]["foreign_keys"].append(
                        {
                            "name": fk_name,
                            "columns": [],
                            "referenced_table": f"{ref_schema}.{ref_table}",
                            "referenced_columns": [],
                            "delete_rule": del_rule,
                            "update_rule": upd_rule,
                        }
                    )
                    existing = tables[key]["foreign_keys"][-1]
                existing["columns"].append(col_name)
                existing["referenced_columns"].append(ref_col)
        except Exception:
            # Foreign keys not supported (e.g., Azure Synapse)
            pass

        # Get index metadata (may have limited support in Synapse)
        try:
            schema_idx_where = f" AND s.name = '{schema_filter}'" if schema_filter else ""
            idx_meta_q = (
                "SELECT s.name AS schema_name, t.name AS table_name, i.name, i.type_desc, "
                "i.is_unique, i.is_primary_key, i.filter_definition, i.object_id, i.index_id"
                " FROM sys.indexes i"
                " JOIN sys.tables t ON i.object_id = t.object_id"
                " JOIN sys.schemas s ON t.schema_id = s.schema_id"
                f" WHERE i.is_hypothetical = 0 AND i.name IS NOT NULL{schema_idx_where}"
            )
            
            # Build index dictionary
            index_dict = {}
            for row in self.connection.execute_query(idx_meta_q):
                schema, table, name, type_desc, is_unique, is_pk, filter_def, obj_id, idx_id = row
                key = f"{schema}.{table}"
                tables.setdefault(key, {"columns": [], "indexes": [], "primary_key": None, "foreign_keys": []})
                
                idx_key = (obj_id, idx_id)
                # Determine if this is a clustered index
                is_clustered = type_desc and 'CLUSTERED' in type_desc.upper()
                
                index_dict[idx_key] = {
                    "table_key": key,
                    "name": name,
                    "type_desc": type_desc,
                    "is_clustered": is_clustered,
                    "is_unique": bool(is_unique),
                    "is_primary_key": bool(is_pk),
                    "columns": [],
                    "included_columns": [],
                    "filter_definition": filter_def,
                }
            
            # Get index columns (key columns)
            idx_cols_q = (
                "SELECT ic.object_id, ic.index_id, c.name, ic.is_included_column, ic.key_ordinal, ic.index_column_id"
                " FROM sys.index_columns ic"
                " JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id"
                " ORDER BY ic.object_id, ic.index_id, ic.is_included_column, ic.key_ordinal, ic.index_column_id"
            )
            
            for row in self.connection.execute_query(idx_cols_q):
                obj_id, idx_id, col_name, is_included, key_ordinal, idx_col_id = row
                idx_key = (obj_id, idx_id)
                if idx_key in index_dict:
                    if is_included:
                        index_dict[idx_key]["included_columns"].append(col_name)
                    else:
                        index_dict[idx_key]["columns"].append(col_name)
            
            # Add indexes to tables
            for idx_data in index_dict.values():
                table_key = idx_data.pop("table_key")
                tables[table_key]["indexes"].append(idx_data)
        except Exception:
            # Indexes may not be fully supported (e.g., Azure Synapse)
            pass

        # Temporal table metadata (SQL Server system-versioned tables).
        # Not all SKUs support temporal tables, so wrap in try/except.
        try:
            schema_temp_where = f" AND s.name = '{schema_filter}'" if schema_filter else ""
            temporal_q = (
                "SELECT s.name AS schema_name, t.name AS table_name, "
                "t.temporal_type, ht.name AS history_table_name "
                "FROM sys.tables t "
                "JOIN sys.schemas s ON t.schema_id = s.schema_id "
                "LEFT JOIN sys.tables ht ON t.history_table_id = ht.object_id "
                f"WHERE t.temporal_type <> 0{schema_temp_where}"
            )
            for row in self.connection.execute_query(temporal_q):
                schema, table, temporal_type, history_table_name = row
                key = f"{schema}.{table}"
                tables.setdefault(key, {"columns": [], "indexes": [], "primary_key": None, "foreign_keys": []})
                tables[key]["is_temporal"] = bool(temporal_type)
                if history_table_name:
                    tables[key]["history_table"] = history_table_name
        except Exception:
            # Temporal metadata not available (older SQL, Synapse, etc.)
            pass

        return tables

    def _extract_views(self, schema_filter: Optional[str] = None) -> Dict[str, Any]:
        if schema_filter:
            import re
            if not re.match(r'^[a-zA-Z0-9_]+$', schema_filter):
                raise ValueError(f"Invalid schema filter: {schema_filter}")
        schema_where = f" AND s.name = '{schema_filter}'" if schema_filter else ""
        query = (
            "SELECT s.name AS schema_name, o.name, m.definition"
            " FROM sys.objects o"
            " JOIN sys.sql_modules m ON o.object_id = m.object_id"
            " JOIN sys.schemas s ON o.schema_id = s.schema_id"
            f" WHERE o.type = 'V'{schema_where}"
        )
        rows = self.connection.execute_query(query)
        return {f"{schema}.{name}": {"definition": definition} for schema, name, definition in rows}

    def _extract_procs(self, schema_filter: Optional[str] = None) -> Dict[str, Any]:
        if schema_filter:
            import re
            if not re.match(r'^[a-zA-Z0-9_]+$', schema_filter):
                raise ValueError(f"Invalid schema filter: {schema_filter}")
        schema_where = f" AND s.name = '{schema_filter}'" if schema_filter else ""
        query = (
            "SELECT s.name AS schema_name, o.name, m.definition"
            " FROM sys.objects o"
            " JOIN sys.sql_modules m ON o.object_id = m.object_id"
            " JOIN sys.schemas s ON o.schema_id = s.schema_id"
            f" WHERE o.type = 'P'{schema_where}"
        )
        rows = self.connection.execute_query(query)
        return {f"{schema}.{name}": {"definition": definition} for schema, name, definition in rows}

    def _extract_functions(self, schema_filter: Optional[str] = None) -> Dict[str, Any]:
        if schema_filter:
            import re
            if not re.match(r'^[a-zA-Z0-9_]+$', schema_filter):
                raise ValueError(f"Invalid schema filter: {schema_filter}")
        schema_where = f" AND s.name = '{schema_filter}'" if schema_filter else ""
        query = (
            "SELECT s.name AS schema_name, o.name, m.definition"
            " FROM sys.objects o"
            " JOIN sys.sql_modules m ON o.object_id = m.object_id"
            " JOIN sys.schemas s ON o.schema_id = s.schema_id"
            f" WHERE o.type IN ('FN','IF','TF'){schema_where}"
        )
        rows = self.connection.execute_query(query)
        return {f"{schema}.{name}": {"definition": definition} for schema, name, definition in rows}

    def _extract_triggers(self, schema_filter: Optional[str] = None) -> Dict[str, Any]:
        try:
            if schema_filter:
                import re
                if not re.match(r'^[a-zA-Z0-9_]+$', schema_filter):
                    raise ValueError(f"Invalid schema filter: {schema_filter}")
            schema_where = f" AND s.name = '{schema_filter}'" if schema_filter else ""
            query = (
                "SELECT s.name AS schema_name, p.name AS parent_name, tr.name AS trigger_name, m.definition, tr.is_disabled"
                " FROM sys.triggers tr"
                " JOIN sys.objects p ON tr.parent_id = p.object_id"
                " JOIN sys.schemas s ON p.schema_id = s.schema_id"
                " JOIN sys.sql_modules m ON tr.object_id = m.object_id"
                f" WHERE tr.parent_class = 1{schema_where}"
            )
            rows = self.connection.execute_query(query)
            return {
                f"{schema}.{parent}.{trig}": {"definition": definition, "is_enabled": not bool(is_disabled)}
                for schema, parent, trig, definition, is_disabled in rows
            }
        except Exception as e:
            # Azure SQL or older versions may not support sys.triggers catalog view
            # Return empty dict instead of failing
            return {}

    def _extract_users(self) -> Dict[str, Any]:
        query = (
            "SELECT name, type_desc, default_schema_name"
            " FROM sys.database_principals"
            " WHERE type IN ('S','U','G') AND name NOT LIKE '##%'")
        rows = self.connection.execute_query(query)
        return {
            name: {"type_desc": type_desc, "default_schema": default_schema}
            for name, type_desc, default_schema in rows
        }

    def _extract_roles(self) -> Dict[str, Any]:
        query = "SELECT name, type_desc FROM sys.database_principals WHERE type = 'R'"
        rows = self.connection.execute_query(query)
        return {name: {"type_desc": type_desc} for name, type_desc in rows}

    def _extract_schemas(self) -> Dict[str, Any]:
        query = "SELECT name, USER_NAME(principal_id) AS owner FROM sys.schemas"
        rows = self.connection.execute_query(query)
        return {name: {"owner": owner} for name, owner in rows}

    def _extract_synonyms(self, schema_filter: Optional[str] = None) -> Dict[str, Any]:
        schema_where = f" WHERE s.name = '{schema_filter}'" if schema_filter else ""
        query = (
            "SELECT s.name AS schema_name, syn.name, syn.base_object_name"
            " FROM sys.synonyms syn"
            " JOIN sys.schemas s ON syn.schema_id = s.schema_id"
            f"{schema_where}"
        )
        rows = self.connection.execute_query(query)
        return {f"{schema}.{name}": {"base_object_name": base} for schema, name, base in rows}

    def _extract_extended_properties(self, schema_filter: Optional[str] = None) -> Dict[str, Any]:
        schema_where = f" AND s.name = '{schema_filter}'" if schema_filter else ""
        query = (
            "SELECT s.name AS schema_name, o.name AS object_name, ep.name, ep.value"
            " FROM sys.extended_properties ep"
            " LEFT JOIN sys.objects o ON ep.major_id = o.object_id"
            " LEFT JOIN sys.schemas s ON o.schema_id = s.schema_id"
            f" WHERE ep.class = 1{schema_where}"
        )
        rows = self.connection.execute_query(query)
        result: Dict[str, Any] = {}
        for schema, obj, name, val in rows:
            key = f"{schema}.{obj}" if schema and obj else f"{name}"
            result.setdefault(key, []).append({"name": name, "value": val})
        return result

    def _extract_check_constraints(self, schema_filter: Optional[str] = None) -> Dict[str, Any]:
        """Extract CHECK constraints from database."""
        try:
            schema_where = f" AND s.name = '{schema_filter}'" if schema_filter else ""
            query = (
                "SELECT s.name AS schema_name, t.name AS table_name, "
                "cc.name AS constraint_name, cc.definition, cc.is_disabled "
                "FROM sys.check_constraints cc "
                "JOIN sys.tables t ON cc.parent_object_id = t.object_id "
                "JOIN sys.schemas s ON t.schema_id = s.schema_id"
                f"{' WHERE' if schema_where else ''}{schema_where[5:] if schema_where else ''}"
            )
            rows = self.connection.execute_query(query)
            return {
                f"{schema}.{table}.{constraint}": {
                    "definition": definition,
                    "is_enabled": not bool(is_disabled)
                }
                for schema, table, constraint, definition, is_disabled in rows
            }
        except Exception:
            # Some Azure SQL versions may not support check constraints catalog view
            return {}

    def _extract_default_constraints(self, schema_filter: Optional[str] = None) -> Dict[str, Any]:
        """Extract DEFAULT constraints from database."""
        try:
            schema_where = f" AND s.name = '{schema_filter}'" if schema_filter else ""
            query = (
                "SELECT s.name AS schema_name, t.name AS table_name, "
                "dc.name AS constraint_name, c.name AS column_name, dc.definition "
                "FROM sys.default_constraints dc "
                "JOIN sys.tables t ON dc.parent_object_id = t.object_id "
                "JOIN sys.schemas s ON t.schema_id = s.schema_id "
                "JOIN sys.columns c ON dc.parent_object_id = c.object_id AND dc.parent_column_id = c.column_id"
                f"{' WHERE' if schema_where else ''}{schema_where[5:] if schema_where else ''}"
            )
            rows = self.connection.execute_query(query)
            return {
                f"{schema}.{table}.{constraint}": {
                    "column": column,
                    "definition": definition
                }
                for schema, table, constraint, column, definition in rows
            }
        except Exception:
            # Some Azure SQL versions may not support default constraints catalog view
            return {}

    def _extract_unique_constraints(self, schema_filter: Optional[str] = None) -> Dict[str, Any]:
        """Extract UNIQUE constraints from database."""
        try:
            schema_where = f" AND s.name = '{schema_filter}'" if schema_filter else ""
            # Get unique constraint metadata
            constraint_q = (
                "SELECT s.name AS schema_name, t.name AS table_name, "
                "kc.name AS constraint_name, kc.unique_index_id "
                "FROM sys.key_constraints kc "
                "JOIN sys.tables t ON kc.parent_object_id = t.object_id "
                "JOIN sys.schemas s ON t.schema_id = s.schema_id "
                f"WHERE kc.type = 'UQ'{schema_where}"
            )
            constraint_rows = self.connection.execute_query(constraint_q)
            
            # Build dictionary with constraint metadata
            constraints = {}
            for schema, table, constraint, index_id in constraint_rows:
                key = f"{schema}.{table}.{constraint}"
                constraints[key] = {
                    "columns": [],
                    "object_id": None,
                    "index_id": index_id
                }
            
            # Get columns for each unique constraint
            if constraints:
                columns_q = (
                    "SELECT s.name AS schema_name, t.name AS table_name, "
                    "kc.name AS constraint_name, c.name AS column_name, ic.key_ordinal "
                    "FROM sys.key_constraints kc "
                    "JOIN sys.tables t ON kc.parent_object_id = t.object_id "
                    "JOIN sys.schemas s ON t.schema_id = s.schema_id "
                    "JOIN sys.index_columns ic ON kc.parent_object_id = ic.object_id AND kc.unique_index_id = ic.index_id "
                    "JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id "
                    f"WHERE kc.type = 'UQ'{schema_where} "
                    "ORDER BY s.name, t.name, kc.name, ic.key_ordinal"
                )
                columns_rows = self.connection.execute_query(columns_q)
                
                for schema, table, constraint, column, ordinal in columns_rows:
                    key = f"{schema}.{table}.{constraint}"
                    if key in constraints:
                        constraints[key]["columns"].append(column)
            
            # Clean up temporary fields
            for constraint in constraints.values():
                del constraint["object_id"]
                del constraint["index_id"]
            
            return constraints
        except Exception:
            # Some Azure SQL versions may not support unique constraints catalog view
            return {}

    def _extract_user_defined_types(self, schema_filter: Optional[str] = None) -> Dict[str, Any]:
        """Extract user-defined types (UDTs) from the database.

        Captures basic properties so they can be compared between
        source and target databases without relying on STRING_AGG
        or other size-limited SQL aggregation.
        """
        try:
            schema_filter_clause = f" AND s.name = '{schema_filter}'" if schema_filter else ""
            query = (
                "SELECT s.name AS schema_name, t.name AS type_name, "
                "bt.name AS base_type, t.is_table_type, t.max_length, t.precision, t.scale "
                "FROM sys.types t "
                "JOIN sys.schemas s ON t.schema_id = s.schema_id "
                "JOIN sys.types bt ON t.system_type_id = bt.user_type_id AND bt.user_type_id = bt.system_type_id "
                "WHERE t.is_user_defined = 1" + schema_filter_clause
            )
            rows = self.connection.execute_query(query)
            return {
                f"{schema}.{type_name}": {
                    "base_type": base_type,
                    "is_table_type": bool(is_table_type),
                    "max_length": max_length,
                    "precision": precision,
                    "scale": scale,
                }
                for schema, type_name, base_type, is_table_type, max_length, precision, scale in rows
            }
        except Exception:
            # Older SQL versions or some Azure flavors may not support all
            # catalog metadata for UDTs; fail gracefully.
            return {}

    def _extract_sequences(self, schema_filter: Optional[str] = None) -> Dict[str, Any]:
        """Extract SEQUENCE objects from the database.

        Not all SQL Server or Azure flavors support sequences; this
        method is wrapped in try/except to keep extraction robust.
        """
        try:
            schema_filter_clause = f" AND s.name = '{schema_filter}'" if schema_filter else ""
            query = (
                "SELECT s.name AS schema_name, seq.name AS sequence_name, "
                "seq.start_value, seq.increment, seq.minimum_value, seq.maximum_value, "
                "seq.is_cycling, seq.cache_size "
                "FROM sys.sequences seq "
                "JOIN sys.schemas s ON seq.schema_id = s.schema_id "
                "WHERE 1 = 1" + schema_filter_clause
            )
            rows = self.connection.execute_query(query)
            return {
                f"{schema}.{name}": {
                    "start_value": start_value,
                    "increment": increment,
                    "minimum_value": min_value,
                    "maximum_value": max_value,
                    "is_cycling": bool(is_cycling),
                    "cache_size": cache_size,
                }
                for (
                    schema,
                    name,
                    start_value,
                    increment,
                    min_value,
                    max_value,
                    is_cycling,
                    cache_size,
                ) in rows
            }
        except Exception:
            # Sequences are not available everywhere; if unsupported,
            # just return an empty set so comparison can continue.
            return {}
