# M4 Dogfood 证据

- 日期：2026-11-12 20:31:25
- 命令：python -m pytest tests\test_aiqe_triage_experiments.py tests\test_aiqe_defect_draft.py tests\test_aiqe_defect_regression.py tests\test_aiqe_noise_rules.py -q
- 结果：**PASS** — ============================= 30 passed in 1.96s ==============================
- 说明：本地 SQLite + fake/契约执行器；真实隔离环境 E2E 见 	ests/e2e/aiqe/（需 AIQE_E2E_BASE_URL）。
