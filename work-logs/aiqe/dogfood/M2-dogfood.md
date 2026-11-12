# M2 Dogfood 证据

- 日期：2026-11-12 20:31:14
- 命令：python -m pytest tests\test_aiqe_workflow_validator.py tests\test_aiqe_dag_scheduler.py tests\test_aiqe_run_context.py tests\test_aiqe_http_driver.py tests\test_aiqe_playwright_driver.py tests\test_aiqe_db_readonly_driver.py tests\test_aiqe_capability_registry.py tests\test_aiqe_workflow_service.py tests\test_aiqe_resource_lock.py -q
- 结果：**PASS** — ======================= 75 passed, 2 warnings in 2.41s ========================
- 说明：本地 SQLite + fake/契约执行器；真实隔离环境 E2E 见 	ests/e2e/aiqe/（需 AIQE_E2E_BASE_URL）。
