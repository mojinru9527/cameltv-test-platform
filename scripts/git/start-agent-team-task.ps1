[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet("claude", "codex")]
    [string]$Executor,
    [switch]$UserConfirmedExecutor,
    [Parameter(Mandatory)]
    [ValidateSet("feature", "fix", "hotfix", "release")]
    [string]$Kind,
    [Parameter(Mandatory)] [string]$Task,
    [Parameter(Mandatory)] [string[]]$Scope,
    [Parameter(Mandatory)] [ValidateRange(1024, 65535)] [int]$FrontendPort,
    [Parameter(Mandatory)] [ValidateRange(1024, 65535)] [int]$BackendPort,
    [string]$RepositoryPath = (Get-Location).Path,
    [string]$DestinationRoot
)

$ErrorActionPreference = "Stop"
if (-not $UserConfirmedExecutor) {
    throw "Agent Team must ask the user whether this task runs in Claude Code or Codex and wait for the explicit reply before starting. After confirmation, rerun with -UserConfirmedExecutor."
}
$arguments = @{
    Executor = $Executor
    Workflow = "agent-team"
    Kind = $Kind
    Task = $Task
    Scope = $Scope
    FrontendPort = $FrontendPort
    BackendPort = $BackendPort
    RepositoryPath = $RepositoryPath
    UserConfirmedExecutor = $true
}
if ($DestinationRoot) { $arguments.DestinationRoot = $DestinationRoot }

& (Join-Path $PSScriptRoot "new-ai-worktree.ps1") @arguments
