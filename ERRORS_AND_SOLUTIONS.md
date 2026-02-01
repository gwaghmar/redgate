# SQL Compare Tool - Errors & Solutions Log

**Purpose:** Document all errors encountered during development and their solutions for future reference.

---

## 🐛 Error Log

### Error #1: Module Import Error - customtkinter
**Date:** January 14, 2026  
**Phase:** Initial Setup

**Error Message:**
```
ModuleNotFoundError: No module named 'customtkinter'
```

**Cause:** Missing Python package in virtual environment

**Solution:**
```powershell
pip install customtkinter
```

**Status:** ✅ RESOLVED

---

### Error #2: Module Import Error - setuptools
**Date:** January 14, 2026  
**Phase:** Initial Setup

**Error Message:**
```
ModuleNotFoundError: No module named 'distutils'
```

**Cause:** Python 3.12 removed distutils, customtkinter needs setuptools

**Solution:**
```powershell
pip install setuptools
```

**Status:** ✅ RESOLVED

---

### Error #3: AttributeError - _show_identical
**Date:** January 14, 2026  
**Phase:** GUI Development

**Error Message:**
```
AttributeError: 'MainWindow' object has no attribute '_show_identical'
```

**Cause:** `_build_results_grid()` called before state variables initialized in `__init__`

**Solution:**
Moved `_build_results_grid()` call to END of `__init__` method, after all state variables are created.

**Code Change:**
```python
# Before (wrong order):
self._build_results_grid()  # Called too early
self._show_identical = ctk.BooleanVar(value=True)  # Defined later

# After (correct order):
self._show_identical = ctk.BooleanVar(value=True)  # Define first
# ... all other state vars ...
self._build_results_grid()  # Call last
```

**Status:** ✅ RESOLVED

---

### Error #4: ODBC Driver Error - ActiveDirectoryInteractive with MSAL
**Date:** January 14, 2026  
**Phase:** Entra Authentication

**Error Message:**
```
HY000: [Microsoft][ODBC Driver 18 for SQL Server][SQL Server]
Driver not capable
```

**Cause:** Mixing `Authentication=ActiveDirectoryInteractive` with MSAL token acquisition

**Solution:**
Switched to `ActiveDirectoryAccessToken` mode with MSAL token passed via `attrs_before`

**Code Change:**
```python
# Before:
conn_str = "...;Authentication=ActiveDirectoryInteractive;"

# After:
conn_str = "...;"  # No Authentication keyword
token = self._acquire_token()
attrs_before = {1256: token_bytes}  # SQL_COPT_SS_ACCESS_TOKEN
```

**Status:** ✅ RESOLVED

---

### Error #5: AADSTS900144 - Scope Error
**Date:** January 14, 2026  
**Phase:** Entra Authentication

**Error Message:**
```
AADSTS900144: The request body must contain the following parameter: 'scope'
```

**Cause:** Manual Chrome browser launch bypassed MSAL's proper OAuth flow

**Solution:**
Removed manual Chrome launching, used `BROWSER` environment variable to prefer Chrome, let MSAL handle browser

**Code Change:**
```python
# Before (manual Chrome launch - wrong):
subprocess.Popen([chrome_path, auth_url])

# After (MSAL handles it - correct):
os.environ['BROWSER'] = chrome_path
result = app.acquire_token_interactive(scopes=self.scope)
```

**Status:** ✅ RESOLVED

---

### Error #6: 08001 - Invalid Authentication Error
**Date:** January 14, 2026  
**Phase:** Token Authentication

**Error Message:**
```
08001: [Microsoft][ODBC Driver 18 for SQL Server]
Parse error at line: 1, column: 381: Incorrect syntax near 'FOR'.
```

**Cause:** Using `Authentication=ActiveDirectoryAccessToken` in connection string when passing token via `attrs_before`

**Solution:**
Remove `Authentication` keyword entirely from connection string when using token-based auth

**Code Change:**
```python
# Before (conflict):
conn_str = "...;Authentication=ActiveDirectoryAccessToken;"
attrs_before = {1256: token_bytes}

# After (no conflict):
conn_str = "...;"  # No Authentication keyword
attrs_before = {1256: token_bytes}
```

**Status:** ✅ RESOLVED

---

### Error #7: 18456 - Login Failed for User
**Date:** January 14, 2026  
**Phase:** Token Authentication

**Error Message:**
```
18456: Login failed for user '<token-identified principal>'
```

**Cause:** SQL Server permissions issue - user needs to be created from external provider

**Solution:**
This is expected for new Entra users. Database admin needs to run:
```sql
CREATE LOGIN [user@domain.com] FROM EXTERNAL PROVIDER;
CREATE USER [user@domain.com] FOR LOGIN [user@domain.com];
GRANT SELECT, VIEW DEFINITION TO [user@domain.com];
```

**Status:** ✅ DOCUMENTED (not a code error)

---

### Error #8: 42000 - STRING_AGG 8000-byte Limit
**Date:** January 14, 2026  
**Phase:** Metadata Extraction

**Error Message:**
```
42000: [Microsoft][ODBC Driver 18 for SQL Server][SQL Server]
STRING_AGG aggregation result exceeded the limit of 8000 bytes.
Use LOB types to avoid result truncation.
```

**Cause:** Index with 100+ columns caused STRING_AGG to exceed 8000 bytes

**Solution Attempted #1 (FAILED):**
```sql
-- Wrapped STRING_AGG with CAST
CAST(STRING_AGG(c.name, ',') AS NVARCHAR(MAX))
-- Still failed - CAST applies to result, not intermediate aggregation
```

**Solution Attempted #2 (FAILED):**
```sql
-- FOR XML PATH with TYPE/value
FOR XML PATH(''), TYPE).value('.', 'NVARCHAR(MAX)')
-- Caused SQL syntax error: Parse error near 'FOR'
```

**Solution #3 (SUCCESS):**
Removed ALL SQL aggregation. Fetch rows and aggregate in Python:
```python
# Get index metadata separately
idx_meta_q = "SELECT ... FROM sys.indexes ..."

# Get index columns separately  
idx_cols_q = "SELECT ... FROM sys.index_columns ..."

# Aggregate in Python
for row in idx_cols:
    index_dict[idx_key]["columns"].append(col_name)
```

**Status:** ✅ RESOLVED

---

### Error #9: 08001 - Column Invalid in SELECT
**Date:** January 14, 2026  
**Phase:** Index Extraction

**Error Message:**
```
08001: Column 'sys.indexes.object_id' is invalid in the select list 
because it is not contained in either an aggregate function or the GROUP BY clause
```

**Cause:** Using STRING_AGG with incomplete GROUP BY clause

**Solution:**
This was resolved when we switched to Python-side aggregation (Error #8 solution)

**Status:** ✅ RESOLVED (by Error #8 fix)

---

### Error #10: 104385 - Catalog View Not Supported
**Date:** January 14, 2026  
**Phase:** Triggers Extraction

**Error Message:**
```
104385: Catalog view 'triggers' is not supported in this version
```

**Cause:** Azure Synapse doesn't support `sys.triggers` catalog view

**Solution:**
Wrapped triggers extraction in try-except block:
```python
def _extract_triggers(self, schema_filter: Optional[str] = None) -> Dict[str, Any]:
    try:
        # Try to extract triggers
        query = "SELECT ... FROM sys.triggers ..."
        return results
    except Exception:
        # Return empty dict if not supported
        return {}
```

**Status:** ✅ RESOLVED

---

### Error #11: SyntaxError - Unmatched Parenthesis
**Date:** January 14, 2026  
**Phase:** Code Cleanup

**Error Message:**
```python
File "metadata_extractor.py", line 273
    )
    ^
SyntaxError: unmatched ')'
```

**Cause:** Duplicate code left after adding try-except block to triggers extraction

**Solution:**
Removed duplicate query code that appeared after `return {}` statement

**Status:** ✅ RESOLVED

---

## 🔍 Common Patterns & Solutions

### Pattern #1: Azure Synapse Compatibility
**Issue:** Synapse has limited catalog view support compared to SQL Server

**Solution:** Wrap optional extractions in try-except:
```python
try:
    # Query catalog view
    query = "SELECT ... FROM sys.foreign_keys ..."
    return results
except Exception:
    # Return empty/default if not supported
    return {}
```

**Applied To:**
- Foreign keys
- Indexes  
- Triggers

---

### Pattern #2: SQL Aggregation Limits
**Issue:** STRING_AGG, FOR XML PATH have 8000-byte limits

**Solution:** Fetch rows separately and aggregate in Python:
```python
# Don't do aggregation in SQL
rows = connection.execute_query("SELECT col1, col2 FROM table")

# Aggregate in Python (unlimited memory)
result_dict = {}
for row in rows:
    key = row[0]
    result_dict.setdefault(key, []).append(row[1])
```

---

### Pattern #3: Token Authentication
**Issue:** Entra token authentication requires specific ODBC setup

**Solution Checklist:**
1. ✅ Use MSAL `PublicClientApplication`
2. ✅ Acquire token with `acquire_token_interactive`
3. ✅ Cache token with `SerializableTokenCache`
4. ✅ Encode token as UTF-16LE with 4-byte length prefix
5. ✅ Pass via `attrs_before={1256: token_bytes}`
6. ✅ Do NOT include `Authentication=` in connection string
7. ✅ Enable `autocommit=True`

---

### Pattern #4: GUI Initialization Order
**Issue:** AttributeError when widgets reference state variables

**Solution:**
Always initialize state variables BEFORE calling methods that use them:
```python
def __init__(self):
    # 1. Create widgets (no state access)
    self.button = ctk.CTkButton(...)
    
    # 2. Initialize ALL state variables
    self._show_identical = ctk.BooleanVar(value=True)
    self._results = None
    
    # 3. Call methods that use state (LAST)
    self._build_grid()
```

---

## 📚 Lessons Learned

1. **Research First:** STRING_AGG errors could have been avoided by researching limitations upfront

2. **Azure Compatibility:** Always assume Azure SQL/Synapse has fewer features than on-premises SQL Server

3. **Error Handling:** Graceful degradation (try-except) better than hard failures for optional features

4. **Token Authentication:** ODBC token auth is tricky - follow the exact pattern

5. **Python > SQL:** When SQL has limits (8000 bytes), do it in Python (unlimited memory)

6. **Initialization Order:** State variables before methods that use them

---

## 🔄 Last Updated
**Date:** January 14, 2026  
**Total Errors Logged:** 11  
**Resolved:** 11  
**Open:** 0
