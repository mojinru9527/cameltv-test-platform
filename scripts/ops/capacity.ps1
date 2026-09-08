# Shared upload admission: the remote Python payload contains no credentials.
function Assert-ReleaseUploadCapacity {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)] [string]$HostName,
        [Parameter(Mandatory)] [string]$UserName,
        [Parameter(Mandatory)] [string]$KeyPath,
        [Parameter(Mandatory)] [string]$ReleaseDir,
        [Parameter(Mandatory)] [string[]]$Archives
    )
    if ($Archives.Count -ne 2) { throw 'Expected backend and frontend archives' }
    [long]$archiveBytes = 0
    foreach ($archive in $Archives) {
        $item = Get-Item -LiteralPath $archive -ErrorAction Stop
        if ($item.PSIsContainer -or $item.Length -le 0) { throw 'Archive must be a nonempty file' }
        $archiveBytes += $item.Length
    }
    $sourcePath = Join-Path $PSScriptRoot '../../deploy/release-console/capacity.py'
    $source64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes($sourcePath))
    $argumentsJson = @{
        release_dir = $ReleaseDir; stage = 'upload'; archive_bytes = $archiveBytes
    } | ConvertTo-Json -Compress
    $arguments64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($argumentsJson))
    $pythonCode = "import base64,json; ns={'__name__':'capacity_remote'}; exec(base64.b64decode('$source64'),ns); print(json.dumps(ns['check'](**json.loads(base64.b64decode('$arguments64')))))"
    $output = & ssh -i $KeyPath -o BatchMode=yes -o ConnectTimeout=15 `
        "${UserName}@${HostName}" "python3 -c `"$pythonCode`"" 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Release upload capacity check failed: $output" }
    $result = ($output | Out-String) | ConvertFrom-Json -ErrorAction Stop
    if ($result.ok -ne $true) { throw 'Release upload capacity check did not succeed' }
    Write-Host 'Release upload capacity check passed.'
}
