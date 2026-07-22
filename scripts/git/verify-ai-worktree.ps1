[CmdletBinding()]
param(
    [string]$RepositoryPath = (Get-Location).Path,
    [string]$BaseBranch = "main",
    [switch]$RequireClean
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Invoke-CheckedGit {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [string[]]$Arguments
    )

    $output = @(& git -C $Path @Arguments 2>&1)
    if ($LASTEXITCODE -ne 0) {
        throw "git $($Arguments -join ' ') failed in ${Path}: $($output -join [Environment]::NewLine)"
    }
    return $output
}

$rootOutput = @(Invoke-CheckedGit -Path $RepositoryPath -Arguments @("rev-parse", "--show-toplevel"))
$root = $rootOutput[0].Trim()
$branchOutput = @(Invoke-CheckedGit -Path $root -Arguments @("branch", "--show-current"))
$branch = $branchOutput[0].Trim()
if (-not $branch) {
    throw "Detached HEAD is not allowed for AI development."
}

$protectedBranches = @("main", "master", "develop")
if ($protectedBranches -contains $branch) {
    throw "AI development is blocked on protected branch '$branch'. Create a task worktree first."
}
if ($branch -notmatch '^(feature|fix|hotfix|release)/[a-z0-9]+(?:-[a-z0-9]+)*$') {
    throw "Branch '$branch' does not match feature|fix|hotfix|release task naming."
}

Invoke-CheckedGit -Path $root -Arguments @("show-ref", "--verify", "--quiet", "refs/remotes/origin/$BaseBranch") | Out-Null
$dirty = @(Invoke-CheckedGit -Path $root -Arguments @("status", "--porcelain=v1"))
if ($RequireClean -and $dirty.Count -gt 0) {
    throw "Worktree '$root' must be clean before development starts: $($dirty -join '; ')"
}

$aheadBehindOutput = @(Invoke-CheckedGit -Path $root -Arguments @("rev-list", "--left-right", "--count", "origin/$BaseBranch...HEAD"))
$aheadBehind = $aheadBehindOutput[0] -split '\s+'
$behind = [int]$aheadBehind[0]
$ahead = [int]$aheadBehind[1]
$metadataPath = Join-Path $root ".ai-worktree.json"
$metadata = $null
if (Test-Path -LiteralPath $metadataPath) {
    $metadata = Get-Content -Raw -LiteralPath $metadataPath | ConvertFrom-Json
}

$result = [pscustomobject]@{
    Root = $root
    Branch = $branch
    Base = "origin/$BaseBranch"
    Ahead = $ahead
    Behind = $behind
    DirtyFiles = $dirty.Count
    Owner = if ($metadata) { $metadata.owner } else { $null }
    Task = if ($metadata) { $metadata.task } else { $null }
}

$result | Format-List
Write-Host "Active worktrees:"
Invoke-CheckedGit -Path $root -Arguments @("worktree", "list") | ForEach-Object { Write-Host "  $_" }
$result
