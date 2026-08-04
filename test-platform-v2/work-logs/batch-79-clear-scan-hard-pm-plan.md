# Batch 79 — PM Plan（C77-1 存量 HARD 清零）

> **PM (🟨)** | Date: 2026-08-04

## 规格摘要

**原始需求**: PRD §1 三个问题；非目标 §3。
**目标时间**: 单日批次，4 个 Slice。

## 开发任务

### [ ] Task 1: scan 注释检测修复
**描述**: `scan-common-bugs.ps1` 多行 except-pass 注释检测改为从匹配结束位置找行尾。
**验收标准**: - auth.py/scheduler.py 等 5 处带注释吞异常降级 WARN；- SelfTest PASS。
**涉及文件**: `scripts/git/scan-common-bugs.ps1`

### [ ] Task 2: 15 处 print→logger
**描述**: main.py 4 处、ai_service.py 2 处、lanhu_provider.py 9 处；8 个无 logger 文件补 logging。
**验收标准**: - scan 复扫 0 print HARD；- ruff F821 全绿；- py_compile 通过。
**涉及文件**: main.py / ai_service.py / lanhu_provider.py

### [ ] Task 3: 26 处无注释吞异常
**描述**: api/v1 9 处、services 15 处加 logger.warning（带上下文）；backend/scripts 2 处加行内注释。
**验收标准**: - scan 复扫 0 吞异常 HARD；- ruff/compile 通过。
**涉及文件**: api/v1/*、services/*、scripts/migrate_*.py

### [ ] Task 4: QA + Leader
**描述**: ruff、py_compile、scan（HARD=0）、SelfTest、本地全量 pytest、audit-cconditions；Leader 出判决。
**验收标准**: QA 报告含命令/退出码；C77-1 关闭证据；C79-1 登记。

## 质量要求

- [x] ruff F821 全绿（22 个改动文件）
- [x] py_compile 全过
- [ ] scan HARD = 0
- [ ] 本地全量 pytest 通过（含子模块初始化后的 3 个 lanhu 契约测试）
