# COMPREHENSIVE PROMPT: BUILD PYTHON SQL COMPARE TOOL (SQL SERVER)

## OBJECTIVE
Build a professional-grade SQL Server schema comparison tool in Python that replicates ALL features and functionality of Redgate SQL Compare. This must be built in ONE SHOT - complete, production-ready, and fully functional.

---

## CRITICAL: RESEARCH FIRST
Before writing ANY code, use web search to research:
1. Redgate SQL Compare official documentation and feature lists
2. SQL Server INFORMATION_SCHEMA and system catalog views
3. Best practices for database schema comparison
4. Professional UI/UX patterns for diff viewers

---

## 1. CORE FEATURES TO IMPLEMENT (MANDATORY)

### 1.1 DATABASE CONNECTION & SOURCES
**Must support comparison between:**
- Live SQL Server databases (via pyodbc)
- Database snapshots (.snp files - custom format)
- SQL script folders (CREATE scripts organized by object type)
- Backup files (.bak files - read-only comparison)

**Connection Requirements:**
- SQL Server Authentication (username/password)
- Windows Authentication
- Connection string management
- Save/remember credentials securely
- Test connection before comparison
- Support for SQL Server 2008, 2012, 2014, 2016, 2017, 2019, Azure SQL

**UI Elements for Connection:**
```
[Source Database]                    [Target Database]
Server: [____________] [Test]        Server: [____________] [Test]
Database: [__________] [▼]           Database: [__________] [▼]
Auth: [●SQL ○Windows]                Auth: [●SQL ○Windows]
Username: [__________]                Username: [__________]
Password: [__________]                Password: [__________]
[☐ Remember credentials]             [☐ Remember credentials]

Or load from:
○ Database    ○ Snapshot    ○ Scripts folder    ○ Backup file
```

### 1.2 COMPARISON ENGINE (CRITICAL)

**Objects to Compare:**
```python
OBJECTS_TO_COMPARE = {
    'Tables': {
        'columns': ['name', 'data_type', 'max_length', 'precision', 'scale', 'is_nullable', 'default_value'],
        'indexes': ['name', 'type_desc', 'is_unique', 'is_primary_key', 'columns', 'included_columns', 'filter_definition'],
        'primary_keys': ['name', 'columns'],
        'foreign_keys': ['name', 'columns', 'referenced_table', 'referenced_columns', 'delete_rule', 'update_rule'],
        'check_constraints': ['name', 'definition'],
        'default_constraints': ['name', 'definition'],
        'unique_constraints': ['name', 'columns'],
        'triggers': ['name', 'definition', 'is_enabled']
    },
    'Views': ['name', 'definition', 'with_check_option', 'is_updated'],
    'Stored Procedures': ['name', 'definition', 'parameters'],
    'Functions': {
        'Scalar Functions': ['name', 'definition', 'return_type'],
        'Table-Valued Functions': ['name', 'definition', 'return_table_definition'],
        'Inline TVFs': ['name', 'definition']
    },
    'Triggers': ['name', 'definition', 'parent_object', 'is_enabled', 'trigger_events'],
    'Users': ['name', 'type_desc', 'default_schema'],
    'Roles': ['name', 'type_desc'],
    'Schemas': ['name', 'owner'],
    'Synonyms': ['name', 'base_object_name'],
    'User-Defined Types': ['name', 'definition', 'base_type'],
    'CLR Objects': ['name', 'assembly_name', 'class_name'],
    'Temporal Tables': ['name', 'history_table', 'history_retention_period'],
    'Partitions': ['scheme_name', 'function_name', 'boundary_values'],
    'Filegroups': ['name', 'is_default', 'files'],
    'Full-Text Catalogs': ['name', 'properties'],
    'Extended Properties': ['name', 'value', 'parent_object']
}
```

**Metadata Extraction Queries:**
```sql
-- Tables
SELECT 
    t.TABLE_SCHEMA,
    t.TABLE_NAME,
    c.COLUMN_NAME,
    c.DATA_TYPE,
    c.CHARACTER_MAXIMUM_LENGTH,
    c.NUMERIC_PRECISION,
    c.NUMERIC_SCALE,
    c.IS_NULLABLE,
    c.COLUMN_DEFAULT
FROM INFORMATION_SCHEMA.TABLES t
JOIN INFORMATION_SCHEMA.COLUMNS c ON t.TABLE_NAME = c.TABLE_NAME
WHERE t.TABLE_TYPE = 'BASE TABLE'

-- Indexes  
SELECT 
    i.name,
    i.type_desc,
    i.is_unique,
    i.is_primary_key,
    STRING_AGG(c.name, ', ') as columns
FROM sys.indexes i
JOIN sys.index_columns ic ON i.object_id = ic.object_id
JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
GROUP BY i.name, i.type_desc, i.is_unique, i.is_primary_key

-- Foreign Keys
SELECT 
    fk.name,
    STRING_AGG(c1.name, ', ') as columns,
    OBJECT_NAME(fk.referenced_object_id) as referenced_table,
    STRING_AGG(c2.name, ', ') as referenced_columns,
    fk.delete_referential_action_desc,
    fk.update_referential_action_desc
FROM sys.foreign_keys fk
JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
JOIN sys.columns c1 ON fkc.parent_object_id = c1.object_id AND fkc.parent_column_id = c1.column_id
JOIN sys.columns c2 ON fkc.referenced_object_id = c2.object_id AND fkc.referenced_column_id = c2.column_id
GROUP BY fk.name, fk.referenced_object_id, fk.delete_referential_action_desc, fk.update_referential_action_desc

-- Views, Procedures, Functions
SELECT 
    o.name,
    o.type_desc,
    m.definition
FROM sys.objects o
JOIN sys.sql_modules m ON o.object_id = m.object_id
WHERE o.type IN ('V', 'P', 'FN', 'IF', 'TF')
```

### 1.3 USER INTERFACE - MAIN COMPARISON WINDOW

**CRITICAL: Study these reference images before building UI:**

```
MANDATORY: Search online for and study these Redgate SQL Compare screenshots:
1. "SQL Compare main comparison results window"
2. "SQL Compare object differences view"  
3. "SQL Compare SQL diff viewer side by side"
4. "SQL Compare deployment wizard"
5. "SQL Compare project options dialog"
6. "SQL Compare filter setup pane"
```

**Main Window Layout:**
```
┌─────────────────────────────────────────────────────────────────────────┐
│ File  Edit  View  Tools  Help                                          │
├─────────────────────────────────────────────────────────────────────────┤
│ [Compare] [Deploy] [Edit Project] [Save Project] [Options] [Filters]   │
├──────────┬──────────────────────────────────────────────────────────────┤
│          │  ┌──────────────────────────────────────────────────────────┐│
│ Filters  │  │ Comparison Results                                       ││
│ ──────── │  ├────────┬─────────┬─────────┬────────┬──────────────────┤│
│          │  │Object  │Source   │Target   │Status  │Actions           ││
│ □ Tables │  ├────────┼─────────┼─────────┼────────┼──────────────────┤│
│ □ Views  │  │☑Table1 │Modified │Modified │Different│[Include in sync]││
│ □ Procs  │  │☑Table2 │Exists   │Missing  │Missing │[Include in sync]││
│ □ Funcs  │  │☑View1  │Modified │Modified │Different│[Include in sync]││
│ □ Trig   │  │ Proc1  │Exists   │Exists   │Identical│[Skip]           ││
│ □ Users  │  │☑Index1 │Missing  │Exists   │Extra   │[Include in sync]││
│ □ Roles  │  └────────┴─────────┴─────────┴────────┴──────────────────┘│
│ □ Schema │                                                              │
│ ──────── │  ══════════════════════════════════════════════════════════ │
│ Custom   │  Differences in: Table1                                     │
│ Filters: │  ┌──────────────────────────────────────────────────────────┐│
│ [+New]   │  │ Tabs: [SQL View] [Summary View]                         ││
│          │  ├──────────────────────┬───────────────────────────────────┤│
│          │  │ SOURCE (DB1)         │ TARGET (DB2)                      ││
│          │  ├──────────────────────┼───────────────────────────────────┤│
│          │  │CREATE TABLE Table1   │CREATE TABLE Table1                ││
│          │  │(                     │(                                  ││
│          │  │  ID INT PRIMARY KEY, │  ID INT PRIMARY KEY,              ││
│          │  │  Name VARCHAR(50),   │  Name VARCHAR(100),  ◄── Changed ││
│          │  │  Email VARCHAR(100), │  Email VARCHAR(100),              ││
│          │  │  NewCol VARCHAR(50)  ◄── Added                           ││
│          │  │);                    │  DeletedCol INT      ◄── Removed  ││
│          │  │                      │);                                 ││
│          │  └──────────────────────┴───────────────────────────────────┘│
└─────────┴──────────────────────────────────────────────────────────────┘
Status: 156 differences found | 42 objects identical | 23 selected for sync
```

**Color Coding (MANDATORY):**
- 🟢 GREEN (Left/Source): Objects/lines that exist in SOURCE but not in TARGET
- 🔴 RED (Right/Target): Objects/lines that exist in TARGET but not in SOURCE
- 🟡 YELLOW: Lines that exist in both but are DIFFERENT
- ⚪ WHITE: Lines that are IDENTICAL
- 📊 GRAY: Objects that are identical (collapsed by default)

### 1.4 COMPARISON STATUS TYPES

**Object Status:**
```python
STATUS_TYPES = {
    'IDENTICAL': 'Objects are exactly the same',
    'DIFFERENT': 'Objects exist in both but definitions differ',
    'MISSING_IN_TARGET': 'Object exists in source but not target',
    'MISSING_IN_SOURCE': 'Object exists in target but not source',
    'RENAMED': 'Object was renamed (detected via heuristics)',
    'MODIFIED': 'Object definition changed'
}
```

**Visual Indicators:**
```
✓ = Identical
⚠ = Different  
→ = Missing in target (deploy to target)
← = Missing in source (exists only in target)
↻ = Renamed
```

### 1.5 PROJECT OPTIONS (COMPREHENSIVE)

**Comparison Options Tab:**
```
□ Ignore whitespace
□ Ignore comments
□ Ignore case in object names
□ Ignore system-named constraints
□ Ignore users
□ Ignore permissions
□ Ignore indexes
□ Ignore full-text indexes
□ Ignore DML triggers
□ Ignore DDL triggers
□ Ignore extended properties
□ Ignore filegroups
□ Ignore fill factor
□ Ignore collation differences
□ Decrypt encrypted objects (if possible)
□ Include dependencies automatically
□ Check for table rename (smart matching)
```

**Deployment Options Tab:**
```
Script Options:
□ Add IF EXISTS checks
□ Add USE [database] statement
□ Include DROP statements
□ Force column order
□ Disable triggers during deployment
□ Use transactions
□ Add error handling
□ Generate rollback script
□ Include object-level comments

Behavior:
□ Warn on data loss
□ Check dependencies
□ Script in dependency order
□ Backup before deployment
```

### 1.6 FILTERS (ADVANCED)

**Filter Setup Panel (Left Side):**
```
┌─────────────────────────────┐
│ Object Type Filters         │
├─────────────────────────────┤
│ ☑ Tables                    │
│ ☑ Views                     │
│ ☑ Stored Procedures         │
│ ☑ Functions                 │
│ ☑ Triggers                  │
│ □ Users                     │
│ □ Roles                     │
│ □ Schemas                   │
├─────────────────────────────┤
│ Custom Filter Rules...      │
├─────────────────────────────┤
│ Active Filters:             │
│ • Name NOT LIKE 'temp%'     │
│ • Schema = 'dbo'            │
│ • Modified After 2024-01-01 │
│ [Edit] [Remove] [+Add New]  │
├─────────────────────────────┤
│ □ Show identical objects    │
│ ☑ Show different objects    │
│ ☑ Show missing objects      │
├─────────────────────────────┤
│ [Save Filter] [Load Filter] │
└─────────────────────────────┘
```

**Custom Filter Dialog:**
```
Property:    [Object Name ▼]
Operator:    [NOT LIKE    ▼]
Value:       [temp%________]
Logic:       [AND         ▼]

[Add to Filter] [Clear]
```

### 1.7 SQL DIFFERENCES VIEWER (CRITICAL)

**Two View Modes:**

**A) SQL View (Side-by-Side Diff):**
```
┌──────────────────────────┬───────────────────────────┐
│ SOURCE                   │ TARGET                    │
├──────────────────────────┼───────────────────────────┤
│ Line 1: CREATE TABLE ... │ Line 1: CREATE TABLE ...  │
│ Line 2: (                │ Line 2: (                 │
│ Line 3:   ID INT PK,     │ Line 3:   ID INT PK,      │
│ Line 4:   Name NVARCHAR( │ Line 4:   Name NVARCHAR(  │
│ Line 5:   NewCol INT,    │   ◄──────── MISSING       │
│ Line 6:   Email VARCHAR( │ Line 5:   Email VARCHAR(  │
│   ◄──────── MISSING      │ Line 6:   OldCol INT,     │
│ Line 7: );               │ Line 7: );                │
└──────────────────────────┴───────────────────────────┘
```

**Line-Level Highlighting:**
- Full line background: GREEN (source only) or RED (target only)
- Partial highlight: YELLOW (differences within same line)
- Darker shade: Specific character differences

**B) Summary View (Semantic Differences):**
```
┌─────────────────────────────────────────────────────┐
│ Table: Customers                                    │
├────────────────┬────────────┬─────────────┬────────┤
│ Property       │ Source     │ Target      │ Status │
├────────────────┼────────────┼─────────────┼────────┤
│ Column 'Name'  │ VARCHAR(50)│ VARCHAR(100)│ CHANGED│
│ Column 'Email' │ EXISTS     │ EXISTS      │ SAME   │
│ Column 'Phone' │ EXISTS     │ MISSING     │ REMOVED│
│ Column 'NewCol'│ MISSING    │ EXISTS      │ ADDED  │
│ Index 'IX_Name'│ EXISTS     │ MISSING     │ REMOVED│
│ PK 'PK_Cust'   │ (ID)       │ (ID)        │ SAME   │
└────────────────┴────────────┴─────────────┴────────┘
```

### 1.8 DEPLOYMENT WIZARD (MULTI-STEP)

**Step 1: Review Changes**
```
┌─────────────────────────────────────────────────────┐
│ Step 1 of 5: Review Changes                         │
├─────────────────────────────────────────────────────┤
│ The following changes will be made:                 │
│                                                      │
│ ☑ Tables to modify: 5                               │
│ ☑ Tables to add: 2                                  │
│ ☑ Views to modify: 3                                │
│ ☑ Stored procedures to modify: 12                   │
│ ☑ Indexes to add: 4                                 │
│ □ Users to add: 0 (excluded)                        │
│                                                      │
│ Total operations: 26                                │
│                                                      │
│ [< Back] [Next >] [Cancel]                          │
└─────────────────────────────────────────────────────┘
```

**Step 2: Check Dependencies**
```
┌─────────────────────────────────────────────────────┐
│ Step 2 of 5: Dependencies                           │
├─────────────────────────────────────────────────────┤
│ ⚠ WARNING: The following dependencies detected:     │
│                                                      │
│ • View 'vw_CustomerOrders' depends on:              │
│   - Table 'Customers' (selected)                    │
│   - Table 'Orders' (NOT selected)                   │
│                                                      │
│ ☑ Automatically include dependent objects           │
│                                                      │
│ Objects to add: Table 'Orders'                      │
│                                                      │
│ [< Back] [Next >] [Cancel]                          │
└─────────────────────────────────────────────────────┘
```

**Step 3: Warnings**
```
┌─────────────────────────────────────────────────────┐
│ Step 3 of 5: Warnings                               │
├─────────────────────────────────────────────────────┤
│ ⛔ CRITICAL WARNINGS:                                │
│                                                      │
│ • Table 'Products' - Column 'Price' data type       │
│   change from INT to DECIMAL may cause data loss    │
│                                                      │
│ • Table 'Orders' - Dropping column 'LegacyID'       │
│   will permanently delete data                      │
│                                                      │
│ • Index 'IX_CustomerName' - Rebuild will cause      │
│   table lock during deployment                      │
│                                                      │
│ □ I understand and want to proceed                  │
│                                                      │
│ [< Back] [Next >] [Cancel]                          │
└─────────────────────────────────────────────────────┘
```

**Step 4: Deployment Script Preview**
```
┌─────────────────────────────────────────────────────┐
│ Step 4 of 5: Review Script                          │
├─────────────────────────────────────────────────────┤
│ -- Generated by SQL Compare Tool                    │
│ -- Date: 2025-01-14 10:30:45                        │
│ -- Source: Server1.Database1                        │
│ -- Target: Server2.Database2                        │
│                                                      │
│ BEGIN TRANSACTION;                                  │
│                                                      │
│ -- Modify Table: Customers                          │
│ ALTER TABLE Customers                               │
│   ALTER COLUMN Name NVARCHAR(100);                  │
│                                                      │
│ -- Add Column: Customers.NewCol                     │
│ ALTER TABLE Customers                               │
│   ADD NewCol INT NULL;                              │
│                                                      │
│ COMMIT TRANSACTION;                                 │
│                                                      │
│ [Copy Script] [Save Script] [< Back] [Deploy]      │
└─────────────────────────────────────────────────────┘
```

**Step 5: Execute**
```
┌─────────────────────────────────────────────────────┐
│ Step 5 of 5: Deployment                             │
├─────────────────────────────────────────────────────┤
│ Deployment Options:                                 │
│ ○ Deploy now                                        │
│ ○ Save script for later                             │
│ ○ Open in SQL Server Management Studio              │
│                                                      │
│ □ Backup target database before deployment          │
│ □ Generate rollback script                          │
│                                                      │
│ Progress: ████████░░ 80%                            │
│ Current: Adding index IX_CustomerEmail...           │
│                                                      │
│ Log:                                                │
│ ✓ Created table: Orders                             │
│ ✓ Modified table: Customers                         │
│ ✓ Created view: vw_CustomerOrders                   │
│ ⚠ Warning: Index rebuild took 15 seconds            │
│                                                      │
│ [< Back] [Finish] [Cancel]                          │
└─────────────────────────────────────────────────────┘
```

### 1.9 REPORTS AND EXPORTS

**HTML Report:**
```html
<!DOCTYPE html>
<html>
<head>
    <title>SQL Compare Report</title>
    <style>
        .different { background-color: #ffffcc; }
        .missing { background-color: #ffcccc; }
        .extra { background-color: #ccffcc; }
        .identical { color: #888888; }
    </style>
</head>
<body>
    <h1>Database Comparison Report</h1>
    <p>Source: Server1.Database1</p>
    <p>Target: Server2.Database2</p>
    <p>Date: 2025-01-14 10:30:45</p>
    
    <h2>Summary</h2>
    <ul>
        <li>Objects compared: 234</li>
        <li>Identical: 189</li>
        <li>Different: 32</li>
        <li>Missing in target: 8</li>
        <li>Extra in target: 5</li>
    </ul>
    
    <h2>Differences</h2>
    <table>
        <tr>
            <th>Object Type</th>
            <th>Object Name</th>
            <th>Status</th>
            <th>Details</th>
        </tr>
        <!-- ... detailed rows ... -->
    </table>
</body>
</html>
```

**Excel Export:**
- Sheet 1: Summary
- Sheet 2: All Objects
- Sheet 3: Differences Only
- Sheet 4: Deployment Script

**Report Formats:**
- HTML (interactive, with CSS)
- Excel (.xlsx)
- PDF
- CSV
- JSON (for API integration)

### 1.10 PROJECT FILES (.sqlcompare format)

**Project File Structure (XML):**
```xml
<?xml version="1.0" encoding="utf-8"?>
<SQLCompareProject>
    <Version>1.0</Version>
    <Created>2025-01-14T10:30:45</Created>
    <Source>
        <Type>Database</Type>
        <Server>Server1</Server>
        <Database>Database1</Database>
        <Authentication>SQL</Authentication>
        <Username>sa</Username>
    </Source>
    <Target>
        <Type>Database</Type>
        <Server>Server2</Server>
        <Database>Database2</Database>
        <Authentication>SQL</Authentication>
        <Username>sa</Username>
    </Target>
    <Options>
        <IgnoreWhitespace>true</IgnoreWhitespace>
        <IgnoreComments>false</IgnoreComments>
        <IncludeDependencies>true</IncludeDependencies>
        <!-- ... all options ... -->
    </Options>
    <Filters>
        <ObjectTypes>
            <Tables>true</Tables>
            <Views>true</Views>
            <!-- ... -->
        </ObjectTypes>
        <CustomFilters>
            <Filter>
                <Property>ObjectName</Property>
                <Operator>NOT LIKE</Operator>
                <Value>temp%</Value>
            </Filter>
        </CustomFilters>
    </Filters>
</SQLCompareProject>
```

---

## 2. TECHNICAL ARCHITECTURE

### 2.1 Required Python Packages
```python
# requirements.txt
pyodbc==5.0.1           # SQL Server connectivity
tkinter                 # GUI (built-in)
customtkinter==5.2.0    # Modern UI components
Pillow==10.1.0          # Image handling
lxml==4.9.3             # XML parsing
openpyxl==3.1.2         # Excel export
reportlab==4.0.7        # PDF generation
deepdiff==6.7.1         # Object comparison
cryptography==41.0.7    # Credential encryption
sqlite3                 # Project storage (built-in)
difflib                 # Text diffing (built-in)
```

### 2.2 Project Structure
```
sql_compare_tool/
├── main.py                      # Entry point
├── requirements.txt
├── config.py                    # Configuration
├── gui/
│   ├── __init__.py
│   ├── main_window.py           # Main comparison window
│   ├── connection_dialog.py     # Database connection UI
│   ├── options_dialog.py        # Project options UI
│   ├── filter_panel.py          # Filter sidebar
│   ├── diff_viewer.py           # SQL diff viewer
│   ├── summary_viewer.py        # Summary view
│   ├── deployment_wizard.py     # 5-step deployment wizard
│   └── widgets.py               # Custom UI components
├── core/
│   ├── __init__.py
│   ├── database.py              # Database connection handler
│   ├── metadata_extractor.py   # Schema extraction
│   ├── comparator.py            # Comparison engine
│   ├── diff_generator.py        # Diff generation
│   ├── dependency_resolver.py  # Dependency checking
│   ├── script_generator.py     # SQL script generation
│   └── snapshot.py              # Snapshot file handler
├── utils/
│   ├── __init__.py
│   ├── sql_parser.py            # SQL parsing utilities
│   ├── credential_manager.py   # Secure credential storage
│   ├── project_manager.py      # Project save/load
│   └── report_generator.py     # HTML/Excel/PDF reports
└── tests/
    ├── __init__.py
    ├── test_comparator.py
    ├── test_metadata.py
    └── test_script_gen.py
```

### 2.3 Core Classes (UML)

```python
class DatabaseConnection:
    """Handles database connectivity"""
    def __init__(self, server, database, auth_type, username, password):
        self.server = server
        self.database = database
        self.connection = None
    
    def connect(self) -> bool:
        """Establish connection"""
        
    def test_connection(self) -> tuple[bool, str]:
        """Test connection and return (success, message)"""
    
    def execute_query(self, query: str) -> list:
        """Execute query and return results"""

class MetadataExtractor:
    """Extracts schema metadata from databases"""
    def __init__(self, connection: DatabaseConnection):
        self.conn = connection
    
    def extract_all_metadata(self) -> dict:
        """Extract complete schema metadata"""
    
    def extract_tables(self) -> list[Table]:
        """Extract all tables"""
    
    def extract_views(self) -> list[View]:
        """Extract all views"""
    
    def extract_stored_procedures(self) -> list[StoredProcedure]:
        """Extract all stored procedures"""
    
    # ... similar methods for all object types

class SchemaComparator:
    """Compares two schemas"""
    def __init__(self, source_metadata: dict, target_metadata: dict, options: dict):
        self.source = source_metadata
        self.target = target_metadata
        self.options = options
    
    def compare(self) -> ComparisonResult:
        """Perform full comparison"""
    
    def compare_tables(self) -> list[TableDifference]:
        """Compare tables"""
    
    def compare_columns(self, source_table: Table, target_table: Table) -> list[ColumnDifference]:
        """Compare columns within a table"""
    
    def apply_filters(self, results: ComparisonResult) -> ComparisonResult:
        """Apply filters to results"""

class DiffGenerator:
    """Generates visual diffs"""
    def __init__(self, source_sql: str, target_sql: str):
        self.source = source_sql
        self.target = target_sql
    
    def generate_side_by_side_diff(self) -> list[DiffLine]:
        """Generate side-by-side diff with line-level highlighting"""
    
    def generate_summary_diff(self, object_diffs: list) -> dict:
        """Generate semantic summary view"""

class ScriptGenerator:
    """Generates deployment scripts"""
    def __init__(self, comparison_result: ComparisonResult, options: dict):
        self.results = comparison_result
        self.options = options
    
    def generate_deployment_script(self, selected_objects: list) -> str:
        """Generate T-SQL deployment script"""
    
    def generate_rollback_script(self) -> str:
        """Generate rollback script"""
    
    def check_warnings(self) -> list[Warning]:
        """Check for data loss warnings"""

class DependencyResolver:
    """Resolves object dependencies"""
    def __init__(self, metadata: dict):
        self.metadata = metadata
    
    def get_dependencies(self, object_name: str, object_type: str) -> list[str]:
        """Get all objects this object depends on"""
    
    def get_dependent_objects(self, object_name: str) -> list[str]:
        """Get all objects that depend on this object"""
    
    def get_deployment_order(self, objects: list) -> list[str]:
        """Return objects in correct deployment order"""

class ProjectManager:
    """Manages project files"""
    def save_project(self, project: Project, filepath: str):
        """Save project to XML file"""
    
    def load_project(self, filepath: str) -> Project:
        """Load project from XML file"""
    
    def export_report(self, results: ComparisonResult, format: str, filepath: str):
        """Export results to HTML/Excel/PDF"""
```

---

## 3. IMPLEMENTATION REQUIREMENTS

### 3.1 GUI Framework: CustomTkinter
```python
import customtkinter as ctk

# Modern, professional appearance
ctk.set_appearance_mode("System")  # Modes: system, dark, light
ctk.set_default_color_theme("blue")

# Main window
app = ctk.CTk()
app.title("SQL Compare Tool")
app.geometry("1600x900")

# Use CTkButton, CTkLabel, CTkEntry, CTkFrame, CTkTabview, etc.
```

### 3.2 Color Scheme (Professional)
```python
COLORS = {
    'source_only': '#E6FFE6',      # Light green background
    'target_only': '#FFE6E6',      # Light red background
    'different': '#FFFFCC',         # Light yellow background
    'identical': '#F5F5F5',         # Light gray background
    'source_text': '#006600',       # Dark green text
    'target_text': '#CC0000',       # Dark red text
    'different_text': '#996600',    # Dark yellow text
    'border': '#CCCCCC',            # Gray border
    'selected': '#CCE5FF',          # Light blue for selection
}
```

### 3.3 Performance Optimization
```python
# For large databases (1000+ objects):
- Use threading for database queries
- Implement pagination in results view
- Cache metadata after extraction
- Use virtual scrolling for large result sets
- Lazy-load object definitions on click
- Show progress bar during comparison
```

### 3.4 Error Handling
```python
try:
    # Database operations
except pyodbc.Error as e:
    # Show user-friendly error dialog
    # Log detailed error
    # Offer retry/cancel options
except Exception as e:
    # Unexpected error handling
    # Create error report
    # Ask user to report bug
```

---

## 4. SQL GENERATION RULES

### 4.1 Deployment Script Structure
```sql
-- =============================================
-- SQL Compare Tool - Deployment Script
-- =============================================
-- Generated: 2025-01-14 10:30:45
-- Source: Server1.Database1
-- Target: Server2.Database2
-- Objects: 26 changes
-- =============================================

USE [Database2];
GO

SET NOCOUNT ON;
SET XACT_ABORT ON;
GO

-- Create backup (optional)
-- BACKUP DATABASE [Database2] TO DISK = 'backup.bak';

BEGIN TRANSACTION;
GO

-- =============================================
-- STEP 1: Drop dependent objects
-- =============================================

IF EXISTS (SELECT * FROM sys.objects WHERE name = 'vw_CustomerOrders')
    DROP VIEW [dbo].[vw_CustomerOrders];
GO

-- =============================================
-- STEP 2: Modify tables
-- =============================================

-- Modify table: Customers
ALTER TABLE [dbo].[Customers]
    ALTER COLUMN [Name] NVARCHAR(100) NOT NULL;
GO

ALTER TABLE [dbo].[Customers]
    ADD [NewColumn] INT NULL;
GO

-- =============================================
-- STEP 3: Recreate dependent objects
-- =============================================

CREATE VIEW [dbo].[vw_CustomerOrders]
AS
SELECT 
    c.CustomerID,
    c.Name,
    o.OrderID
FROM [dbo].[Customers] c
LEFT JOIN [dbo].[Orders] o ON c.CustomerID = o.CustomerID;
GO

-- =============================================
-- STEP 4: Create indexes
-- =============================================

CREATE NONCLUSTERED INDEX [IX_CustomerName]
ON [dbo].[Customers]([Name])
INCLUDE ([Email]);
GO

COMMIT TRANSACTION;
GO

PRINT 'Deployment completed successfully at ' + CONVERT(VARCHAR, GETDATE(), 120);
GO
```

### 4.2 Object Creation Order
```
1. Schemas
2. User-defined types
3. Tables (without FKs)
4. Indexes (non-unique first)
5. Primary keys
6. Unique constraints
7. Foreign keys
8. Check constraints
9. Default constraints
10. Views
11. Functions
12. Stored procedures
13. Triggers
14. Users
15. Roles
16. Permissions
```

---

## 5. TESTING REQUIREMENTS

### 5.1 Test Databases
```sql
-- Create test databases with known differences
-- Test_DB_Source
CREATE TABLE Customers (
    ID INT PRIMARY KEY,
    Name VARCHAR(50),
    Email VARCHAR(100)
);

-- Test_DB_Target
CREATE TABLE Customers (
    ID INT PRIMARY KEY,
    Name VARCHAR(100),  -- Different length
    Phone VARCHAR(20)   -- Different column
);
```

### 5.2 Unit Tests
```python
def test_table_comparison():
    """Test table structure comparison"""
    
def test_column_diff_detection():
    """Test column difference detection"""
    
def test_index_comparison():
    """Test index comparison"""
    
def test_script_generation():
    """Test deployment script generation"""
    
def test_dependency_resolution():
    """Test dependency order"""
```

---

## 6. USER DOCUMENTATION

### 6.1 Quick Start Guide (Include in Help menu)
```markdown
# Quick Start

1. Connect to source and target databases
2. Click "Compare" to start comparison
3. Review differences in the results grid
4. Select objects to deploy
5. Click "Deploy" and follow wizard
```

### 6.2 Help Topics (F1 Key)
- Connecting to databases
- Understanding comparison results
- Using filters
- Deployment best practices
- Troubleshooting connection issues
- Understanding warnings

---

## 7. DELIVERABLES CHECKLIST

### Phase 1: Core Functionality
- [ ] Database connection dialog (SQL + Windows auth)
- [ ] Metadata extraction for all object types
- [ ] Comparison engine with all status types
- [ ] Main results window with filters
- [ ] SQL diff viewer (side-by-side)

### Phase 2: Advanced Features
- [ ] Summary view (semantic differences)
- [ ] Deployment script generator
- [ ] Dependency resolver
- [ ] 5-step deployment wizard
- [ ] Project save/load (.sqlcompare XML)

### Phase 3: Polish & Reports
- [ ] HTML report generation
- [ ] Excel export
- [ ] PDF export
- [ ] Snapshot file support
- [ ] Options dialog (all 40+ options)
- [ ] Custom filters dialog
- [ ] Credential manager (secure storage)

### Phase 4: Testing & Documentation
- [ ] Unit tests for core logic
- [ ] Integration tests with test databases
- [ ] User guide
- [ ] Code documentation
- [ ] Error handling

---

## 8. CRITICAL SUCCESS FACTORS

### 8.1 MUST WORK PERFECTLY
✓ Database connection (SQL Server auth)
✓ Table comparison (columns, indexes, keys, constraints)
✓ Side-by-side SQL diff viewer with color coding
✓ Deployment script generation
✓ Dependency checking
✓ Project save/load

### 8.2 PROFESSIONAL APPEARANCE
✓ Modern UI (CustomTkinter)
✓ Proper color coding (green/red/yellow)
✓ Responsive layout
✓ Progress indicators
✓ Clear error messages
✓ Professional icons

### 8.3 PERFORMANCE
✓ Handle databases with 500+ objects
✓ Comparison completes in < 30 seconds
✓ No UI freezing (use threading)
✓ Memory efficient

---

## 9. SAMPLE USAGE WORKFLOW

```python
# User workflow:
1. Launch application
2. Enter source: Server1, Database1, SQL auth
3. Enter target: Server2, Database2, SQL auth
4. Click "Compare" button
5. Wait for progress bar (should take 5-15 seconds)
6. View results:
   - 234 objects compared
   - 189 identical (grayed out)
   - 45 different (yellow highlight)
7. Click on "Customers" table
8. See side-by-side diff showing:
   - Name column changed from VARCHAR(50) to VARCHAR(100)
   - NewColumn added
9. Check boxes next to objects to deploy
10. Click "Deploy"
11. Wizard shows:
    - Step 1: Review 26 selected changes
    - Step 2: Dependencies detected (includes Orders table automatically)
    - Step 3: Warning about column size change
    - Step 4: Preview deployment script
    - Step 5: Execute deployment
12. Success! Target database now matches source
13. Save project as "Production_Sync.sqlcompare"
```

---

## 10. FINAL INSTRUCTIONS FOR COPILOT

**CRITICAL: Follow this sequence:**

1. **RESEARCH FIRST** (15 minutes):
   - Search for Redgate SQL Compare screenshots
   - Search for SQL Server metadata query examples
   - Search for CustomTkinter UI examples
   - Search for side-by-side diff viewer implementations

2. **PLAN** (10 minutes):
   - Review ALL features above
   - Create detailed implementation plan
   - Identify technical challenges
   - Design database connection flow

3. **BUILD** (Main work):
   - Start with database connection module
   - Then metadata extraction
   - Then comparison engine
   - Then GUI (main window first)
   - Then diff viewer
   - Then script generator
   - Then deployment wizard
   - Finally: reports, projects, filters

4. **TEST**:
   - Test with sample databases
   - Test all UI interactions
   - Test error handling
   - Test with 500+ objects

5. **DOCUMENT**:
   - Add docstrings
   - Create README.md
   - Add code comments

**SUCCESS CRITERIA:**
✓ Can connect to SQL Server
✓ Can extract schema metadata
✓ Can compare two databases
✓ Shows differences in professional UI
✓ Can generate deployment script
✓ Can execute deployment
✓ Handles errors gracefully
✓ Looks professional

**QUALITY STANDARDS:**
- Clean, well-organized code
- Type hints throughout
- Error handling everywhere
- Professional UI appearance
- Fast performance (<30s comparison)
- Production-ready quality

---

## IMPORTANT REMINDERS

🎯 This is a ONE-SHOT implementation
🎯 Research SQL Compare thoroughly first
🎯 Build complete, production-ready tool
🎯 Professional UI is mandatory
🎯 All features must work
🎯 Handle errors gracefully
🎯 Performance matters
🎯 Test thoroughly

**GO BUILD THE BEST SQL COMPARE CLONE POSSIBLE!**
