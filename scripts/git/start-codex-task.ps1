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

$ErrorActionPreference = "Stop"
$arguments = @{
    Owner = "codex"
    Kind = $Kind
    Task = $Task
    Scope = $Scope
    FrontendPort = $FrontendPort
    BackendPort = $BackendPort
    RepositoryPath = $RepositoryPath
}
if ($DestinationRoot) { $arguments.DestinationRoot = $DestinationRoot }

& (Join-Path $PSScriptRoot "new-ai-worktree.ps1") @arguments
