# M8 Dogfood 证据

- 日期：2026-11-12 20:31:39
- 命令：python -m pytest tests\test_aiqe_device_broker.py tests\test_aiqe_miniapp_adapter.py tests\test_aiqe_desktop_iot_drivers.py tests\test_aiqe_domain_packs.py -q
- 结果：**PASS** — ============================= 24 passed in 0.29s ==============================
- 说明：本地 SQLite + fake/契约执行器；真实隔离环境 E2E 见 	ests/e2e/aiqe/（需 AIQE_E2E_BASE_URL）。
