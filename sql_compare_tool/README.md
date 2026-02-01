# SQL Compare Tool (work in progress)

Simple steps to run and share with teammates.

## Prereqs
- Windows with UI (for interactive sign-in).
- ODBC Driver 18 for SQL Server installed (from Microsoft).
- For running from source: Python 3.10+.

## Run from source (dev/test)
1) Open PowerShell in this folder: `sql_compare_tool`.
2) Install deps: `pip install -r requirements.txt`.
3) Launch: `python main.py`.
4) In the app, pick Source and Target servers/databases.
   - Auth: choose SQL Login, Windows, or Entra MFA (will show Microsoft sign-in prompt).
   - Click Test on each side, then Compare (placeholder until diff engine added).

## Build single EXE (PyInstaller)
After installing deps:
```
pyinstaller --onefile --noconsole --name sql-compare-tool main.py
```
The EXE will be in `dist/sql-compare-tool.exe`. Share that with teammates; they do not need Python, just ODBC Driver 18 installed. When they run it, the Entra login prompt will appear for MFA.

## Current status
- Connection UI for Source/Target with SQL Login, Windows, Entra MFA.
- Test buttons to validate connectivity.
- Compare runs metadata extract (tables with columns/PK/FK/indexes, views, procs, functions, triggers, users, roles, schemas, synonyms, extended properties), compares with DeepDiff, shows counts, a short list of differences, and populates a results grid (row colors by status).
- Filter checkbox to hide/show identical items in the grid.
- Selecting a row shows a side-by-side preview in the lower pane.
- Script preview button outputs a placeholder deployment script (create/drop/alter TODO lines) for the last comparison.
- Export CSV button saves compare results to exports/compare_results.csv.
- Export HTML button saves compare results to exports/compare_results.html with status coloring.
- Export JSON button saves compare results to exports/compare_results.json.
- Export Excel button saves compare results to exports/compare_results.xlsx.

## Next steps (high level)
- Add metadata extraction (tables, views, procs, functions, triggers, indexes, keys, constraints).
- Add comparison engine and results grid with colors and filters.
- Add side-by-side SQL diff viewer and summary view.
- Add deployment script generation and wizard.
- Add project save/load and report exports (HTML/Excel/PDF/CSV/JSON).
