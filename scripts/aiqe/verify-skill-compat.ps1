<#
.SYNOPSIS
  AIQE Skill 跨 Agent 兼容性校验（TA-038）。
  校验 6 个 SKILL.md 契约 + 三客户端清单 + 文档存在。
#>
[CmdletBinding()]
param(
    [string]$RepositoryPath = ".",
    [switch]$SelfTest
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path -LiteralPath $RepositoryPath).Path
$agents = @(
    "a0-requirement", "a2-test-design", "a3-workflow-planner",
    "a4-failure-triage", "a5-change-impact", "a6-learning-curator"
)
$clients = @("claude-code", "codex", "cursor")
$errors = [System.Collections.Generic.List[string]]::new()

$manifestPath = Join-Path $root "scripts/aiqe/skill-clients.json"
if (-not (Test-Path -LiteralPath $manifestPath)) {
    $errors.Add("缺少脚本/客户端清单 scripts/aiqe/skill-clients.json")
}
else {
    $manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
    foreach ($client in $clients) {
        if ($manifest.clients.id -notcontains $client) {
            $errors.Add("清单缺少客户端: $client")
        }
    }
}

foreach ($agent in $agents) {
    $path = Join-Path $root ".claude/skills/$agent/SKILL.md"
    if (-not (Test-Path -LiteralPath $path)) {
        $errors.Add("$agent : 缺少 SKILL.md")
        continue
    }
    $lines = @(Get-Content -LiteralPath $path)
    if ($lines.Count -lt 4 -or $lines[0].Trim() -ne "---") {
        $errors.Add("$agent : frontmatter 起始缺失")
        continue
    }
    $text = $lines -join "`n"
    if (-not $text.Contains("name: $agent")) { $errors.Add("$agent : name 不匹配") }
    if (-not $text.Contains("description:")) { $errors.Add("$agent : 缺 description") }
    foreach ($section in @("## 输入", "## 输出", "## 安全边界")) {
        if (-not $text.Contains($section)) { $errors.Add("$agent : 缺少 $section") }
    }
}

$doc = Join-Path $root "docs/aiqe/skills.md"
if (-not (Test-Path -LiteralPath $doc)) { $errors.Add("缺少 docs/aiqe/skills.md") }

if ($errors.Count -gt 0) {
    Write-Host "SKILL_COMPAT=FAIL ($($errors.Count) 处)"
    $errors | ForEach-Object { Write-Host "  - $_" }
    exit 1
}

Write-Host "SKILL_COMPAT=PASS clients=$($clients.Count) skills=$($agents.Count)"
exit 0
