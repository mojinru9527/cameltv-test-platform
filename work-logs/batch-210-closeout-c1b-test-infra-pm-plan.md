# Batch 210 — 收尾 — PM Plan
> **PM (🟨)** | Date: 2026-09-02

## 开发任务
### [x] S0: 工件
### [ ] S1: 测试基建修复
- notification_channel 夹具：test_batch148 导入注册通知模型。
- lanhu/deploy 测试：lanhu-mcp 子模块缺失时 pytest skip（原因明确），不再硬失败。
- 涉及: tests/test_batch148_p0_fixes.py、tests/test_lanhu_provider.py、tests/test_lanhu_login_hook.py、tests/test_deploy_compose_contract.py
### [ ] S2: C1b BrowserDriver adapter
- workflow/drivers 增加 `ensure_browser_runner()`：Playwright 可用时用 browser/driver.BrowserDriver 包装为 runner 并注册；不可用返回 False（仍 BLOCKED，原因含 capability）。
- 测试：mock BrowserDriver 可用/不可用两分支 + 现有分派保持。
- 涉及: workflow/drivers.py、browser/driver.py(仅 adapter import)
### [ ] S3: C2b 兜底物化
- materialize_bindings_for_plan：无 observation 匹配时，对 APPROVED oracle 若 plan 恰有一个 data/api 命令且 oracle 类型可推导 → 默认 binding_type（DB→DB_COLUMN 等）指向该命令。
- 测试：DB oracle 单命令自动 DB_COLUMN；多命令不臆测。
- 涉及: scenario/repository.py
### [ ] S4: QA + ADR-0025

## 质量要求
ruff F821 / 全量 pytest 0 失败（本批目标）/ 无迁移。
