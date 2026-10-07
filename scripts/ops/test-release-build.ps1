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
    # 平台简化批次：ai-gateway 独立服务已删除，split 发布只包含
    # backend(api target) + frontend + runner 三个制品，并用 -deploy.yml
    # 钉住唯一的部署 compose 配置。
    $requiredSplitArtifacts = @(
        'cameltv-tp-runner:$Tag',
        '-Target runner',
        '$Tag-runner.tar',
        'runner = @{',
        '$Tag-deploy.yml',
        'execution_config_sha256'
    )
    foreach ($required in $requiredSplitArtifacts) {
        if (-not $release.Contains($required)) {
            throw "Split release is missing simplified artifact contract: $required"
        }
    }
    foreach ($retired in @('ai-gateway', 'AI_GATEWAY')) {
        if ($release.Contains($retired)) {
            throw "Release script still references retired service: $retired"
        }
    }
    Write-Host 'PASS: fresh digest, invalid metadata rejection, release ordering and simplified artifact contract.'
} finally {
    Remove-Item -LiteralPath $metadataFile
}
