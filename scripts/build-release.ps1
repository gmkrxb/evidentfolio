$ErrorActionPreference = 'Stop'

$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Release = Join-Path $Root 'release'
$Stage = Join-Path $Release '.backend-stage'
$RuntimeImage = 'evidentfolio-runtime:latest'

New-Item -ItemType Directory -Force -Path $Release | Out-Null
if (Test-Path -LiteralPath $Stage) {
    $resolvedStage = (Resolve-Path -LiteralPath $Stage).Path
    if (-not $resolvedStage.StartsWith($Release, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Unsafe staging path: $resolvedStage"
    }
    Remove-Item -LiteralPath $resolvedStage -Recurse -Force
}

Push-Location (Join-Path $Root 'frontend')
try {
    cnpm run type-check
    cnpm run test
    cnpm run build
} finally {
    Pop-Location
}

docker build --platform linux/amd64 -f (Join-Path $Root 'Dockerfile.runtime') -t $RuntimeImage $Root
docker save -o (Join-Path $Release 'evidentfolio-runtime-linux-amd64.tar') $RuntimeImage

New-Item -ItemType Directory -Path $Stage | Out-Null
Copy-Item -LiteralPath (Join-Path $Root 'backend\app') -Destination $Stage -Recurse
Copy-Item -LiteralPath (Join-Path $Root 'backend\alembic') -Destination $Stage -Recurse
Copy-Item -LiteralPath (Join-Path $Root 'backend\tests') -Destination $Stage -Recurse
Copy-Item -LiteralPath (Join-Path $Root 'backend\alembic.ini'),(Join-Path $Root 'backend\requirements.txt'),(Join-Path $Root 'backend\pyproject.toml') -Destination $Stage
New-Item -ItemType Directory -Force -Path (Join-Path $Stage 'deploy\config') | Out-Null
Copy-Item -LiteralPath (Join-Path $Root 'deploy\config\config.example.py') -Destination (Join-Path $Stage 'deploy\config\config.example.py')

$FrontendZip = Join-Path $Release 'evidentfolio-frontend.zip'
$BackendZip = Join-Path $Release 'evidentfolio-backend.zip'
Remove-Item -LiteralPath $FrontendZip,$BackendZip -Force -ErrorAction SilentlyContinue
tar.exe -a -c -f $FrontendZip --exclude=write-check.tmp -C (Join-Path $Root 'frontend\dist') .
tar.exe -a -c -f $BackendZip --exclude=__pycache__ --exclude=.pytest_cache --exclude=.runtime -C $Stage .

$Artifacts = @(
    'evidentfolio-runtime-linux-amd64.tar',
    'evidentfolio-frontend.zip',
    'evidentfolio-backend.zip'
)
$Checksums = foreach ($Name in $Artifacts) {
    $Hash = (Get-FileHash (Join-Path $Release $Name) -Algorithm SHA256).Hash.ToLower()
    "$Hash  $Name"
}
Set-Content -LiteralPath (Join-Path $Release 'SHA256SUMS.txt') -Value $Checksums -Encoding utf8NoBOM
Remove-Item -LiteralPath $Stage -Recurse -Force
Write-Host "Release artifacts written to $Release"
