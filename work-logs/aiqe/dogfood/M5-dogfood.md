# M5 Dogfood 证据

- 日期：2026-11-12 20:31:31
- 命令：python -m pytest tests\test_aiqe_change_impact_agent.py tests\test_aiqe_learning_curator.py tests\test_aiqe_quality_gate.py tests\test_aiqe_mcp_gateway.py tests\test_aiqe_mcp_server.py tests\test_aiqe_execution_profile.py tests\test_aiqe_interference_detectors.py tests\test_aiqe_failure_triage_agent.py tests\test_aiqe_noise_hint_agent.py -q
- 结果：**PASS** — ============================= 78 passed in 1.48s ==============================
- 说明：本地 SQLite + fake/契约执行器；真实隔离环境 E2E 见 	ests/e2e/aiqe/（需 AIQE_E2E_BASE_URL）。
