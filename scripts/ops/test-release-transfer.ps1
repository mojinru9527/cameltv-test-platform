$ErrorActionPreference = 'Stop'
$transferScript = Join-Path $PSScriptRoot 'release-transfer.ps1'
$root = Join-Path ([IO.Path]::GetTempPath()) ('capacity-transfer-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $root | Out-Null
$source = Join-Path $root 'source.txt'
$destination = Join-Path $root 'received.txt'
Set-Content -LiteralPath $source -Value 'local transfer probe'
try {
    . $transferScript
    Send-ReleaseArchive -KeyPath (Join-Path $root 'unused.key') -Source $source -Destination $destination
    if ((Get-FileHash -LiteralPath $source).Hash -ne (Get-FileHash -LiteralPath $destination).Hash) {
        throw 'Successful transfer changed contents'
    }
    $job = Start-Job -ScriptBlock {
        param($script, $root)
        . $script
        Send-ReleaseArchive -KeyPath (Join-Path $root 'unused.key') `
            -Source (Join-Path $root 'missing.tar') -Destination (Join-Path $root 'missing-target.tar')
    } -ArgumentList $transferScript, $root
    $rejected = $false
    try { Wait-ReleaseUploads -Jobs @($job) }
    catch {
        if ($_.Exception.Message -notmatch 'upload failed') { throw }
        $rejected = $true
    }
    if (-not $rejected) { throw 'Nonzero scp exit was incorrectly accepted as a completed upload' }
    if (Get-Job -Id $job.Id -ErrorAction SilentlyContinue) { throw 'Finished upload job was not cleaned up' }
    Write-Host 'PASS: successful archive content verified; native scp failure fails the background upload'
} finally {
    Remove-Item -LiteralPath $source -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $destination -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $root
}
