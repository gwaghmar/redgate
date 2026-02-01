# PowerShell script to push REDGATE SQL project to GitHub
# This script will replace all content in the existing repository

param(
    [Parameter(Mandatory=$false)]
    [string]$GitHubUsername,
    
    [Parameter(Mandatory=$false)]
    [string]$RepositoryName = "REDGATE-SQL",
    
    [Parameter(Mandatory=$false)]
    [switch]$Force
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "REDGATE SQL - GitHub Push Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if git is installed
try {
    $gitVersion = git --version
    Write-Host "✓ Git found: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Git is not installed. Please install Git first." -ForegroundColor Red
    exit 1
}

# Check if we're in the right directory
if (-not (Test-Path "sql_compare_tool")) {
    Write-Host "✗ Error: sql_compare_tool directory not found. Please run this script from the REDGATE SQL directory." -ForegroundColor Red
    exit 1
}

Write-Host "✓ Found project files" -ForegroundColor Green
Write-Host ""

# Get GitHub username if not provided
if (-not $GitHubUsername) {
    $GitHubUsername = Read-Host "Enter your GitHub username"
}

# Initialize git repository if not already initialized
if (-not (Test-Path ".git")) {
    Write-Host "Initializing git repository..." -ForegroundColor Yellow
    git init
    Write-Host "✓ Git repository initialized" -ForegroundColor Green
} else {
    Write-Host "✓ Git repository already initialized" -ForegroundColor Green
}

# Add all files
Write-Host "Adding files to git..." -ForegroundColor Yellow
git add .
Write-Host "✓ Files added" -ForegroundColor Green

# Check if there are changes to commit
$status = git status --porcelain
if ($status) {
    Write-Host "Creating initial commit..." -ForegroundColor Yellow
    git commit -m "Initial commit: SQL Compare Tool - Complete project with documentation and tags"
    Write-Host "✓ Commit created" -ForegroundColor Green
} else {
    Write-Host "✓ No changes to commit" -ForegroundColor Green
}

# Set branch to main
Write-Host "Setting branch to main..." -ForegroundColor Yellow
git branch -M main
Write-Host "✓ Branch set to main" -ForegroundColor Green

# Add remote repository
$repoUrl = "https://github.com/$GitHubUsername/$RepositoryName.git"
Write-Host "Adding remote repository: $repoUrl" -ForegroundColor Yellow

# Remove existing remote if it exists
$existingRemote = git remote get-url origin 2>$null
if ($existingRemote) {
    Write-Host "Removing existing remote..." -ForegroundColor Yellow
    git remote remove origin
}

git remote add origin $repoUrl
Write-Host "✓ Remote added" -ForegroundColor Green

# Push to GitHub
Write-Host ""
Write-Host "Pushing to GitHub..." -ForegroundColor Yellow
Write-Host "WARNING: This will replace ALL content in the repository!" -ForegroundColor Red
Write-Host ""

if ($Force) {
    git push -u origin main --force
} else {
    $confirm = Read-Host "Do you want to proceed with force push? (yes/no)"
    if ($confirm -eq "yes" -or $confirm -eq "y") {
        git push -u origin main --force
    } else {
        Write-Host "Push cancelled." -ForegroundColor Yellow
        exit 0
    }
}

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✓ Successfully pushed to GitHub!" -ForegroundColor Green
    Write-Host "Repository URL: $repoUrl" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "1. Create tags if needed: git tag -a v1.0.0 -m 'Initial release'" -ForegroundColor White
    Write-Host "2. Push tags: git push origin --tags" -ForegroundColor White
} else {
    Write-Host ""
    Write-Host "✗ Push failed. Please check:" -ForegroundColor Red
    Write-Host "1. Repository exists on GitHub: $repoUrl" -ForegroundColor Yellow
    Write-Host "2. You have write access to the repository" -ForegroundColor Yellow
    Write-Host "3. Your GitHub credentials are configured" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To configure credentials:" -ForegroundColor Yellow
    Write-Host "  - Use Personal Access Token: https://github.com/settings/tokens" -ForegroundColor White
    Write-Host "  - Or use GitHub CLI: gh auth login" -ForegroundColor White
}
