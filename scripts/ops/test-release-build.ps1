$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'release-build.ps1')
$metadataFile = [IO.Path]::GetTempFileName()
try {
    $expected = 'a' * 64
    [IO.File]::WriteAllText($metadataFile, (@{'containerimage.config.digest' = "sha256:$expected"} | ConvertTo-Json))
    if ((Get-ExportDigest $metadataFile) -ne $expected) { throw 'Wrong fresh-build digest' }
    foreach ($invalid in @('{}', '{"containerimage.config.digest":"bad"}', 'not-json')) {
        [IO.File]::WriteAllText($metadataFile, $invalid)
        $rejected = $false
        try { Get-ExportDigest $metadataFile | Out-Null } catch { $rejected = $true }
        if (-not $rejected) { throw 'Invalid metadata was accepted' }
    }
    $source = Get-Content (Join-Path $PSScriptRoot 'release.ps1') -Raw
    $release = $source.Substring($source.IndexOf('function Invoke-Release'))
    if ($release.IndexOf('Invoke-BuildxExport') -gt $release.IndexOf('Get-ExportDigest')) {
        throw 'Digest must be read after the fresh export'
    }
    if ($release.IndexOf('Get-ExportDigest') -gt $release.IndexOf('POST')) {
        throw 'Deployment must only be registered after verified build metadata'
    }
    Write-Host 'PASS: fresh digest, invalid metadata rejection and release ordering.'
} finally {
    Remove-Item -LiteralPath $metadataFile
}
