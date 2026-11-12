# M3 Dogfood 证据

- 日期：2026-11-12 20:31:20
- 命令：python -m pytest tests\test_aiqe_playwright_mcp_explorer.py tests\test_aiqe_testerarmy_adapter.py tests\test_aiqe_keploy_driver.py tests\test_aiqe_requirement_agent.py tests\test_aiqe_test_design_agent.py tests\test_aiqe_workflow_planner_agent.py -q
- 结果：**PASS** — ======================= 44 passed, 2 warnings in 2.11s ========================
- 说明：本地 SQLite + fake/契约执行器；真实隔离环境 E2E 见 	ests/e2e/aiqe/（需 AIQE_E2E_BASE_URL）。
