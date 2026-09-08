$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'capacity.ps1')

$script:sshCalls = 0
$script:sshExit = 0
$script:sshResponse = '{"ok":true}'
function ssh {
    $script:sshCalls++
    $script:lastRemoteCommand = $args[-1]
    $global:LASTEXITCODE = $script:sshExit
    return $script:sshResponse
}

$parameters = @{
    HostName = 'example.invalid'; UserName = 'tester'; KeyPath = 'unused'
    ReleaseDir = '/opt/path with spaces/$(must-not-run)'
    Archives = @((Join-Path $PSScriptRoot 'capacity.ps1'), (Join-Path $PSScriptRoot 'test-capacity.ps1'))
}
Assert-ReleaseUploadCapacity @parameters
if ($script:sshCalls -ne 1) { throw 'Expected one SSH inspection' }
if ($script:lastRemoteCommand.Contains('$(must-not-run)')) { throw 'Unescaped path reached shell' }
$matches64 = [regex]::Matches($script:lastRemoteCommand, "b64decode\('([A-Za-z0-9+/=]+)'\)")
if ($matches64.Count -ne 2) { throw 'Expected encoded source and structured arguments' }
$payload = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($matches64[1].Groups[1].Value)) | ConvertFrom-Json
if ($payload.release_dir -ne $parameters.ReleaseDir -or $payload.stage -ne 'upload' -or $payload.archive_bytes -le 0) {
    throw 'Upload capacity payload did not preserve arguments'
}

foreach ($failure in @('remote-error', 'invalid-json', 'not-ok', 'missing-file')) {
    $script:sshExit = 0
    $script:sshResponse = '{"ok":true}'
    if ($failure -eq 'remote-error') { $script:sshExit = 1 }
    if ($failure -eq 'invalid-json') { $script:sshResponse = 'not-json' }
    if ($failure -eq 'not-ok') { $script:sshResponse = '{"ok":false}' }
    if ($failure -eq 'missing-file') { $parameters.Archives = @('does-not-exist', 'also-missing') }
    $rejected = $false
    try { Assert-ReleaseUploadCapacity @parameters } catch { $rejected = $true }
    if (-not $rejected) { throw "Expected fail-closed behavior: $failure" }
}
$global:LASTEXITCODE = 0
Write-Host 'PASS: upload admission payload, shell isolation and four rejection paths.'
