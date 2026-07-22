[CmdletBinding()]
param(
    [string]$RepositoryPath = (Get-Location).Path,
    [string]$BaseBranch = "main",
    [switch]$RequireClean,
    [switch]$RequireMetadata,
    [ValidateSet("claude", "codex", "human", "agent-team")]
    [string]$ExpectedOwner
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
elseif ($RequireMetadata -or $ExpectedOwner) {
    throw "Worktree metadata is required but missing: $metadataPath"
}

if ($metadata) {
    $allowedOwners = @("claude", "codex", "human", "agent-team")
    $owner = [string]$metadata.owner
    $task = [string]$metadata.task
    $metadataBranch = [string]$metadata.branch
    $metadataBase = [string]$metadata.base
    $scope = @(@($metadata.scope) | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) })
    $frontendPort = [int]$metadata.ports.frontend
    $backendPort = [int]$metadata.ports.backend
    $expectedTask = ($branch -split "/", 2)[1]
    $expectedDirectory = "$owner-$task"

    if ($allowedOwners -notcontains $owner) { throw "Unknown metadata owner '$owner'." }
    if ($ExpectedOwner -and $owner -ne $ExpectedOwner) {
        throw "Worktree owner '$owner' does not match expected owner '$ExpectedOwner'."
    }
    if ($metadataBranch -ne $branch) {
        throw "Metadata branch '$metadataBranch' does not match current branch '$branch'."
    }
    if ($metadataBase -ne "origin/$BaseBranch") {
        throw "Metadata base '$metadataBase' must be 'origin/$BaseBranch'."
    }
    if ($task -ne $expectedTask) {
        throw "Metadata task '$task' does not match branch task '$expectedTask'."
    }
    if ((Split-Path -Leaf $root) -ne $expectedDirectory) {
        throw "Worktree directory must be '$expectedDirectory' for owner '$owner' and task '$task'."
    }
    if ($scope.Count -eq 0) { throw "Worktree scope must contain at least one path." }
    if ($frontendPort -lt 1024 -or $frontendPort -gt 65535 -or $backendPort -lt 1024 -or $backendPort -gt 65535 -or $frontendPort -eq $backendPort) {
        throw "Worktree frontend/backend ports must be distinct values between 1024 and 65535."
    }
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
    Scope = if ($metadata) { @($metadata.scope) -join "," } else { $null }
}

$result | Format-List
Write-Host "Active worktrees:"
Invoke-CheckedGit -Path $root -Arguments @("worktree", "list") | ForEach-Object { Write-Host "  $_" }
$result
