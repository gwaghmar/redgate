# GitHub Repository Setup - REDGATE SQL

This guide will help you push the SQL Compare Tool project to your existing GitHub repository.

## Prerequisites

1. **Git installed** - Download from [git-scm.com](https://git-scm.com/download/win)
2. **GitHub account** - Create one at [github.com](https://github.com)
3. **GitHub authentication** - Set up one of:
   - Personal Access Token (recommended)
   - SSH keys
   - GitHub CLI

## Quick Start

### Option 1: Using the Automated Script (Recommended)

1. **Run the push script:**
   ```powershell
   .\push_to_github.ps1
   ```

2. **Enter your GitHub username when prompted**

3. **Enter repository name** (default: `REDGATE-SQL`)

4. **Confirm force push** when prompted (this will replace all existing content)

### Option 2: Manual Push

If you know your GitHub username and repository name:

```powershell
# Add remote repository (replace YOUR_USERNAME and REPO_NAME)
git remote add origin https://github.com/YOUR_USERNAME/REPO_NAME.git

# Push with force to replace all content
git push -u origin main --force

# Push tags
git push origin --tags
```

### Option 3: If Repository Doesn't Exist Yet

1. **Create the repository on GitHub:**
   - Go to [github.com/new](https://github.com/new)
   - Repository name: `REDGATE-SQL` (or your preferred name)
   - Description: "SQL Server database comparison and deployment tool with Azure Synapse support"
   - Choose Public or Private
   - **DO NOT** initialize with README, .gitignore, or license (we already have these)
   - Click "Create repository"

2. **Push the code:**
   ```powershell
   git remote add origin https://github.com/YOUR_USERNAME/REPO_NAME.git
   git push -u origin main --force
   git push origin --tags
   ```

## Authentication

If you get authentication errors:

### Using Personal Access Token (Recommended)

1. Go to [GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)](https://github.com/settings/tokens)
2. Generate new token with `repo` scope
3. When prompted for password, use the token instead

### Using GitHub CLI

```powershell
gh auth login
```

### Using SSH

1. Generate SSH key:
   ```powershell
   ssh-keygen -t ed25519 -C "your_email@example.com"
   ```

2. Add to GitHub: [github.com/settings/keys](https://github.com/settings/keys)

3. Use SSH URL:
   ```powershell
   git remote set-url origin git@github.com:YOUR_USERNAME/REPO_NAME.git
   ```

## What's Included

This push includes:

- ✅ Complete source code (Python application)
- ✅ Comprehensive documentation (README.md, PROGRESS.md, etc.)
- ✅ Security improvements documentation
- ✅ Error logs and solutions
- ✅ Unit tests
- ✅ Configuration files
- ✅ .gitignore (properly configured)
- ✅ Initial release tag (v1.0.0)

## Repository Structure

```
REDGATE SQL/
├── sql_compare_tool/     # Main application
│   ├── core/            # Core comparison logic
│   ├── gui/             # User interface
│   ├── utils/           # Utilities
│   └── tests/           # Unit tests
├── config/              # Configuration files
├── docs/                # Documentation files
├── README.md            # Main documentation
├── .gitignore          # Git ignore rules
└── push_to_github.ps1  # Push script
```

## After Pushing

1. **Verify the push:**
   - Visit your repository on GitHub
   - Check that all files are present
   - Verify the README.md displays correctly

2. **Create additional tags if needed:**
   ```powershell
   git tag -a v1.0.1 -m "Bug fixes and improvements"
   git push origin --tags
   ```

3. **Set up GitHub Actions** (optional):
   - Add CI/CD workflows
   - Set up automated testing
   - Configure code quality checks

## Troubleshooting

### "Repository not found"
- Verify the repository name is correct
- Check that you have access to the repository
- Ensure the repository exists on GitHub

### "Authentication failed"
- Use Personal Access Token instead of password
- Check token has `repo` scope
- Verify SSH keys are set up correctly

### "Force push rejected"
- Some repositories have branch protection
- Contact repository admin to allow force push
- Or create a new branch and merge it

## Support

If you encounter issues:
1. Check the error message carefully
2. Verify your GitHub credentials
3. Ensure the repository exists and you have write access
4. Review the authentication setup

---

**Ready to push?** Run `.\push_to_github.ps1` and follow the prompts!
