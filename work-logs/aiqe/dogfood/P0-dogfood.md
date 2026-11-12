# P0 Dogfood 证据

- 日期：2026-11-12 20:31:44
- 命令：python -m pytest tests\test_aiqe_conditional_edges.py tests\test_aiqe_p0_ops.py -q
- 结果：**PASS** — ======================== 7 passed, 2 warnings in 0.76s ========================
- 说明：本地 SQLite + fake/契约执行器；真实隔离环境 E2E 见 	ests/e2e/aiqe/（需 AIQE_E2E_BASE_URL）。
