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

# (batch-190) DeepSeek Harness Agent Team（模式②船长）入口：与 start-agent-team-task.ps1 同构，
# 固定 executor=DeepSeek_Harness、workflow=agent-team。使用前提：用户在聊天中已明确
# 本任务由 DeepSeek Harness 执行（三选：Claude Code / Codex / DeepSeek Harness）。
$ErrorActionPreference = "Stop"
$arguments = @{
    Executor = "DeepSeek_Harness"
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
