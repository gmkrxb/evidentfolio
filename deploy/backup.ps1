param(
    [Parameter(Mandatory = $true)]
    [string]$Destination
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$destinationPath = [System.IO.Path]::GetFullPath($Destination)
New-Item -ItemType Directory -Force -Path $destinationPath | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$archivePath = Join-Path $destinationPath "portfolio-backup-$timestamp.zip"
$targets = @(
    (Join-Path $projectRoot "data"),
    (Join-Path $projectRoot "uploads"),
    (Join-Path $projectRoot "deploy\config\config.py")
)
Compress-Archive -LiteralPath $targets -DestinationPath $archivePath -CompressionLevel Optimal
Write-Output $archivePath

