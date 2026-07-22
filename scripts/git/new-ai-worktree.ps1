[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [Alias("Owner")]
    [ValidateSet("claude", "codex", "human")]
    [string]$Executor,

    [ValidateSet("direct", "agent-team")]
    [string]$Workflow = "direct",

    [Parameter(Mandatory)]
    [ValidateSet("feature", "fix", "hotfix", "release")]
    [string]$Kind,

    [Parameter(Mandatory)]
    [string]$Task,

    [Parameter(Mandatory)]
    [string[]]$Scope,

    [Parameter(Mandatory)]
    [ValidateRange(1024, 65535)]
    [int]$FrontendPort,

    [Parameter(Mandatory)]
    [ValidateRange(1024, 65535)]
    [int]$BackendPort,

    [string]$RepositoryPath = (Get-Location).Path,
    [string]$DestinationRoot,
    [string]$BaseBranch = "main"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Invoke-CheckedGit {
    param([string]$Path, [string[]]$Arguments)
    $output = @(& git -C $Path @Arguments 2>&1)
    if ($LASTEXITCODE -ne 0) {
        throw "git $($Arguments -join ' ') failed in ${Path}: $($output -join [Environment]::NewLine)"
    }
    return $output
}

if ($Task.Length -gt 50 -or $Task -notmatch '^[a-z0-9]+(?:-[a-z0-9]+)*$') {
    throw "Task must be lowercase kebab-case and no longer than 50 characters."
}
if ($Workflow -eq "agent-team" -and $Executor -eq "human") {
    throw "Agent Team workflow executor must be claude or codex."
}
if ($FrontendPort -eq $BackendPort) {
    throw "Frontend and backend ports must be different."
}

$rootOutput = @(Invoke-CheckedGit -Path $RepositoryPath -Arguments @("rev-parse", "--show-toplevel"))
$root = $rootOutput[0].Trim()
if (-not $DestinationRoot) {
    $DestinationRoot = Join-Path (Split-Path -Parent $root) "CamelTv-worktrees"
}
$destinationRootFull = [System.IO.Path]::GetFullPath($DestinationRoot)
$branch = "$Kind/$Task"
$destination = [System.IO.Path]::GetFullPath((Join-Path $destinationRootFull "$Executor-$Task"))
$rootPrefix = $destinationRootFull.TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
if (-not $destination.StartsWith($rootPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Destination escaped the approved worktree root."
}
if (Test-Path -LiteralPath $destination) {
    throw "Destination already exists: $destination"
}

Invoke-CheckedGit -Path $root -Arguments @("fetch", "origin", "--prune") | Out-Null
Invoke-CheckedGit -Path $root -Arguments @("show-ref", "--verify", "--quiet", "refs/remotes/origin/$BaseBranch") | Out-Null

& git -C $root show-ref --verify --quiet "refs/heads/$branch"
if ($LASTEXITCODE -eq 0) { throw "Local branch already exists: $branch" }
& git -C $root show-ref --verify --quiet "refs/remotes/origin/$branch"
if ($LASTEXITCODE -eq 0) { throw "Remote branch already exists: $branch" }

foreach ($line in @(Invoke-CheckedGit -Path $root -Arguments @("worktree", "list", "--porcelain"))) {
    if (-not $line.StartsWith("worktree ")) { continue }
    $existingPath = $line.Substring(9)
    $existingMetadata = Join-Path $existingPath ".ai-worktree.json"
    if (-not (Test-Path -LiteralPath $existingMetadata)) { continue }
    $entry = Get-Content -Raw -LiteralPath $existingMetadata | ConvertFrom-Json
    if ([int]$entry.ports.frontend -eq $FrontendPort -or [int]$entry.ports.backend -eq $BackendPort) {
        throw "Port collision with worktree '$existingPath'."
    }
}

New-Item -ItemType Directory -Path $destinationRootFull -Force | Out-Null
Invoke-CheckedGit -Path $root -Arguments @("worktree", "add", "-b", $branch, $destination, "origin/$BaseBranch") | Out-Null

$metadata = [ordered]@{
    schema_version = 2
    workflow = $Workflow
    executor = $Executor
    task = $Task
    branch = $branch
    base = "origin/$BaseBranch"
    created_at = (Get-Date).ToString("o")
    scope = @($Scope)
    ports = [ordered]@{ frontend = $FrontendPort; backend = $BackendPort }
}
$metadata | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $destination ".ai-worktree.json")

$frontendEnvPath = Join-Path $destination "test-platform-v2/frontend/.env.local"
$backendEnvPath = Join-Path $destination "test-platform-v2/backend/.env"
New-Item -ItemType Directory -Path (Split-Path -Parent $frontendEnvPath) -Force | Out-Null
New-Item -ItemType Directory -Path (Split-Path -Parent $backendEnvPath) -Force | Out-Null
@(
    "VITE_DEV_PORT=$FrontendPort"
    "VITE_PROXY_TARGET=http://127.0.0.1:$BackendPort"
) | Set-Content -Encoding UTF8 -LiteralPath $frontendEnvPath
@(
    "ENVIRONMENT=development"
    "DATABASE_URL=sqlite:///./data/platform-$Task.db"
    "ALLOWED_ORIGINS=http://localhost:$FrontendPort,http://127.0.0.1:$FrontendPort"
) | Set-Content -Encoding UTF8 -LiteralPath $backendEnvPath

$verifyScript = Join-Path $PSScriptRoot "verify-ai-worktree.ps1"
& $verifyScript -RepositoryPath $destination -BaseBranch $BaseBranch -RequireClean -RequireMetadata -ExpectedWorkflow $Workflow -ExpectedExecutor $Executor
if ($LASTEXITCODE -ne 0) { throw "Created worktree failed verification." }

[pscustomobject]@{ Path=$destination; Branch=$branch; Base="origin/$BaseBranch"; Workflow=$Workflow; Executor=$Executor; FrontendPort=$FrontendPort; BackendPort=$BackendPort; FrontendEnv=$frontendEnvPath; BackendEnv=$backendEnvPath }
