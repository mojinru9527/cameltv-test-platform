[CmdletBinding()]
param(
    [string]$RepositoryPath = (Get-Location).Path,
    [string]$GitHubLogin,
    [string]$GitHubEmail
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$root = (& git -C $RepositoryPath rev-parse --show-toplevel 2>&1)
if ($LASTEXITCODE -ne 0) { throw "Not a Git repository: $RepositoryPath" }
$root = $root.Trim()

if (-not $GitHubLogin -or -not $GitHubEmail) {
    $identity = (& gh api user 2>&1 | ConvertFrom-Json)
    if ($LASTEXITCODE -ne 0) { throw "Unable to read the authenticated GitHub identity." }
    if (-not $GitHubLogin) { $GitHubLogin = $identity.login }
    if (-not $GitHubEmail) {
        $GitHubEmail = if ($identity.email) { $identity.email } else { "$($identity.id)+$($identity.login)@users.noreply.github.com" }
    }
}

$settings = [ordered]@{
    "user.name" = $GitHubLogin
    "user.email" = $GitHubEmail
    "fetch.prune" = "true"
    "push.default" = "current"
    "rerere.enabled" = "true"
    "core.hooksPath" = ".githooks"
    "core.autocrlf" = "false"
}
foreach ($entry in $settings.GetEnumerator()) {
    & git -C $root config --local $entry.Key $entry.Value
    if ($LASTEXITCODE -ne 0) { throw "Failed to set $($entry.Key)." }
}

Write-Host "Installed CamelTv Git guardrails in $root"
$settings.GetEnumerator() | ForEach-Object { [pscustomobject]@{ Key=$_.Key; Value=$_.Value } } | Format-Table -AutoSize
