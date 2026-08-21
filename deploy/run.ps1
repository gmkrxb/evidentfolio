param(
    [int]$Port = 8080,
    [switch]$Build,
    [switch]$Recreate
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$configPath = Join-Path $projectRoot "deploy\config\config.py"
$dataPath = Join-Path $projectRoot "data"
$uploadsPath = Join-Path $projectRoot "uploads"
$containerName = "evidentfolio"
$imageName = "evidentfolio:local"

if (-not (Test-Path -LiteralPath $configPath)) {
    throw "Missing config: copy deploy/config/config.example.py to deploy/config/config.py first."
}

New-Item -ItemType Directory -Force -Path $dataPath, $uploadsPath | Out-Null

if ($Build) {
    docker build --platform linux/amd64 --provenance=false `
        -t $imageName `
        -f (Join-Path $projectRoot "Dockerfile.unified") `
        $projectRoot
    if ($LASTEXITCODE -ne 0) {
        throw "Unified image build failed."
    }
}

$existing = docker ps -a --filter "name=^/$containerName$" --format "{{.Names}}"
if ($existing -and -not $Recreate) {
    throw "Container '$containerName' already exists. Run with -Recreate to replace only this container."
}
if ($existing -and $Recreate) {
    docker rm -f $containerName | Out-Null
}

docker run -d `
    --name $containerName `
    --restart unless-stopped `
    -p "${Port}:80" `
    -v "${dataPath}:/app/data" `
    -v "${uploadsPath}:/app/uploads" `
    -v "${configPath}:/app/config/config.py:ro" `
    $imageName | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to start the unified EvidentFolio container."
}

Write-Output "EvidentFolio started as one container at http://localhost:$Port"
Write-Output "Image: $imageName"
Write-Output "Health check: http://localhost:$Port/api/health"
