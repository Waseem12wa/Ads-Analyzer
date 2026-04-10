# Docker Image Builder Script
Write-Host "`nDocker Image Builder - Autodownload Tool`n" -ForegroundColor Cyan

# Validate Docker is installed
$docker = Get-Command docker -ErrorAction SilentlyContinue
if (-not $docker) {
    Write-Host "ERROR: Docker is not installed." -ForegroundColor Red
    exit 1
}

# Prompt for Docker Hub details
$username = Read-Host "Docker Hub username (default: omarupwork)"
if ([string]::IsNullOrWhiteSpace($username)) { $username = "omarupwork" }

$imageName = Read-Host "Image name (default: autodownload-tool)"
if ([string]::IsNullOrWhiteSpace($imageName)) { $imageName = "autodownload-tool" }

$tag = Read-Host "Tag (default: latest)"
if ([string]::IsNullOrWhiteSpace($tag)) { $tag = "latest" }

$fullName = "$username/$imageName`:$tag"

Write-Host "`nBuilding image: $fullName`n" -ForegroundColor Green

# Build Docker image
docker build -t $fullName .
if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed!" -ForegroundColor Red
    exit 1
}

Write-Host "`nBuild successful!`n" -ForegroundColor Green

# Ask about pushing to Docker Hub
$response = Read-Host "Push to Docker Hub? (y/n)"
if ($response -eq "y" -or $response -eq "Y") {
    Write-Host "`nLogging into Docker Hub..." -ForegroundColor Cyan
    docker login
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`nPushing image..." -ForegroundColor Cyan
        docker push $fullName
        Write-Host "`nPush complete!`n" -ForegroundColor Green
    }
}

Write-Host "Commands to use your image:`n" -ForegroundColor Yellow
Write-Host "  docker pull $fullName"
Write-Host "  docker run -it $fullName`n"
