# Batch 80 — PM Plan（C79-1 WARN 高价值项）

> **PM (🟨)** | Date: 2026-08-04

## 规格摘要

**原始需求**: PRD §1 两个问题；非目标 §3。
**目标时间**: 单日批次，3 个 Slice。

## 开发任务

### [ ] Task 1: cipher.py 硬编码密钥移除 + 单测
**描述**: `_get_fernet()` 改用 `effective_secret_key`，缺失时 RuntimeError；新增 `tests/test_cipher.py` 4 条（注入隔离 Settings）。
**验收标准**: - 源码无 cameltv-dev-key；- 4 单测过；- 不污染全局 settings。
**涉及文件**: `app/core/cipher.py`、`tests/test_cipher.py`

### [ ] Task 2: 404 双约定规范 + scan 消息
**描述**: bug-guard 新增"404 双约定"铁律；scan 规则消息改为"HTTP 404 断言复核（隔离守卫正确/业务查不到应 200+code）"，同行已断言 envelope code 时跳过。
**验收标准**: - 文档含判别方法；- SelfTest PASS；- scan HARD 0。
**涉及文件**: `scripts/git/scan-common-bugs.ps1`、`.claude/skills/cameltv-bug-guard/SKILL.md`

### [ ] Task 3: QA + Leader
**描述**: ruff、py_compile、scan（HARD=0/WARN 230）、cipher 4 单测、本地全量 pytest、audit-cconditions；Leader 出判决。
**验收标准**: QA 报告含命令/退出码；C79-1 关闭证据；C80-1 登记。

## 质量要求

- [x] ruff F821 全绿
- [x] py_compile 全过
- [ ] scan HARD = 0
- [ ] 本地全量 pytest ≥1023 全绿
