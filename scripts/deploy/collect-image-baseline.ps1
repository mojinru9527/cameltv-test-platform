[CmdletBinding()]
param(
    [string[]]$Images = @(),
    [string]$Output = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Invoke-JsonCommand {
    param([string[]]$Arguments)
    try {
        $output = @(& docker @Arguments 2>&1)
        if ($LASTEXITCODE -ne 0) {
            return [pscustomobject]@{ ok = $false; error = ($output -join [Environment]::NewLine) }
        }
        return [pscustomobject]@{ ok = $true; output = ($output -join [Environment]::NewLine) }
    }
    catch {
        return [pscustomobject]@{ ok = $false; error = $_.Exception.Message }
    }
}

$root = (& git rev-parse --show-toplevel).Trim()
$dockerVersion = Invoke-JsonCommand -Arguments @("version", "--format", "{{.Server.Version}}")
$dockerAvailable = $dockerVersion.ok

$imageRows = @()
foreach ($image in $Images) {
    if (-not $image) { continue }
    $row = [ordered]@{ image = $image; available = $false; size_bytes = $null; size_mib = $null }
    if ($dockerAvailable) {
        $inspect = Invoke-JsonCommand -Arguments @("image", "inspect", "--format", "{{.Size}}", $image)
        if ($inspect.ok) {
            $bytes = [int64]$inspect.output.Trim()
            $row.available = $true
            $row.size_bytes = $bytes
            $row.size_mib = [math]::Round($bytes / 1MB, 2)
        }
        else {
            $row.error = $inspect.error
        }
    }
    $imageRows += [pscustomobject]$row
}

$dockerfilePath = Join-Path $root "test-platform-v2/backend/Dockerfile"
$dockerfile = Get-Content -Raw -LiteralPath $dockerfilePath
$targets = [regex]::Matches($dockerfile, "(?m)^FROM\s+\S+\s+AS\s+(\S+)\s*$") |
    ForEach-Object { $_.Groups[1].Value }
$frontendDockerfile = Get-Content -Raw -LiteralPath (Join-Path $root "test-platform-v2/frontend/Dockerfile")

$payload = [ordered]@{
    collected_at = (Get-Date).ToString("o")
    git_head = (& git rev-parse HEAD).Trim()
    docker_available = $dockerAvailable
    docker_server_version = if ($dockerAvailable) { $dockerVersion.output.Trim() } else { "" }
    docker_error = if ($dockerAvailable) { "" } else { $dockerVersion.error }
    images = $imageRows
    static = [ordered]@{
        backend_targets = @($targets)
        backend_cache_mounts = ([regex]::Matches($dockerfile, "--mount=type=cache").Count)
        frontend_cache_mounts = ([regex]::Matches($frontendDockerfile, "--mount=type=cache").Count)
        execution_overlay = Test-Path -LiteralPath (Join-Path $root "test-platform-v2/deploy/docker-compose.execution.yml")
    }
}

$json = $payload | ConvertTo-Json -Depth 8
if ($Output) {
    $outputPath = [System.IO.Path]::GetFullPath($Output)
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $outputPath) | Out-Null
    $json | Set-Content -Encoding UTF8 -LiteralPath $outputPath
}
$json
