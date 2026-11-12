<#
.SYNOPSIS
  AIQE Dogfood Ratchet 执行器（P0）。
#>
[CmdletBinding()]
param(
    [string]$RepositoryPath = ".",
    [string]$OutputDir = "work-logs/aiqe/dogfood"
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path -LiteralPath $RepositoryPath).Path
$backend = Join-Path $root "test-platform-v2/backend"
$out = Join-Path $root $OutputDir
New-Item -ItemType Directory -Path $out -Force | Out-Null
$env:ENVIRONMENT = "test"
$env:DATABASE_URL = "sqlite:///./data/dogfood.db"
if (-not $env:SECRET_KEY) { $env:SECRET_KEY = ("a" * 64) }

$groups = [ordered]@{
    "M1" = @("test_aiqe_run_models.py", "test_aiqe_run_state.py", "test_aiqe_run_api.py", "test_aiqe_event_service.py", "test_aiqe_artifact_service.py", "test_aiqe_artifact_minio.py")
    "M2" = @("test_aiqe_workflow_validator.py", "test_aiqe_dag_scheduler.py", "test_aiqe_run_context.py", "test_aiqe_http_driver.py", "test_aiqe_playwright_driver.py", "test_aiqe_db_readonly_driver.py", "test_aiqe_capability_registry.py", "test_aiqe_workflow_service.py", "test_aiqe_resource_lock.py")
    "M3" = @("test_aiqe_playwright_mcp_explorer.py", "test_aiqe_testerarmy_adapter.py", "test_aiqe_keploy_driver.py", "test_aiqe_requirement_agent.py", "test_aiqe_test_design_agent.py", "test_aiqe_workflow_planner_agent.py")
    "M4" = @("test_aiqe_triage_experiments.py", "test_aiqe_defect_draft.py", "test_aiqe_defect_regression.py", "test_aiqe_noise_rules.py")
    "M5" = @("test_aiqe_change_impact_agent.py", "test_aiqe_learning_curator.py", "test_aiqe_quality_gate.py", "test_aiqe_mcp_gateway.py", "test_aiqe_mcp_server.py", "test_aiqe_execution_profile.py", "test_aiqe_interference_detectors.py", "test_aiqe_failure_triage_agent.py", "test_aiqe_noise_hint_agent.py")
    "M6" = @("test_aiqe_sports_vertical.py", "test_aiqe_asset_map.py", "test_aiqe_hardening.py")
    "M8" = @("test_aiqe_device_broker.py", "test_aiqe_miniapp_adapter.py", "test_aiqe_desktop_iot_drivers.py", "test_aiqe_domain_packs.py")
    "P0" = @("test_aiqe_conditional_edges.py", "test_aiqe_p0_ops.py")
}

Set-Location $backend
$overall = 0
foreach ($key in $groups.Keys) {
    $files = $groups[$key] | ForEach-Object { Join-Path "tests" $_ }
    $output = & python -m pytest @files -q 2>&1
    $code = $LASTEXITCODE
    $summary = ($output | Select-String -Pattern 'passed|failed|error' | Select-Object -Last 1).Line
    if (-not $summary) { $summary = ($output | Select-Object -Last 1) }
    $status = if ($code -eq 0) { "PASS" } else { "FAIL" }
    if ($code -ne 0) { $overall = 1 }
    $md = @"
# $key Dogfood 证据

- 日期：$(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
- 命令：`python -m pytest $($files -join ' ') -q`
- 结果：**$status** — $summary
- 说明：本地 SQLite + fake/契约执行器；真实隔离环境 E2E 见 `tests/e2e/aiqe/`（需 AIQE_E2E_BASE_URL）。
"@
    $md | Set-Content -LiteralPath (Join-Path $out "$key-dogfood.md") -Encoding utf8
    Write-Host "$key : $status — $summary"
}

exit $overall
