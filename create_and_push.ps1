# Complete script to create GitHub repo and push REDGATE SQL project
# This script will attempt to create the repository and push all code

$GitHubUsername = "gwaghmar"
$RepositoryName = "redgate"
$RepoUrl = "https://github.com/$GitHubUsername/$RepositoryName.git"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "REDGATE SQL - Create Repo & Push" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if GitHub CLI is installed
$ghInstalled = Get-Command gh -ErrorAction SilentlyContinue

if ($ghInstalled) {
    Write-Host "GitHub CLI found. Attempting to create repository..." -ForegroundColor Yellow
    
    # Check if authenticated
    $authStatus = gh auth status 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ GitHub CLI authenticated" -ForegroundColor Green
        
        # Create repository
        Write-Host "Creating repository '$RepositoryName'..." -ForegroundColor Yellow
        $createResult = gh repo create $RepositoryName --public --description "SQL Server database comparison and deployment tool with Azure Synapse support" 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Repository created successfully" -ForegroundColor Green
        } else {
            Write-Host "Repository may already exist or creation failed. Continuing..." -ForegroundColor Yellow
        }
    } else {
        Write-Host "GitHub CLI not authenticated. Please run: gh auth login" -ForegroundColor Yellow
    }
} else {
    Write-Host "GitHub CLI not found. Please create repository manually:" -ForegroundColor Yellow
    Write-Host "1. Go to: https://github.com/new" -ForegroundColor White
    Write-Host "2. Repository name: $RepositoryName" -ForegroundColor White
    Write-Host "3. Description: SQL Server database comparison and deployment tool" -ForegroundColor White
    Write-Host "4. Choose Public or Private" -ForegroundColor White
    Write-Host "5. DO NOT initialize with README, .gitignore, or license" -ForegroundColor White
    Write-Host "6. Click 'Create repository'" -ForegroundColor White
    Write-Host ""
    $continue = Read-Host "Press Enter after creating the repository to continue..."
}

# Ensure we're in the right directory
if (-not (Test-Path "sql_compare_tool")) {
    Write-Host "ERROR: Please run this script from the REDGATE SQL directory." -ForegroundColor Red
    exit 1
}

# Set remote
Write-Host ""
Write-Host "Configuring git remote..." -ForegroundColor Yellow
$existingRemote = git remote get-url origin 2>$null
if ($existingRemote) {
    git remote set-url origin $RepoUrl
} else {
    git remote add origin $RepoUrl
}
Write-Host "✓ Remote configured: $RepoUrl" -ForegroundColor Green

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
    
    Write-Host ""
    Write-Host "All done! Visit your repository:" -ForegroundColor Green
    Write-Host $RepoUrl -ForegroundColor Cyan
    
} else {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "PUSH FAILED" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Possible reasons:" -ForegroundColor Yellow
    Write-Host "1. Repository doesn't exist - Create it at: https://github.com/new" -ForegroundColor White
    Write-Host "2. Authentication failed - Use Personal Access Token" -ForegroundColor White
    Write-Host "3. Permission denied - Check repository access" -ForegroundColor White
    Write-Host ""
    Write-Host "For authentication:" -ForegroundColor Cyan
    Write-Host "- Generate token: https://github.com/settings/tokens" -ForegroundColor White
    Write-Host "- Use token with 'repo' scope" -ForegroundColor White
    Write-Host "- Use token as password when prompted" -ForegroundColor White
    exit 1
}
