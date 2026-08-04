[CmdletBinding()]
param(
    [string]$RepositoryPath = (Get-Location).Path,
    [switch]$FailOnWarning,
    [switch]$SelfTest
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Get-GitRoot {
    param([string]$Path)
    $out = @(& git -C $Path rev-parse --show-toplevel 2>&1)
    if ($LASTEXITCODE -ne 0) { throw "Not a git repository: $Path" }
    return $out[0].Trim()
}

function Add-Hit {
    param(
        [System.Collections.Generic.List[object]]$Target,
        [string]$Severity,
        [string]$File,
        [string]$Line,
        [string]$Col,
        [string]$Snippet
    )
    $Target.Add([pscustomobject]@{
        Severity = $Severity
        File = $File
        Line = $Line
        Col = $Col
        Snippet = $Snippet
    })
}

function Get-LineCol {
    param([string]$Text, [int]$Index)
    $before = $Text.Substring(0, [Math]::Min($Index, $Text.Length))
    $line = ($before -split "`n").Count
    $lastNl = $before.LastIndexOf("`n")
    $col = if ($lastNl -ge 0) { $Index - $lastNl } else { $Index + 1 }
    return @($line, $col)
}

function Test-File {
    param(
        [System.Collections.Generic.List[object]]$Hard,
        [System.Collections.Generic.List[object]]$Warn,
        [string]$Path,
        [string]$Relative,
        [string]$Role   # backend-app | backend-tests | frontend-src
    )
    $text = [System.IO.File]::ReadAllText($Path)
    $patterns = @()
    if ($Role -eq "backend-app" -or $Role -eq "frontend-src" -or $Role -eq "backend-scripts") {
        # 调试遗留（Hard）
        if ($Role -eq "backend-app") {
            $patterns += @(
                @{ Name = "print 调试遗留"; Re = '\bprint\s*\('; Sev = "HARD" },
                @{ Name = "breakpoint 调试遗留"; Re = '\bbreakpoint\s*\(\s*\)'; Sev = "HARD" },
                @{ Name = "pdb 调试遗留"; Re = 'pdb\.set_trace\s*\('; Sev = "HARD" }
            )
        }
        elseif ($Role -eq "backend-scripts") {
            $patterns += @(
                @{ Name = "scripts print（运维脚本可接受，需复核）"; Re = '\bprint\s*\('; Sev = "WARN" }
            )
        }
        else {
            $patterns += @(
                @{ Name = "console.log 调试遗留"; Re = 'console\.log\s*\('; Sev = "HARD" },
                @{ Name = "debugger 调试遗留"; Re = '\bdebugger\b'; Sev = "HARD" }
            )
        }
        # 硬编码密钥 / 回退密钥（Warn）
        $patterns += @(
            @{ Name = "回退密钥 cameltv-dev-key"; Re = 'cameltv-dev-key'; Sev = "WARN" },
            @{ Name = "硬编码 SECRET_KEY"; Re = 'SECRET_KEY\s*=\s*["''][^"'']+["'']'; Sev = "WARN" },
            @{ Name = "硬编码 api_key/secret/token"; Re = '(?:api[_-]?key|secret|token)\s*=\s*["''][A-Za-z0-9_\-]{12,}["'']'; Sev = "WARN" }
        )
    }
    if ($Role -eq "backend-app" -or $Role -eq "backend-scripts") {
        # 静默吞异常（Hard）
        $patterns += @(
            @{ Name = "except: pass 静默吞异常"; Re = '(?m)^\s*except[^\n]*:[^\S\n]*\n[^\S\n]*pass\b'; Sev = "HARD" },
            @{ Name = "except: pass 同行"; Re = 'except[^\n]*:[ \t]+pass\b'; Sev = "HARD" }
        )
    }
    if ($Role -eq "backend-app") {
        # 密码进日志/print（Hard，Batch 37 P0-02）
        $patterns += @(
            @{ Name = "print/log 输出密码"; Re = '(?i)(?:print\s*\(|logger\.(?:info|debug|warning|error)\s*\().{0,60}(?:password|密码)'; Sev = "HARD" }
        )
    }
    if ($Role -eq "backend-tests") {
        # envelope 断言（Warn）：查不到应断言 body code==404 而非 HTTP 404
        $patterns += @(
            @{ Name = "envelope 断言 status_code==404"; Re = 'status_code\s*==\s*404'; Sev = "WARN" }
        )
    }
    foreach ($p in $patterns) {
        foreach ($m in [regex]::Matches($text, $p.Re)) {
            $lc = Get-LineCol -Text $text -Index $m.Index
            $snip = ($text.Substring($m.Index, [Math]::Min(70, $text.Length - $m.Index)) -replace "`r|`n", " ")
            $sev = $p.Sev
            if ($p.Name -like "except*") {
                # 带注释的 except-pass 视为有意为之，降级为 WARN 复核
                $lineEnd = $text.IndexOf("`n", $m.Index)
                if ($lineEnd -lt 0) { $lineEnd = $text.Length }
                $extended = $text.Substring($m.Index, $lineEnd - $m.Index)
                if ($extended -match '#') { $sev = "WARN" }
            }
            if ($sev -eq "WARN") {
                Add-Hit -Target $Warn -Severity WARN -File $Relative -Line $lc[0] -Col $lc[1] -Snippet "$($p.Name): $snip"
            }
            else {
                Add-Hit -Target $Hard -Severity HARD -File $Relative -Line $lc[0] -Col $lc[1] -Snippet "$($p.Name): $snip"
            }
        }
    }
}

function Invoke-Scan {
    param([string]$Root)
    $hard = New-Object System.Collections.Generic.List[object]
    $warn = New-Object System.Collections.Generic.List[object]

    $backendDir = Join-Path $Root "test-platform-v2/backend"
    $frontendDir = Join-Path $Root "test-platform-v2/frontend/src"
    $files = @()
    if (Test-Path -LiteralPath $backendDir) {
        $files += Get-ChildItem -LiteralPath $backendDir -Recurse -Filter *.py -File -ErrorAction SilentlyContinue
    }
    if (Test-Path -LiteralPath $frontendDir) {
        $files += Get-ChildItem -LiteralPath $frontendDir -Recurse -Include *.ts, *.tsx -File -ErrorAction SilentlyContinue
    }
    foreach ($f in ($files | Sort-Object FullName -Unique)) {
        $rel = $f.FullName.Substring($Root.Length).TrimStart('\', '/')
        $rel = $rel -replace '\\', '/'
        if ($rel -match 'node_modules|__pycache__|\.venv|\\venv\\|dist\\|\.next\\') { continue }
        $role = $null
        if ($rel -match '^test-platform-v2/backend/tests/') { $role = "backend-tests" }
        elseif ($rel -match '^test-platform-v2/backend/scripts/') { $role = "backend-scripts" }
        elseif ($rel -match '^test-platform-v2/backend/') { $role = "backend-app" }
        elseif ($rel -match '^test-platform-v2/frontend/src/') { $role = "frontend-src" }
        if (-not $role) { continue }
        Test-File -Hard $hard -Warn $warn -Path $f.FullName -Relative $rel -Role $role
    }

    # R.err 调用但无定义（Hard）
    $rUsageList = New-Object System.Collections.Generic.List[object]
    $defFound = $false
    foreach ($f in $files) {
        $rel = $f.FullName.Substring($Root.Length).TrimStart('\', '/')
        $rel = $rel -replace '\\', '/'
        if ($rel -notmatch '^test-platform-v2/backend/' -or $rel -match '__pycache__') { continue }
        $text = [System.IO.File]::ReadAllText($f.FullName)
        if ($text -match 'R\.err\s*\(') {
            foreach ($m in [regex]::Matches($text, 'R\.err\s*\(')) {
                $lc = Get-LineCol -Text $text -Index $m.Index
                $rUsageList.Add([pscustomobject]@{ File = $rel; Line = $lc[0]; Col = $lc[1] })
            }
        }
        if ($text -match 'def err\s*\(') { $defFound = $true }
    }
    if (-not $defFound) {
        foreach ($u in $rUsageList) {
            Add-Hit -Target $hard -Severity HARD -File $u.File -Line $u.Line -Col $u.Col -Snippet "R.err 调用但未发现 def err( 定义"
        }
    }

    return @{ Hard = $hard; Warn = $warn }
}

function Write-Report {
    param($Result)
    Write-Host "== scan-common-bugs =="
    Write-Host "HARD findings : $($Result.Hard.Count)"
    foreach ($h in $Result.Hard) { Write-Host ("  [HARD] {0}:{1}:{2} {3}" -f $h.File, $h.Line, $h.Col, $h.Snippet) }
    Write-Host "WARN findings : $($Result.Warn.Count)"
    foreach ($w in $Result.Warn) { Write-Verbose ("  [WARN] {0}:{1}:{2} {3}" -f $w.File, $w.Line, $w.Col, $w.Snippet) }
}

if ($SelfTest) {
    $fixture = Join-Path ([IO.Path]::GetTempPath()) ("scan-common-bugs-fixture-" + [guid]::NewGuid().ToString("N"))
    try {
        $bApp = Join-Path $fixture "test-platform-v2/backend/app"
        $bTests = Join-Path $fixture "test-platform-v2/backend/tests"
        $fSrc = Join-Path $fixture "test-platform-v2/frontend/src"
        New-Item -ItemType Directory -Force -Path $bApp, $bTests, $fSrc | Out-Null
        @"
class R:
    @classmethod
    def ok(cls):
        return cls(code=0, msg="ok", data=None)
"@ | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $bApp "r.py")
        @"
def handler():
    return R.err(code=404, msg="not found")
"@ | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $bApp "bad_r.py")
        @"
def debug():
    print("hello")
    breakpoint()
"@ | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $bApp "dbg.py")
        @"
export function dbg() {
  console.log("x");
  debugger;
}
"@ | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $fSrc "dbg.tsx")
        @"
def swallow():
    try:
        do_work()
    except Exception:
        pass
"@ | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $bApp "swallow.py")
        @"
SECRET_KEY = "cameltv-dev-key"
api_key = "0123456789abcdef"
"@ | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $bApp "secret.py")
        @"
def log_pwd(pwd):
    print(f"password={pwd}")
"@ | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $bApp "pwd.py")
        @"
def test_404():
    resp = client.get("/x")
    assert resp.status_code == 404
"@ | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $bTests "test_env.py")

        $res = Invoke-Scan -Root $fixture
        $ok = $true
        if ($res.Hard.Count -lt 4) { $ok = $false; Write-Host "SELF-TEST FAIL: expected >=4 HARD, got $($res.Hard.Count)" }
        if (($res.Hard | Where-Object { $_.Snippet -match 'R\.err' }).Count -lt 1) { $ok = $false; Write-Host "SELF-TEST FAIL: R.err rule not triggered" }
        if (($res.Hard | Where-Object { $_.Snippet -match 'except' }).Count -lt 1) { $ok = $false; Write-Host "SELF-TEST FAIL: swallow rule not triggered" }
        if ($res.Warn.Count -lt 2) { $ok = $false; Write-Host "SELF-TEST FAIL: expected >=2 WARN, got $($res.Warn.Count)" }
        if ($ok) {
            Write-Host "SELF-TEST PASS (HARD=$($res.Hard.Count) WARN=$($res.Warn.Count))"
            exit 0
        }
        Write-Report -Result $res
        exit 1
    }
    finally {
        if (Test-Path -LiteralPath $fixture) { Remove-Item -LiteralPath $fixture -Recurse -Force }
    }
}

$root = Get-GitRoot -Path $RepositoryPath
$result = Invoke-Scan -Root $root
Write-Report -Result $result
if ($result.Hard.Count -gt 0) { exit 1 }
if ($result.Warn.Count -gt 0) { if ($FailOnWarning) { exit 1 } else { exit 2 } }
exit 0
