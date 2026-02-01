# PowerShell script to push REDGATE SQL to GitHub repository "redgate"
# This will replace all existing content in the repository

$GitHubUsername = "gwaghmar"
$RepositoryName = "redgate"
$RepoUrl = "https://github.com/$GitHubUsername/$RepositoryName.git"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "REDGATE SQL - Push to GitHub" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Repository: $RepoUrl" -ForegroundColor Yellow
Write-Host ""

# Check if git is installed
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Git is not installed." -ForegroundColor Red
    exit 1
}

# Ensure we're in the right directory
if (-not (Test-Path "sql_compare_tool")) {
    Write-Host "ERROR: Please run this script from the REDGATE SQL directory." -ForegroundColor Red
    exit 1
}

# Set remote
Write-Host "Setting remote repository..." -ForegroundColor Yellow
$existingRemote = git remote get-url origin 2>$null
if ($existingRemote) {
    git remote set-url origin $RepoUrl
} else {
    git remote add origin $RepoUrl
}
Write-Host "✓ Remote configured" -ForegroundColor Green

# Push to GitHub
Write-Host ""
Write-Host "Pushing to GitHub..." -ForegroundColor Yellow
Write-Host "WARNING: This will replace ALL content in the repository!" -ForegroundColor Red
Write-Host ""

git push -u origin main --force

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "SUCCESS! Pushed to GitHub" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Repository: $RepoUrl" -ForegroundColor Cyan
    
    # Push tags
    Write-Host ""
    Write-Host "Pushing tags..." -ForegroundColor Yellow
    git push origin --tags
    Write-Host "✓ Tags pushed" -ForegroundColor Green
    
} else {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "PUSH FAILED" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Possible reasons:" -ForegroundColor Yellow
    Write-Host "1. Repository doesn't exist on GitHub" -ForegroundColor White
    Write-Host "2. Authentication failed (need Personal Access Token)" -ForegroundColor White
    Write-Host "3. Permission denied" -ForegroundColor White
    Write-Host ""
    Write-Host "To create the repository:" -ForegroundColor Cyan
    Write-Host "1. Go to: https://github.com/new" -ForegroundColor White
    Write-Host "2. Repository name: redgate" -ForegroundColor White
    Write-Host "3. Description: SQL Server database comparison and deployment tool" -ForegroundColor White
    Write-Host "4. Choose Public or Private" -ForegroundColor White
    Write-Host "5. DO NOT initialize with README, .gitignore, or license" -ForegroundColor White
    Write-Host "6. Click 'Create repository'" -ForegroundColor White
    Write-Host "7. Run this script again" -ForegroundColor White
    Write-Host ""
    Write-Host "For authentication:" -ForegroundColor Cyan
    Write-Host "- Use Personal Access Token: https://github.com/settings/tokens" -ForegroundColor White
    Write-Host "- Generate token with 'repo' scope" -ForegroundColor White
    Write-Host "- Use token as password when prompted" -ForegroundColor White
    exit 1
}
