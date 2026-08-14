[CmdletBinding()]
param(
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

# (batch-173) DeepSeek Harness 直接任务入口：与 start-codex-task.ps1 同构，executor 标识为 DeepSeek_Harness。
$ErrorActionPreference = "Stop"
$arguments = @{
    Executor = "DeepSeek_Harness"
    Workflow = "direct"
    Kind = $Kind
    Task = $Task
    Scope = $Scope
    FrontendPort = $FrontendPort
    BackendPort = $BackendPort
    RepositoryPath = $RepositoryPath
}
if ($DestinationRoot) { $arguments.DestinationRoot = $DestinationRoot }

& (Join-Path $PSScriptRoot "new-ai-worktree.ps1") @arguments
