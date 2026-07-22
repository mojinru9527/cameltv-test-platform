[CmdletBinding()]
param(
    [string]$RepositoryPath = (Get-Location).Path,
    [int]$PrNumber,
    [ValidateSet("direct", "agent-team")]
    [string]$ExpectedWorkflow,
    [ValidateSet("claude", "codex", "human")]
    [string]$ExpectedExecutor,
    [ValidateSet("claude", "codex", "human", "agent-team")]
    [string]$ExpectedOwner,
    [switch]$RequireSuccessfulChecks
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$requiredChecks = @(
    "AI/Git 交付策略",
    "后端全新检出与全量回归",
    "前端全新检出与全量回归"
)

function Invoke-CheckedGit {
    param([string]$Path, [string[]]$Arguments)
    $output = @(& git -C $Path @Arguments 2>&1)
    if ($LASTEXITCODE -ne 0) {
        throw "git $($Arguments -join ' ') failed in ${Path}: $($output -join [Environment]::NewLine)"
    }
    return $output
}

function Invoke-CheckedGh {
    param([string[]]$Arguments)
    $output = @(& gh @Arguments 2>&1)
    if ($LASTEXITCODE -ne 0) {
        throw "gh $($Arguments -join ' ') failed: $($output -join [Environment]::NewLine)"
    }
    return ($output -join [Environment]::NewLine)
}

function Test-PathInScope {
    param([string]$Path, [string[]]$Scope)
    $normalizedPath = $Path.Replace("\", "/")
    if ($normalizedPath.StartsWith("./")) { $normalizedPath = $normalizedPath.Substring(2) }
    foreach ($entry in $Scope) {
        $normalizedScope = $entry.Replace("\", "/").Trim()
        if ($normalizedScope.StartsWith("./")) { $normalizedScope = $normalizedScope.Substring(2) }
        $normalizedScope = $normalizedScope.TrimEnd("/")
        if ($normalizedScope -eq "*" -or $normalizedPath -eq $normalizedScope -or $normalizedPath.StartsWith("$normalizedScope/", [System.StringComparison]::OrdinalIgnoreCase)) {
            return $true
        }
    }
    return $false
}

$root = (@(Invoke-CheckedGit -Path $RepositoryPath -Arguments @("rev-parse", "--show-toplevel")))[0].Trim()
$verifyArguments = @{
    RepositoryPath = $root
    RequireMetadata = $true
    RequireClean = $true
}
if ($ExpectedWorkflow) { $verifyArguments.ExpectedWorkflow = $ExpectedWorkflow }
if ($ExpectedExecutor) { $verifyArguments.ExpectedExecutor = $ExpectedExecutor }
if ($ExpectedOwner) { $verifyArguments.ExpectedOwner = $ExpectedOwner }
$verifyOutput = @(& (Join-Path $PSScriptRoot "verify-ai-worktree.ps1") @verifyArguments)
$verification = $verifyOutput[-1]

$branch = (@(Invoke-CheckedGit -Path $root -Arguments @("branch", "--show-current")))[0].Trim()
Invoke-CheckedGit -Path $root -Arguments @("fetch", "origin", "--prune") | Out-Null
$upstream = (@(Invoke-CheckedGit -Path $root -Arguments @("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")))[0].Trim()
if ($upstream -ne "origin/$branch") {
    throw "Current branch upstream '$upstream' must be 'origin/$branch'."
}

$head = (@(Invoke-CheckedGit -Path $root -Arguments @("rev-parse", "HEAD")))[0].Trim()
$remoteHead = (@(Invoke-CheckedGit -Path $root -Arguments @("rev-parse", "refs/remotes/origin/$branch")))[0].Trim()
if ($head -ne $remoteHead) {
    throw "Local HEAD '$head' does not match pushed remote HEAD '$remoteHead'."
}

$aheadBehind = ((@(Invoke-CheckedGit -Path $root -Arguments @("rev-list", "--left-right", "--count", "origin/main...HEAD")))[0].Trim() -split "\s+")
if ([int]$aheadBehind[0] -ne 0) {
    throw "Branch is behind origin/main by $($aheadBehind[0]) commit(s); merge origin/main before PR approval."
}

$metadata = Get-Content -Raw -LiteralPath (Join-Path $root ".ai-worktree.json") | ConvertFrom-Json
$scope = @()
foreach ($entry in @($metadata.scope)) {
    $scope += @([string]$entry -split "," | ForEach-Object { $_.Trim() } | Where-Object { $_ })
}

$prArguments = @("pr", "view")
if ($PrNumber) { $prArguments += [string]$PrNumber }
$prArguments += @("--json", "number,state,isDraft,baseRefName,headRefName,headRefOid,mergeStateStatus,statusCheckRollup,files,url")
$pr = Invoke-CheckedGh -Arguments $prArguments | ConvertFrom-Json
if ($pr.state -ne "OPEN") { throw "PR #$($pr.number) must be OPEN for delivery audit; state=$($pr.state)." }
if ($pr.baseRefName -ne "main") { throw "PR base '$($pr.baseRefName)' must be 'main'." }
if ($pr.headRefName -ne $branch) { throw "PR head '$($pr.headRefName)' does not match current branch '$branch'." }
if ($pr.headRefOid -ne $head) { throw "PR head SHA '$($pr.headRefOid)' does not match local/remote HEAD '$head'." }

$outOfScope = @($pr.files | Where-Object { -not (Test-PathInScope -Path $_.path -Scope $scope) } | ForEach-Object { $_.path })
if ($outOfScope.Count -gt 0) {
    throw "PR contains file(s) outside declared worktree scope: $($outOfScope -join ', ')"
}

$repoName = (Invoke-CheckedGh -Arguments @("repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner")).Trim()
$repository = Invoke-CheckedGh -Arguments @("api", "repos/$repoName") | ConvertFrom-Json
if ($repository.default_branch -ne "main") { throw "Repository default branch must be main." }
if (-not $repository.allow_squash_merge -or $repository.allow_merge_commit -or $repository.allow_rebase_merge) {
    throw "Repository must allow squash merge only."
}
if (-not $repository.delete_branch_on_merge) { throw "Repository must delete task branches after merge." }

$checkResults = @()
foreach ($name in $requiredChecks) {
    $check = @($pr.statusCheckRollup | Where-Object name -eq $name | Select-Object -Last 1)
    $status = if ($check.Count -eq 1) { [string]$check[0].status } else { "MISSING" }
    $conclusion = if ($check.Count -eq 1) { [string]$check[0].conclusion } else { "MISSING" }
    $checkResults += [pscustomobject]@{ Name = $name; Status = $status; Conclusion = $conclusion }
    if ($RequireSuccessfulChecks -and ($status -ne "COMPLETED" -or $conclusion -ne "SUCCESS")) {
        throw "Required check '$name' is not successful: status=$status conclusion=$conclusion"
    }
}

$result = [pscustomobject]@{
    PullRequest = [int]$pr.number
    Url = [string]$pr.url
    Workflow = [string]$verification.Workflow
    Executor = [string]$verification.Executor
    Branch = $branch
    Base = [string]$pr.baseRefName
    Head = $head
    Draft = [bool]$pr.isDraft
    MergeState = [string]$pr.mergeStateStatus
    Scope = $scope -join ","
    ChecksRequired = [bool]$RequireSuccessfulChecks
    Checks = $checkResults
}

$result | Format-List PullRequest,Url,Workflow,Executor,Branch,Base,Head,Draft,MergeState,Scope,ChecksRequired
$checkResults | Format-Table -AutoSize
$result
