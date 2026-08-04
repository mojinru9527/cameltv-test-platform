# Batch 77 — PM Plan（C76-1 存量 P0 修复）

> **PM (🟨)** | Date: 2026-08-04

## 规格摘要

**原始需求**: PRD §1 三个 P0/P1 项；非目标 §3（剩余 HARD 移交 C77-1）。
**目标时间**: 单日批次，5 个 Slice。

## 开发任务

### [ ] Task 1: R.err 补定义 + 单测
**描述**: `schemas/common.py` R 类补 `err()` classmethod；新建 `tests/test_r_schema.py` 3 条单测。
**验收标准**: - `err(code,msg)` 返回 `{code,msg,data:None}`；- 单测覆盖默认值与自定义值；- 与 R.ok 同构。
**涉及文件**: `test-platform-v2/backend/app/schemas/common.py`、`test-platform-v2/backend/tests/test_r_schema.py`
**参考**: PRD §4 US-1；Batch 37 review P0-01

### [ ] Task 2: seed.py 密码 print → logger
**描述**: 补 logging，5 处 print 改 logger.info，密码行不输出明文。
**验收标准**: - stdout 无明文密码；- scan 复扫 seed.py 0 HARD。
**涉及文件**: `test-platform-v2/backend/app/seed.py`

### [ ] Task 3: 6 处高危静默吞异常加日志
**描述**: open_api 3 处 logger.exception；api_task_worker 2 处 logger.warning；playwright_executor 1 处 logger.warning。
**验收标准**: - 6 处均有日志语句；- scan 复扫 0 HARD。
**涉及文件**: open_api.py / api_task_worker.py / playwright_executor.py

### [ ] Task 4: scan 工具"注释吞异常降级 WARN"
**描述**: `scan-common-bugs.ps1` 对带 `#` 注释的 except-pass 降级为 WARN；SelfTest 保持 PASS。
**验收标准**: - 自测过；- 真实仓库 HARD 下降且 R.err 清零。
**涉及文件**: `scripts/git/scan-common-bugs.ps1`

### [ ] Task 5: QA + Leader
**描述**: ruff F821、scan 复扫、audit-cconditions、本地 pytest 阻塞记录（CI 全量兜底）；Leader 出判决。
**验收标准**: QA 报告含命令/退出码；C76-1 关闭证据；C77-1 登记。

## 质量要求

- [x] ruff F821 全绿（含新测试文件）
- [ ] 涉及模块 pytest：本地阻塞（Python 环境损坏），由 CI 后端全量回归执行并记录
- [ ] scan HARD 显著下降、R.err 清零
- [ ] 无调试遗留、无密钥
