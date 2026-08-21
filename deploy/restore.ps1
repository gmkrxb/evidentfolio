param(
    [Parameter(Mandatory = $true)]
    [string]$Archive
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$archivePath = (Resolve-Path -LiteralPath $Archive).Path
$confirmation = Read-Host "Restore will overwrite matching data/upload/config files. Type RESTORE to continue"
if ($confirmation -ne "RESTORE") {
    throw "Restore cancelled"
}
Expand-Archive -LiteralPath $archivePath -DestinationPath $projectRoot -Force
Write-Output "Restore complete: $archivePath"

