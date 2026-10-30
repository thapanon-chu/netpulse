# Build script for NetPulse Standalone Portable Bundle
# Creates a self-contained zero-dependency Windows distribution

param(
    [string]$DistDir = "$PSScriptRoot\..\dist",
    [switch]$SkipZip = $false
)

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path "$PSScriptRoot\..").Path
$BundleName = "NetPulse-v2.4-Portable"
$TargetDir = Join-Path $DistDir $BundleName
$RuntimeDir = Join-Path $TargetDir "runtime"
$SitePackagesDir = Join-Path $RuntimeDir "Lib\site-packages"

Write-Host "========================================"
Write-Host "NetPulse Portable Bundle Builder"
Write-Host "========================================"
Write-Host "Project Root: $ProjectRoot"
Write-Host "Target Dir  : $TargetDir"

# Clean target directory
if (Test-Path $TargetDir) {
    Write-Host "Cleaning previous build..."
    Remove-Item -Recurse -Force $TargetDir
}
New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
New-Item -ItemType Directory -Path $RuntimeDir -Force | Out-Null
New-Item -ItemType Directory -Path $SitePackagesDir -Force | Out-Null

# Copy application files
Write-Host "Copying core application files..."
$FilesToCopy = @(
    "app.py",
    "tracker.py",
    "analytics.py",
    "tray_app.py",
    "user_settings.json",
    "requirements.txt",
    "LICENSE",
    "README.md",
    "Start-NetPulse.bat",
    "Stop-NetPulse.bat"
)

foreach ($file in $FilesToCopy) {
    $src = Join-Path $ProjectRoot $file
    if (Test-Path $src) {
        Copy-Item -Path $src -Destination $TargetDir -Force
    }
}

# Copy directories
$DirsToCopy = @("assets", "docs", "scripts", ".streamlit")
foreach ($dir in $DirsToCopy) {
    $src = Join-Path $ProjectRoot $dir
    if (Test-Path $src) {
        Copy-Item -Path $src -Destination (Join-Path $TargetDir $dir) -Recurse -Force
    }
}

# Download and extract Python 3.12 embeddable package
$EmbedZipUrl = "https://www.python.org/ftp/python/3.12.5/python-3.12.5-embed-amd64.zip"
$CacheZipPath = Join-Path $env:TEMP "python-3.12.5-embed-amd64.zip"

if (-not (Test-Path $CacheZipPath)) {
    Write-Host "Downloading Python 3.12.5 embeddable distribution..."
    Invoke-WebRequest -Uri $EmbedZipUrl -OutFile $CacheZipPath
} else {
    Write-Host "Using cached Python embeddable zip..."
}

Write-Host "Extracting Python runtime to bundle..."
Expand-Archive -Path $CacheZipPath -DestinationPath $RuntimeDir -Force

# Configure python312._pth to enable site-packages
Write-Host "Configuring Python path and site-packages..."
$PthFile = Join-Path $RuntimeDir "python312._pth"
$PthContent = @"
python312.zip
.
Lib/site-packages
import site
"@
Set-Content -Path $PthFile -Value $PthContent -Encoding ASCII

# Install dependencies into runtime site-packages
Write-Host "Installing dependencies into portable runtime..."
$ReqFile = Join-Path $ProjectRoot "requirements.txt"
& python -m pip install --target $SitePackagesDir -r $ReqFile --no-warn-script-location

# Verify runtime execution
Write-Host "Verifying portable runtime packages..."
$VerifyCmd = Join-Path $RuntimeDir "python.exe"
$VerifyScript = "import streamlit, psutil, pandas, plotly, sklearn, pystray, PIL; print('Portable runtime verified successfully.')"
& $VerifyCmd -c $VerifyScript

if ($LASTEXITCODE -ne 0) {
    Write-Error "Portable runtime verification failed."
    exit 1
}

# Optionally create zip archive
if (-not $SkipZip) {
    $ZipPath = Join-Path $DistDir "$BundleName.zip"
    if (Test-Path $ZipPath) {
        Remove-Item -Force $ZipPath
    }
    Write-Host "Creating zip archive: $ZipPath..."
    Compress-Archive -Path "$TargetDir\*" -DestinationPath $ZipPath -CompressionLevel Optimal
    $ZipSizeMB = [math]::Round((Get-Item $ZipPath).Length / 1MB, 2)
    Write-Host "Archive created successfully: $ZipSizeMB MB"
}

Write-Host "========================================"
Write-Host "Build complete: $TargetDir"
Write-Host "========================================"
