# M1 Dogfood 证据

- 日期：2026-11-12 20:31:07
- 命令：python -m pytest tests\test_aiqe_run_models.py tests\test_aiqe_run_state.py tests\test_aiqe_run_api.py tests\test_aiqe_event_service.py tests\test_aiqe_artifact_service.py tests\test_aiqe_artifact_minio.py -q
- 结果：**PASS** — ======================= 64 passed, 6 warnings in 7.01s ========================
- 说明：本地 SQLite + fake/契约执行器；真实隔离环境 E2E 见 	ests/e2e/aiqe/（需 AIQE_E2E_BASE_URL）。
