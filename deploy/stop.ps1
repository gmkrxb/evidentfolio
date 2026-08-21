$ErrorActionPreference = "Stop"
$containerName = "portfolio"
$existing = docker ps -a --filter "name=^/$containerName$" --format "{{.Names}}"
if ($existing) {
    docker stop $containerName | Out-Null
}
Write-Output "Portfolio container stopped. Data and uploads were preserved."
