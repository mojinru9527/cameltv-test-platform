#requires -Version 5.1
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$releaseScript = (Resolve-Path (Join-Path (Split-Path $PSScriptRoot -Parent) "release.ps1")).Path
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    $releaseScript,
    [ref]$tokens,
    [ref]$parseErrors
)

if ($parseErrors.Count -gt 0) {
    throw "release.ps1 parse failed: $($parseErrors[0].Message)"
}

function Get-FunctionAst([string]$Name) {
    $result = $ast.Find(
        {
            param($node)
            $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
                $node.Name -eq $Name
        },
        $true
    )
    if (-not $result) { throw "Missing function: $Name" }
    return $result
}

function Assert-True([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
}

$buildxFunction = Get-FunctionAst "Invoke-BuildxExport"
$releaseFunction = Get-FunctionAst "Invoke-Release"
$digestFunction = Get-FunctionAst "Get-BuildxDigest"

Assert-True ($buildxFunction.Extent.Text.Contains("--metadata-file")) `
    "Invoke-BuildxExport must request a Buildx metadata file"
Assert-True ($buildxFunction.Extent.Text.Contains("Remove-Item")) `
    "Invoke-BuildxExport must remove stale metadata before building"

$commands = @($releaseFunction.Body.FindAll(
    { param($node) $node -is [System.Management.Automation.Language.CommandAst] },
    $true
))
$exports = @($commands | Where-Object { $_.GetCommandName() -eq "Invoke-BuildxExport" })
$digests = @($commands | Where-Object { $_.GetCommandName() -eq "Get-BuildxDigest" })
$registration = @($commands | Where-Object { $_.GetCommandName() -eq "Invoke-Api" }) | Select-Object -First 1

Assert-True ($exports.Count -eq 2) "Invoke-Release must export backend and frontend exactly once"
Assert-True ($digests.Count -eq 2) "Invoke-Release must read backend and frontend metadata exactly once"
Assert-True ($null -ne $registration) "Invoke-Release must register the release"
Assert-True (($exports | Measure-Object -Property { $_.Extent.StartOffset } -Maximum).Maximum -lt
    ($digests | Measure-Object -Property { $_.Extent.StartOffset } -Minimum).Minimum) `
    "Both Buildx exports must finish before digest extraction"
Assert-True (($digests | Measure-Object -Property { $_.Extent.StartOffset } -Maximum).Maximum -lt
    $registration.Extent.StartOffset) `
    "Digest extraction must finish before release registration"

# Load only the digest helper so the test never runs the release entry point.
Invoke-Expression $digestFunction.Extent.Text
$tempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("cameltv-release-test-" + [guid]::NewGuid())
New-Item -ItemType Directory -Path $tempDir | Out-Null
try {
    $primary = Join-Path $tempDir "primary.json"
    $fallback = Join-Path $tempDir "fallback.json"
    $invalid = Join-Path $tempDir "invalid.json"
    $primaryDigest = "sha256:" + ("a" * 64)
    $fallbackDigest = "sha256:" + ("b" * 64)

    @{ "containerimage.config.digest" = $primaryDigest } |
        ConvertTo-Json | Set-Content -LiteralPath $primary -Encoding UTF8
    @{ "containerimage.digest" = $fallbackDigest } |
        ConvertTo-Json | Set-Content -LiteralPath $fallback -Encoding UTF8
    @{ "containerimage.config.digest" = "sha256:not-a-digest" } |
        ConvertTo-Json | Set-Content -LiteralPath $invalid -Encoding UTF8

    Assert-True ((Get-BuildxDigest $primary) -eq ("a" * 64)) `
        "The config digest must be preferred"
    Assert-True ((Get-BuildxDigest $fallback) -eq ("b" * 64)) `
        "The image digest must be accepted as fallback"

    foreach ($path in @($invalid, (Join-Path $tempDir "missing.json"))) {
        $failedClosed = $false
        try { Get-BuildxDigest $path | Out-Null } catch { $failedClosed = $true }
        Assert-True $failedClosed "Missing or invalid metadata must fail closed: $path"
    }
} finally {
    Remove-Item -LiteralPath $tempDir -Recurse -Force
}

Write-Host "release.ps1 regression checks passed"
