[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet("claude", "codex")]
    [string]$Executor,

    [switch]$UserConfirmedCompletion,

    [string]$RepositoryPath = (Get-Location).Path
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if (-not $UserConfirmedCompletion) {
    throw "Agent Team must ask the user which executor actually performed the work and whether final audit/merge is authorized, then wait for the explicit reply before passing -UserConfirmedCompletion."
}

$verifyScript = Join-Path $PSScriptRoot "verify-ai-worktree.ps1"
$verifyOutput = @(& $verifyScript -RepositoryPath $RepositoryPath -RequireClean -RequireMetadata -ExpectedWorkflow agent-team -ExpectedExecutor $Executor)
$verification = $verifyOutput[-1]
if ([int]$verification.SchemaVersion -ne 3) {
    throw "Completion confirmation requires schema v3 Agent Team metadata."
}
if ($verification.StartConfirmation -ne "confirmed") {
    throw "A matching confirmed start identity is required before completion confirmation."
}

$metadataPath = Join-Path $verification.Root ".ai-worktree.json"
$metadata = Get-Content -Raw -LiteralPath $metadataPath | ConvertFrom-Json
$completion = $metadata.confirmations.completion
if ([string]$completion.status -eq "confirmed") {
    if ([string]$completion.executor -ne $Executor) {
        throw "Completion was already confirmed for executor '$($completion.executor)', not '$Executor'."
    }
}
else {
    $completion.status = "confirmed"
    $completion.executor = $Executor
    $completion.confirmed_at = (Get-Date).ToString("o")
    $metadata | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 -LiteralPath $metadataPath
}

$confirmedOutput = @(& $verifyScript -RepositoryPath $verification.Root -RequireClean -RequireMetadata -RequireCompletionConfirmation -ExpectedWorkflow agent-team -ExpectedExecutor $Executor)
$confirmedOutput[-1]
