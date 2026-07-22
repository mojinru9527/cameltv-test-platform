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

    $mainRejected = $false
    try { & $verify -RepositoryPath $control -RequireClean | Out-Null } catch { $mainRejected = $true }
    Assert-True $mainRejected "verify script must reject protected main"

    $createdOutput = @(& $creator -Owner claude -Kind feature -Task test-isolation -Scope frontend -FrontendPort 55173 -BackendPort 58000 -RepositoryPath $control -DestinationRoot $worktrees)
    $created = $createdOutput[-1]
    $taskPath = Join-Path $worktrees "claude-test-isolation"
    Assert-True (Test-Path -LiteralPath (Join-Path $taskPath ".ai-worktree.json")) "metadata must be created"
    Assert-True ((Get-Content -Raw -LiteralPath (Join-Path $taskPath "test-platform-v2/frontend/.env.local")) -match 'VITE_DEV_PORT=55173') "frontend port env must be isolated"
    Assert-True ((Get-Content -Raw -LiteralPath (Join-Path $taskPath "test-platform-v2/backend/.env")) -match 'platform-test-isolation.db') "SQLite env must be isolated"
    Assert-True (@(& git -C $taskPath status --porcelain).Count -eq 0) "metadata must remain ignored"
    Assert-True ($created.Branch -eq "feature/test-isolation") "creator must return the task branch"

    $duplicateRejected = $false
    try { & $creator -Owner codex -Kind feature -Task test-isolation -Scope backend -FrontendPort 55174 -BackendPort 58001 -RepositoryPath $control -DestinationRoot $worktrees | Out-Null } catch { $duplicateRejected = $true }
    Assert-True $duplicateRejected "duplicate branch must be rejected"

    & git -C $control config core.hooksPath ([System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\..\.githooks")))
    Set-Content -Encoding UTF8 -LiteralPath (Join-Path $taskPath "feature.txt") -Value "feature"
    & git -C $taskPath add -- feature.txt
    & git -C $taskPath -c user.name=test -c user.email=test@example.com commit -m "feature" | Out-Null
    & git -C $taskPath push -u origin feature/test-isolation | Out-Null
    Assert-True ($LASTEXITCODE -eq 0) "task branch push must succeed"

    Set-Content -Encoding UTF8 -LiteralPath (Join-Path $control "main.txt") -Value "blocked"
    & git -C $control add -- main.txt
    & git -C $control -c user.name=test -c user.email=test@example.com commit -m "blocked main" | Out-Null
    & git -C $control push origin main 2>$null
    Assert-True ($LASTEXITCODE -ne 0) "direct main push must be blocked by pre-push hook"

    Write-Host "PASS: AI worktree creation, metadata isolation, duplicate detection, and protected push guard."
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
