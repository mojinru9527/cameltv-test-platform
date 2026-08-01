[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Assert-True([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw "ASSERTION FAILED: $Message" }
}

function Assert-Equal($Expected, $Actual, [string]$Message) {
    if ($Expected -ne $Actual) {
        throw "ASSERTION FAILED: $Message (expected=$Expected, actual=$Actual)"
    }
}

function Assert-Throws([scriptblock]$Action, [string]$Pattern, [string]$Message) {
    $thrown = $false
    try { & $Action } catch {
        $thrown = $true
        if ($_.Exception.Message -notmatch $Pattern) {
            throw "ASSERTION FAILED: $Message (unexpected error: $($_.Exception.Message))"
        }
    }
    if (-not $thrown) { throw "ASSERTION FAILED: $Message (no error was thrown)" }
}

$scriptUnderTest = Join-Path $PSScriptRoot "start-platform-environment.ps1"
. $scriptUnderTest -LibraryOnly

$expectedBackend = 'F:\CamelTv-worktrees\current-task\test-platform-v2\backend'
Assert-True `
    (Test-ProcessBelongsToPath -CommandLine "python -m uvicorn --app-dir `"$expectedBackend`"" -ExpectedPath $expectedBackend) `
    "an exact app-dir must belong to the worktree"
Assert-True `
    (-not (Test-ProcessBelongsToPath -CommandLine "python -m uvicorn --app-dir `"$expectedBackend-foreign`"" -ExpectedPath $expectedBackend)) `
    "a sibling worktree sharing the path prefix must be rejected"

$script:listenerReadCount = 0
function Get-ListeningProcesses {
    param([int]$Port)
    $script:listenerReadCount++
    if ($script:listenerReadCount -eq 1) { return @() }
    return @([pscustomobject]@{
        ProcessId = 4242
        CommandLine = "python -m uvicorn --app-dir `"$expectedBackend`" --port $Port"
    })
}

$resolvedPid = Resolve-LocalListener `
    -Port 58026 `
    -ExpectedPath $expectedBackend `
    -Label "backend" `
    -StartProcess { [pscustomobject]@{ Id = 1111 } }
Assert-Equal 4242 $resolvedPid "the listener PID, not the venv forwarding PID, must be returned"

$manifest = [pscustomobject]@{
    pids = [pscustomobject]@{ backend = 1111; frontend = 3333 }
}
$listeners = @([pscustomobject]@{
    ProcessId = 4242
    CommandLine = "python -m uvicorn --app-dir `"$expectedBackend`" --port 58026"
})
$verifiedPid = Set-VerifiedManifestListenerPid `
    -Manifest $manifest `
    -Name "backend" `
    -Listeners $listeners `
    -Port 58026 `
    -ExpectedPath $expectedBackend `
    -Label "Backend"
Assert-Equal 4242 $verifiedPid "status must resolve the actual listener PID"
Assert-Equal 4242 $manifest.pids.backend "status must reconcile the in-memory manifest PID"

$foreignManifest = [pscustomobject]@{
    pids = [pscustomobject]@{ backend = 1111; frontend = 3333 }
}
$foreignListeners = @([pscustomobject]@{
    ProcessId = 9999
    CommandLine = 'python -m uvicorn --app-dir "F:\CamelTv-worktrees\another-task\test-platform-v2\backend" --port 58026'
})
Assert-Throws `
    { Set-VerifiedManifestListenerPid -Manifest $foreignManifest -Name "backend" -Listeners $foreignListeners -Port 58026 -ExpectedPath $expectedBackend -Label "Backend" } `
    "outside this worktree" `
    "manifest reconciliation must reject a foreign listener"
Assert-Equal 1111 $foreignManifest.pids.backend "a rejected foreign listener must not alter the manifest"

Write-Host "PASS: runtime listener PID forwarding, manifest reconciliation, and worktree ownership guards."
