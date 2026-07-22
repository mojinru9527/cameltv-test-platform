[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Assert-True([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw "ASSERTION FAILED: $Message" }
}

$tempBase = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
$testRoot = Join-Path $tempBase ("cameltv-worktree-test-" + [guid]::NewGuid().ToString("N"))
$testRootFull = [System.IO.Path]::GetFullPath($testRoot)
if (-not $testRootFull.StartsWith($tempBase, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Temporary test root escaped the system temp directory."
}

try {
    $remote = Join-Path $testRootFull "remote.git"
    $seed = Join-Path $testRootFull "seed"
    $control = Join-Path $testRootFull "control"
    $worktrees = Join-Path $testRootFull "worktrees"
    New-Item -ItemType Directory -Path $testRootFull -Force | Out-Null
    & git init --bare --initial-branch=main $remote | Out-Null
    & git init --initial-branch=main $seed | Out-Null
    Set-Content -Encoding UTF8 -LiteralPath (Join-Path $seed "README.md") -Value "test"
    Set-Content -Encoding UTF8 -LiteralPath (Join-Path $seed ".gitignore") -Value @(".ai-worktree.json", ".env", ".env.*")
    & git -C $seed add -- README.md .gitignore
    & git -C $seed -c user.name=test -c user.email=test@example.com commit -m "initial" | Out-Null
    & git -C $seed remote add origin $remote
    & git -C $seed push -u origin main | Out-Null
    & git clone $remote $control | Out-Null

    $verify = Join-Path $PSScriptRoot "verify-ai-worktree.ps1"
    $creator = Join-Path $PSScriptRoot "new-ai-worktree.ps1"
    $installer = Join-Path $PSScriptRoot "install-git-guardrails.ps1"
    $claudeStarter = Join-Path $PSScriptRoot "start-claude-task.ps1"
    $codexStarter = Join-Path $PSScriptRoot "start-codex-task.ps1"
    $agentTeamStarter = Join-Path $PSScriptRoot "start-agent-team-task.ps1"

    & $installer -RepositoryPath $control -GitHubLogin test-owner -GitHubEmail test-owner@example.com | Out-Null
    Assert-True ((& git -C $control config --local core.autocrlf) -eq "false") "installer must disable core.autocrlf"

    $mainRejected = $false
    try { & $verify -RepositoryPath $control -RequireClean | Out-Null } catch { $mainRejected = $true }
    Assert-True $mainRejected "verify script must reject protected main"

    $humanAgentTeamRejected = $false
    try { & $creator -Executor human -Workflow agent-team -Kind feature -Task invalid-human-team -Scope governance -FrontendPort 55171 -BackendPort 57998 -RepositoryPath $control -DestinationRoot $worktrees | Out-Null } catch { $humanAgentTeamRejected = $true }
    Assert-True $humanAgentTeamRejected "Agent Team workflow must reject human as executor"
    Assert-True (-not (Test-Path -LiteralPath (Join-Path $worktrees "human-invalid-human-team"))) "invalid workflow/executor must not create a worktree"

    Assert-True (Test-Path -LiteralPath $claudeStarter) "Claude fixed-executor entry must exist"
    $createdOutput = @(& $claudeStarter -Kind feature -Task test-isolation -Scope frontend -FrontendPort 55173 -BackendPort 58000 -RepositoryPath $control -DestinationRoot $worktrees)
    $created = $createdOutput[-1]
    $taskPath = Join-Path $worktrees "claude-test-isolation"
    Assert-True (Test-Path -LiteralPath (Join-Path $taskPath ".ai-worktree.json")) "metadata must be created"
    Assert-True ((Get-Content -Raw -LiteralPath (Join-Path $taskPath "test-platform-v2/frontend/.env.local")) -match 'VITE_DEV_PORT=55173') "frontend port env must be isolated"
    Assert-True ((Get-Content -Raw -LiteralPath (Join-Path $taskPath "test-platform-v2/backend/.env")) -match 'platform-test-isolation.db') "SQLite env must be isolated"
    Assert-True (@(& git -C $taskPath status --porcelain).Count -eq 0) "metadata must remain ignored"
    Assert-True ($created.Branch -eq "feature/test-isolation") "creator must return the task branch"
    Assert-True ($created.Workflow -eq "direct") "Claude entry must fix workflow=direct"
    Assert-True ($created.Executor -eq "claude") "Claude entry must fix executor=claude"
    & $verify -RepositoryPath $taskPath -RequireMetadata -ExpectedWorkflow direct -ExpectedExecutor claude | Out-Null
    $executorMismatchRejected = $false
    try { & $verify -RepositoryPath $taskPath -RequireMetadata -ExpectedExecutor codex | Out-Null } catch { $executorMismatchRejected = $true }
    Assert-True $executorMismatchRejected "ExpectedExecutor mismatch must be rejected"
    $workflowMismatchRejected = $false
    try { & $verify -RepositoryPath $taskPath -RequireMetadata -ExpectedWorkflow agent-team | Out-Null } catch { $workflowMismatchRejected = $true }
    Assert-True $workflowMismatchRejected "ExpectedWorkflow mismatch must be rejected"

    Assert-True (Test-Path -LiteralPath $codexStarter) "Codex fixed-executor entry must exist"
    Assert-True (Test-Path -LiteralPath $agentTeamStarter) "Agent Team workflow entry must exist"
    $codexCreated = @(& $codexStarter -Kind fix -Task codex-isolation -Scope backend -FrontendPort 55174 -BackendPort 58001 -RepositoryPath $control -DestinationRoot $worktrees)[-1]
    $agentTeamCreated = @(& $agentTeamStarter -Executor codex -Kind feature -Task agent-team-isolation -Scope governance -FrontendPort 55175 -BackendPort 58002 -RepositoryPath $control -DestinationRoot $worktrees)[-1]
    Assert-True ($codexCreated.Workflow -eq "direct") "Codex entry must fix workflow=direct"
    Assert-True ($codexCreated.Executor -eq "codex") "Codex entry must fix executor=codex"
    Assert-True ($agentTeamCreated.Workflow -eq "agent-team") "Agent Team entry must fix workflow=agent-team"
    Assert-True ($agentTeamCreated.Executor -eq "codex") "Agent Team entry must preserve the selected executor"
    $agentTeamPath = Join-Path $worktrees "codex-agent-team-isolation"
    & $verify -RepositoryPath $agentTeamPath -RequireMetadata -ExpectedWorkflow agent-team -ExpectedExecutor codex | Out-Null
    $claudeAgentTeamCreated = @(& $agentTeamStarter -Executor claude -Kind feature -Task agent-team-claude -Scope governance -FrontendPort 55176 -BackendPort 58003 -RepositoryPath $control -DestinationRoot $worktrees)[-1]
    Assert-True ($claudeAgentTeamCreated.Workflow -eq "agent-team") "Claude-hosted Agent Team must preserve workflow=agent-team"
    Assert-True ($claudeAgentTeamCreated.Executor -eq "claude") "Claude-hosted Agent Team must preserve executor=claude"

    & $creator -Owner codex -Kind feature -Task legacy-isolation -Scope governance -FrontendPort 55177 -BackendPort 58004 -RepositoryPath $control -DestinationRoot $worktrees | Out-Null
    $legacyPath = Join-Path $worktrees "codex-legacy-isolation"
    $legacyMetadataPath = Join-Path $legacyPath ".ai-worktree.json"
    $legacyMetadata = [ordered]@{
        owner = "codex"
        task = "legacy-isolation"
        branch = "feature/legacy-isolation"
        base = "origin/main"
        created_at = (Get-Date).ToString("o")
        scope = @("governance")
        ports = [ordered]@{ frontend = 55177; backend = 58004 }
    }
    $legacyMetadata | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 -LiteralPath $legacyMetadataPath
    & $verify -RepositoryPath $legacyPath -RequireMetadata -ExpectedWorkflow direct -ExpectedExecutor codex | Out-Null

    $legacyAgentTeamPath = Join-Path $worktrees "agent-team-legacy-agent-team"
    & git -C $control worktree add -b feature/legacy-agent-team $legacyAgentTeamPath origin/main | Out-Null
    $legacyAgentTeamMetadata = [ordered]@{
        owner = "agent-team"
        task = "legacy-agent-team"
        branch = "feature/legacy-agent-team"
        base = "origin/main"
        created_at = (Get-Date).ToString("o")
        scope = @("governance")
        ports = [ordered]@{ frontend = 55178; backend = 58005 }
    }
    $legacyAgentTeamMetadata | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $legacyAgentTeamPath ".ai-worktree.json")
    & $verify -RepositoryPath $legacyAgentTeamPath -RequireMetadata -ExpectedWorkflow agent-team | Out-Null
    $unknownLegacyExecutorRejected = $false
    try { & $verify -RepositoryPath $legacyAgentTeamPath -RequireMetadata -ExpectedExecutor codex | Out-Null } catch { $unknownLegacyExecutorRejected = $true }
    Assert-True $unknownLegacyExecutorRejected "Legacy owner=agent-team must not be guessed as codex"

    $duplicateRejected = $false
    try { & $creator -Owner codex -Kind feature -Task test-isolation -Scope backend -FrontendPort 55179 -BackendPort 58006 -RepositoryPath $control -DestinationRoot $worktrees | Out-Null } catch { $duplicateRejected = $true }
    Assert-True $duplicateRejected "duplicate branch must be rejected"

    & git -C $control config core.hooksPath ([System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\..\.githooks")))
    Set-Content -Encoding UTF8 -LiteralPath (Join-Path $taskPath "feature.txt") -Value "feature"
    & git -C $taskPath add -- feature.txt
    & git -C $taskPath -c user.name=test -c user.email=test@example.com commit -m "feature" | Out-Null
    & git -C $taskPath push -u origin feature/test-isolation | Out-Null
    Assert-True ($LASTEXITCODE -eq 0) "task branch push must succeed"

    $metadataPath = Join-Path $taskPath ".ai-worktree.json"
    $metadata = Get-Content -Raw -LiteralPath $metadataPath | ConvertFrom-Json
    $metadata.branch = "feature/wrong-task"
    $metadata | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 -LiteralPath $metadataPath
    Set-Content -Encoding UTF8 -LiteralPath (Join-Path $taskPath "invalid-metadata.txt") -Value "blocked"
    & git -C $taskPath add -- invalid-metadata.txt
    & git -C $taskPath -c user.name=test -c user.email=test@example.com commit -m "invalid metadata" | Out-Null
    & git -C $taskPath push origin feature/test-isolation 2>$null
    Assert-True ($LASTEXITCODE -ne 0) "task push with mismatched metadata must be blocked"
    $metadata.branch = "feature/test-isolation"
    $metadata | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 -LiteralPath $metadataPath
    & git -C $taskPath push origin feature/test-isolation | Out-Null
    Assert-True ($LASTEXITCODE -eq 0) "task push must succeed after metadata is restored"

    & git -C $control push origin --delete feature/test-isolation | Out-Null
    Assert-True ($LASTEXITCODE -eq 0) "merged task branch deletion must not require worktree metadata"

    Set-Content -Encoding UTF8 -LiteralPath (Join-Path $control "main.txt") -Value "blocked"
    & git -C $control add -- main.txt
    & git -C $control -c user.name=test -c user.email=test@example.com commit -m "blocked main" | Out-Null
    & git -C $control push origin main 2>$null
    Assert-True ($LASTEXITCODE -ne 0) "direct main push must be blocked by pre-push hook"

    Write-Host "PASS: workflow/executor entry, invalid pair rejection, legacy metadata, task push/delete, and protected push guard."
}
finally {
    if (Test-Path -LiteralPath $testRootFull) {
        $resolved = [System.IO.Path]::GetFullPath($testRootFull)
        if (-not $resolved.StartsWith($tempBase, [System.StringComparison]::OrdinalIgnoreCase) -or $resolved -eq $tempBase) {
            throw "Refusing to remove unsafe test path: $resolved"
        }
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}
