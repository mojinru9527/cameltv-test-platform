<#
.SYNOPSIS
  Oracle 来源守卫（TA-020.3）：assertion 缺 `oracle_layer`（或非法值）一律拒绝。

.DESCRIPTION
  扫描 PR 变更的 JSON/Markdown 文件（含 Markdown 内 ```json 代码块），递归查找
  `assertions` 数组，要求每个元素都带：
      "oracle_layer": "REQ" | "STD" | "PATTERN"
  只检查变更文件（-Files / -BaseRef），避免历史数据一次性爆红。

.EXAMPLE
  pwsh scripts/ci/check-oracle-layer.ps1 -RepositoryPath . -BaseRef origin/main

.EXAMPLE
  pwsh scripts/ci/check-oracle-layer.ps1 -SelfTest
#>
[CmdletBinding()]
param(
    [string]$RepositoryPath = ".",
    [string]$BaseRef = "origin/main",
    [string[]]$Files = @(),
    [switch]$All,
    [switch]$SelfTest
)

$ErrorActionPreference = "Stop"
$script:AllowedLayers = @("REQ", "STD", "PATTERN")
$script:Violations = [System.Collections.Generic.List[string]]::new()

function Add-Violation([string]$message) {
    $script:Violations.Add($message)
}

function Get-JsonDocuments {
    param([string]$Path, [string]$Text)
    $docs = @()
    if ($Path -match '\.json$') {
        try {
            $docs += ,($Text | ConvertFrom-Json -AsHashtable)
        }
        catch {
            Add-Violation "$Path : JSON 解析失败（$($_.Exception.Message)）"
        }
        return $docs
    }
    if ($Path -match '\.(md|markdown)$') {
        $rx = [regex]'(?ms)^```json\s*(.*?)^```'
        foreach ($match in $rx.Matches($Text)) {
            try {
                $docs += ,($match.Groups[1].Value | ConvertFrom-Json -AsHashtable)
            }
            catch {
                Add-Violation "$Path : Markdown JSON 代码块解析失败（$($_.Exception.Message)）"
            }
        }
    }
    return $docs
}

function Find-AssertionViolations {
    param($Node, [string]$Path, [string]$JsonPath)
    if ($null -eq $Node) { return }

    if ($Node -is [System.Collections.IDictionary]) {
        foreach ($key in @($Node.Keys)) {
            $value = $Node[$key]
            $childPath = if ($JsonPath) { "$JsonPath.$key" } else { [string]$key }
            if ($key -eq 'assertions' -and $value -is [System.Collections.IList]) {
                for ($i = 0; $i -lt $value.Count; $i++) {
                    $assertion = $value[$i]
                    if ($assertion -isnot [System.Collections.IDictionary]) {
                        Add-Violation "$Path : $childPath[$i] 不是对象"
                        continue
                    }
                    if (-not $assertion.Contains('oracle_layer')) {
                        Add-Violation "$Path : $childPath[$i] 缺少 oracle_layer"
                        continue
                    }
                    $layer = [string]$assertion['oracle_layer']
                    if ($script:AllowedLayers -notcontains $layer) {
                        Add-Violation "$Path : $childPath[$i] oracle_layer 非法（$layer）"
                    }
                }
            }
            Find-AssertionViolations -Node $value -Path $Path -JsonPath $childPath
        }
        return
    }

    if ($Node -is [System.Collections.IList]) {
        for ($i = 0; $i -lt $Node.Count; $i++) {
            Find-AssertionViolations -Node $Node[$i] -Path $Path -JsonPath "$JsonPath[$i]"
        }
    }
}

function Invoke-Scan {
    param([string[]]$Targets)
    foreach ($target in $Targets) {
        if ([string]::IsNullOrWhiteSpace($target)) { continue }
        if ($target -notmatch '\.(json|md|markdown)$') { continue }
        if (-not (Test-Path -LiteralPath $target)) { continue }
        $text = Get-Content -Raw -LiteralPath $target
        if ([string]::IsNullOrWhiteSpace($text)) { continue }
        $docs = Get-JsonDocuments -Path $target -Text $text
        foreach ($doc in $docs) {
            if ($null -eq $doc) { continue }
            Find-AssertionViolations -Node $doc -Path $target -JsonPath ''
        }
    }
}

if ($SelfTest) {
    $temp = Join-Path ([System.IO.Path]::GetTempPath()) ("oracle-guard-" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $temp | Out-Null
    try {
        $good = Join-Path $temp "good.json"
        $bad = Join-Path $temp "bad.json"
        $bogus = Join-Path $temp "bogus.json"
        $md = Join-Path $temp "good.md"
        @'
{"nodes":[{"key":"a","assertions":[{"key":"ok","oracle_layer":"REQ","expected":1}]}]}
'@ | Set-Content -LiteralPath $good -Encoding utf8
        @'
{"nodes":[{"key":"a","assertions":[{"key":"missing","expected":1}]}]}
'@ | Set-Content -LiteralPath $bad -Encoding utf8
        @'
{"nodes":[{"key":"a","assertions":[{"key":"bogus","oracle_layer":"GUESS","expected":1}]}]}
'@ | Set-Content -LiteralPath $bogus -Encoding utf8
        @'
```json
{"nodes":[{"key":"a","assertions":[{"key":"md","oracle_layer":"PATTERN"}]}]}
```
'@ | Set-Content -LiteralPath $md -Encoding utf8

        Invoke-Scan -Targets @($good, $md)
        if ($script:Violations.Count -ne 0) {
            Write-Host "SELFTEST=FAIL good docs flagged: $($script:Violations -join '; ')"
            exit 1
        }
        Invoke-Scan -Targets @($bad, $bogus)
        if ($script:Violations.Count -lt 2) {
            Write-Host "SELFTEST=FAIL expected 2 violations, got $($script:Violations.Count)"
            exit 1
        }
        Write-Host "SELFTEST=PASS"
        exit 0
    }
    finally {
        Remove-Item -Recurse -Force -LiteralPath $temp -ErrorAction SilentlyContinue
    }
}

$resolvedRepo = (Resolve-Path -LiteralPath $RepositoryPath).Path
$targets = @()
if ($Files.Count -gt 0) {
    $targets = $Files | ForEach-Object {
        if ([System.IO.Path]::IsPathRooted($_)) { $_ } else { Join-Path $resolvedRepo $_ }
    }
}
elseif ($All) {
    $targets = Get-ChildItem -LiteralPath $resolvedRepo -Recurse -File -Include *.json, *.md, *.markdown |
        Where-Object { $_.FullName -notmatch '[\\/](\.git|node_modules|\.venv)[\\/]' } |
        ForEach-Object { $_.FullName }
}
else {
    $diff = & git -C $resolvedRepo diff --name-only --diff-filter=AM "$BaseRef...HEAD" 2>$null
    if ($LASTEXITCODE -ne 0) {
        $diff = & git -C $resolvedRepo diff --name-only --diff-filter=AM "HEAD~1" 2>$null
    }
    $targets = @($diff) | Where-Object { $_ -match '\.(json|md|markdown)$' } | ForEach-Object {
        Join-Path $resolvedRepo $_
    }
}

Invoke-Scan -Targets $targets

if ($script:Violations.Count -gt 0) {
    Write-Host "ORACLE_LAYER_GUARD=FAIL ($($script:Violations.Count) 处)"
    $script:Violations | ForEach-Object { Write-Host "  - $_" }
    Write-Host "修复：每条 assertion 增加 `"oracle_layer`": `"REQ`" | `"STD`" | `"PATTERN`"（13 号 §9.4）。"
    exit 1
}

Write-Host "ORACLE_LAYER_GUARD=PASS（扫描 $($targets.Count) 个文件）"
exit 0
