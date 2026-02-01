# SQL Compare Tool

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active%20Development-yellow.svg)]()

A comprehensive SQL Server database comparison and deployment tool with support for Azure Synapse, Entra MFA authentication, and advanced metadata extraction.

**Repository:** [https://github.com/gwaghmar/redgate-sql-compare](https://github.com/gwaghmar/redgate-sql-compare)

## 🚀 Features

- **Multi-Authentication Support**
  - SQL Server Authentication
  - Windows Authentication
  - Azure Entra ID (MFA) with MSAL token flow

- **Comprehensive Metadata Extraction**
  - Tables (columns, data types, constraints)
  - Primary Keys, Foreign Keys, Indexes
  - Views, Stored Procedures, Functions
  - Triggers, Users, Roles, Schemas
  - Synonyms, Extended Properties
  - Check Constraints, Default Constraints, Unique Constraints
  - User-Defined Types, Sequences
  - Temporal Tables, Partitioning

- **Advanced Comparison Engine**
  - Deep object comparison using DeepDiff
  - Status detection: IDENTICAL, DIFFERENT, MISSING_IN_TARGET, MISSING_IN_SOURCE
  - Schema filtering for focused comparisons
  - Side-by-side diff viewer with color highlighting

- **Deployment Script Generation**
  - Phase-based deployment (Drop, Tables, Constraints, Programmability, Misc)
  - ALTER TABLE support for column changes
  - Transaction wrapping with rollback support
  - Dependency resolution for programmability objects
  - Deployment wizard with warnings and preview

- **Export & Reporting**
  - CSV, JSON, Excel (.xlsx), HTML, PDF exports
  - Project save/load (XML format)
  - Snapshot support (.snp files)
  - Script folder comparison

- **Security & Quality**
  - SQL injection protection
  - Input validation
  - Secure JSON caching (no Pickle)
  - Comprehensive logging
  - Unit test coverage

## 📋 Prerequisites

- **Windows** (with UI for interactive sign-in)
- **Python 3.10+**
- **ODBC Driver 18 for SQL Server** (from Microsoft)
- **SQL Server** or **Azure Synapse Analytics** database access

## 🛠️ Installation

### From Source

1. Clone the repository:
```bash
git clone <repository-url>
cd "REDGATE SQL"
```

2. Create a virtual environment:
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

3. Install dependencies:
```powershell
cd sql_compare_tool
pip install -r requirements.txt
```

4. Run the application:
```powershell
python main.py
```

### Build Executable (PyInstaller)

After installing dependencies:
```powershell
pyinstaller --onefile --noconsole --name sql-compare-tool main.py
```

The executable will be in `dist/sql-compare-tool.exe`. Share this with teammates; they only need ODBC Driver 18 installed.

## 📖 Usage

### Basic Workflow

1. **Launch the application**
   ```powershell
   python main.py
   ```

2. **Configure Source Connection**
   - Select authentication type (SQL Login, Windows, or Entra MFA)
   - Enter server name and database
   - Click "Test" to validate connection

3. **Configure Target Connection**
   - Repeat the same process for target database

4. **Run Comparison**
   - Click "Compare" button
   - Wait for metadata extraction to complete
   - Review results in the grid

5. **View Differences**
   - Select any row in the results grid
   - View side-by-side diff in the lower pane
   - Use tabs to switch between SQL View and Summary View

6. **Generate Deployment Script**
   - Click "Script Preview" button
   - Review the generated SQL script
   - Use deployment wizard for guided deployment

7. **Export Results**
   - Use export buttons: CSV, JSON, Excel, HTML, PDF
   - Save project for later: File → Save Project

### Advanced Features

#### Schema Filtering
- Enter schema name in the filter field to compare only specific schemas
- Reduces load time for large databases

#### Comparison Options
- Configure what to compare (tables, views, procs, etc.)
- Set comparison options (whitespace handling, case sensitivity)

#### Deployment Options
- Configure transaction wrapping
- Set deployment phases
- Enable rollback script generation

#### Snapshots
- Save database metadata as snapshot (.snp file)
- Compare against snapshots instead of live databases
- Useful for offline comparisons

## 📁 Project Structure

```
REDGATE SQL/
├── sql_compare_tool/
│   ├── core/              # Core comparison logic
│   │   ├── database.py           # Database connections
│   │   ├── metadata_extractor.py # Metadata extraction
│   │   ├── comparator.py          # Comparison engine
│   │   ├── diff_generator.py     # Diff generation
│   │   ├── script_generator.py   # Deployment scripts
│   │   └── snapshot.py           # Snapshot management
│   ├── gui/               # User interface
│   │   └── main_window.py        # Main application window
│   ├── utils/            # Utilities
│   │   ├── config.py            # Configuration management
│   │   ├── logger.py            # Logging system
│   │   ├── project_manager.py   # Project save/load
│   │   ├── report_generator.py  # Export functionality
│   │   └── sql_parser.py        # SQL parsing utilities
│   ├── tests/            # Unit tests
│   ├── cache_manager.py # Cache management
│   ├── main.py          # Application entry point
│   └── requirements.txt # Python dependencies
├── config/              # Configuration files
├── docs/                # Documentation
│   ├── PROGRESS.md
│   ├── IMPROVEMENTS_SUMMARY.md
│   ├── ERRORS_AND_SOLUTIONS.md
│   └── NEXT_STEPS_STATUS.md
└── README.md           # This file
```

## 🔧 Configuration

Configuration is stored in `config/settings.json` and includes:

- **App Settings**: UI theme, recent servers, auto-save
- **Database Settings**: Timeouts, default auth, connection pooling
- **Comparison Settings**: Whitespace handling, case sensitivity
- **Script Generation**: Transaction wrapping, rollback options
- **Cache Settings**: Cache retention policies
- **Logging**: Log levels, file retention
- **Export**: Default formats, output directories

## 🧪 Testing

Run unit tests:
```powershell
cd sql_compare_tool/tests
python test_core_components.py
```

Expected output:
```
Ran 15 tests in 0.XXXs
OK
```

## 📊 Current Status

**Overall Progress: 60% Complete**

### ✅ Completed Features
- Database connectivity (SQL/Windows/Entra MFA)
- Comprehensive metadata extraction
- Comparison engine with DeepDiff
- User interface with CustomTkinter
- Export functionality (CSV, JSON, Excel, HTML, PDF)
- Project save/load
- Deployment script generation
- Security improvements (SQL injection protection, secure caching)
- Logging infrastructure
- Configuration management
- Unit test suite

### 🚧 In Progress
- Enhanced metadata extraction (temporal tables, partitions)
- Advanced diff viewer improvements
- Deployment wizard enhancements
- Performance optimizations

### 📅 Planned
- CLR objects support
- UI/UX improvements
- Integration tests
- Comprehensive documentation
- CI/CD pipeline

See [PROGRESS.md](PROGRESS.md) for detailed progress tracking.

## 🔒 Security

- **SQL Injection Protection**: Input validation on all schema filters
- **Secure Caching**: JSON-based cache (no Pickle)
- **Server Validation**: Blocks dangerous characters in server names
- **Token Management**: Secure MSAL token caching

## 📝 Documentation

- [PROGRESS.md](PROGRESS.md) - Development progress and roadmap
- [IMPROVEMENTS_SUMMARY.md](IMPROVEMENTS_SUMMARY.md) - Recent improvements and security fixes
- [ERRORS_AND_SOLUTIONS.md](ERRORS_AND_SOLUTIONS.md) - Error log and solutions
- [NEXT_STEPS_STATUS.md](NEXT_STEPS_STATUS.md) - Implementation status

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🐛 Known Issues

- Dependency graph is heuristic (text-based) and may need hardening
- Deployment wizard is basic (3 steps, no live execution UI)
- Test coverage at 15% (needs expansion)

## 🔮 Future Enhancements

- Connection pooling for better performance
- Result pagination for large comparisons
- Live deployment execution UI
- Enhanced dependency resolution
- Telemetry for error tracking
- Multi-threading for database operations

## 📞 Support

For issues, questions, or contributions:
- Review documentation in `docs/` folder
- Check logs in `logs/` directory
- Review [ERRORS_AND_SOLUTIONS.md](ERRORS_AND_SOLUTIONS.md) for known issues

---

## 🚀 Deployment

This is a **desktop application** (not web-deployed). Users install and run locally on Windows machines.

**Installation Requirements:**
- Windows 10/11
- Python 3.10+
- ODBC Driver 18 for SQL Server
- SQL Server or Azure Synapse Analytics access

---

**Last Updated:** January 2026  
**Version:** 1.0.0  
**Status:** Active Development (60% Complete)
