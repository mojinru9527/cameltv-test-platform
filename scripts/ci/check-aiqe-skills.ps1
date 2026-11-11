<#
.SYNOPSIS
  AIQE Agent Skills 校验（TA-032.5）：6 个 skill 必须存在且符合统一契约。
#>
[CmdletBinding()]
param(
    [string]$RepositoryPath = "."
)

$ErrorActionPreference = "Stop"
$agents = @(
    "a0-requirement",
    "a2-test-design",
    "a3-workflow-planner",
    "a4-failure-triage",
    "a5-change-impact",
    "a6-learning-curator"
)
$root = (Resolve-Path -LiteralPath $RepositoryPath).Path
$errors = [System.Collections.Generic.List[string]]::new()

foreach ($agent in $agents) {
    $path = Join-Path $root ".claude/skills/$agent/SKILL.md"
    if (-not (Test-Path -LiteralPath $path)) {
        $errors.Add("$agent : 缺少 SKILL.md")
        continue
    }
    $lines = @(Get-Content -LiteralPath $path)
    if ($lines.Count -lt 4 -or $lines[0].Trim() -ne "---") {
        $errors.Add("$agent : frontmatter 起始 --- 缺失")
        continue
    }
    $end = -1
    for ($i = 1; $i -lt $lines.Count; $i++) {
        if ($lines[$i].Trim() -eq "---") { $end = $i; break }
    }
    if ($end -lt 0) {
        $errors.Add("$agent : frontmatter 结束 --- 缺失")
        continue
    }
    $front = $lines[1..($end - 1)]
    $nameLine = $front | Where-Object { $_ -match '^name:\s*(.+)$' } | Select-Object -First 1
    if (-not $nameLine -or $nameLine.Trim() -ne "name: $agent") {
        $errors.Add("$agent : frontmatter name 缺失或不匹配")
    }
    $descLine = $front | Where-Object { $_ -match '^description:\s*\S' } | Select-Object -First 1
    if (-not $descLine) {
        $errors.Add("$agent : frontmatter description 为空")
    }
    $text = $lines -join "`n"
    foreach ($section in @("## 输入", "## 输出", "## 安全边界")) {
        if (-not $text.Contains($section)) {
            $errors.Add("$agent : 缺少章节 $section")
        }
    }
}

if ($errors.Count -gt 0) {
    Write-Host "AIQE_SKILLS=FAIL ($($errors.Count) 处)"
    $errors | ForEach-Object { Write-Host "  - $_" }
    exit 1
}

Write-Host "AIQE_SKILLS=PASS（$($agents.Count) 个 skill）"
exit 0
