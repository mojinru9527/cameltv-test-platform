# Batch 77 — QA 报告（C76-1 存量 P0 修复）

> **QA (🔍)** | Date: 2026-08-04 | Verdict: **PASS（有条件：本地 pytest 环境阻塞，CI 全量兜底）**

## 测试总览

| 条件数 | 通过 | 失败 | 阻塞（环境） |
|-------|------|------|------|
| 12 | 10 | 1（CI 首轮抓出，已修复） | 1 |

## 可执行门禁（命令、退出码与日志摘要）

**CI 分类**：变更域 = `test-platform-v2/backend/**` → 触发后端 required + backend/PG 扩展检查；CI 将执行后端全量回归。

| 检查项 | 命令 | 退出码 | 结果 |
|--------|------|:------:|------|
| ruff F821（6 个改动文件 + 新测试） | `ruff check ... --select F821` | 0 | ✅ All checks passed |
| scan 自测 | `scan-common-bugs.ps1 -SelfTest` | 0 | ✅ PASS（HARD=8 WARN=4） |
| scan 真实仓库复扫 | `scan-common-bugs.ps1 -RepositoryPath <wt>` | 1 | ✅ 按设计阻断：HARD 67→49，**R.err 清零**；seed.py print 降级 WARN |
| R.err 单测 | pytest test_r_schema | 阻塞 | ⚠️ 本地 Python 3.12 基础被卸载，两个 venv 损坏，runner Python 异常；由 CI 后端全量回归执行 |
| C 条件门禁 | `audit-cconditions.ps1 -RequireLatestBatch` | 0 | ✅ 见 Leader 工件运行记录 |
| 变更范围 | `git diff --name-only` | 0 | ✅ 仅声明文件 |

## 逐条件验证（PRD §2 成功指标）

### M1: R.err 定义 + 单测
✅ `schemas/common.py` 新增 `err()`（默认 code=1/msg="error"，data=None）；新增 `tests/test_r_schema.py` 3 条（默认/自定义/与 ok 同构）。测试执行由 CI 兜底。

### M2: seed 密码（契约复核）
✅ 结论修正：`test_seed_credentials.py` 强制"生成凭据一次性显示"（admin 走 WARNING 日志、tester 走 stdout、二次运行零输出），属已测试的安全契约而非漏洞。**本批首轮方案（删除密码显示）被 CI 后端全量回归抓出（1 failed / 1025 passed），已回退**；scan 将 seed.py print 降级 WARN 复核。

### M3: 6 处静默吞异常
✅ open_api 3 处 logger.exception、api_task_worker 2 处 logger.warning、playwright_executor 1 处 logger.warning；scan 复扫 0 HARD。

### M4: scan HARD 下降
✅ 67→49（-18）：R.err 7 消除、6 处吞异常消除、seed 密码按契约保留（降级 WARN）；剩余 49 处（app 内 print、无注释 except-pass 等）登记 C77-1。

### M5: ruff F821
✅ 全绿。

## 缺陷列表

| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| D1 | P3（环境） | 本地 Python 3.12 被卸载，.venv/venv/runner Python 均不可用，pytest 无法本地执行 | pyvenv.cfg 指向缺失路径 | 阻塞登记，CI 兜底；C77-2 修复开发机 |
| D2 | P2（存量） | 剩余 49 处 HARD（app 内 print 迁移、无注释 except-pass 逐处处理） | scan 输出 | 移交 C77-1 |
| D3 | P1（本批返工） | 首轮 seed 方案删除密码显示，破坏 test_seed_credentials.py 一次性显示契约，CI 抓出 1 failed | CI 日志：`assert 'test-generated-tester-...' in ''` | Closed（已回退 + 扫描降级） |

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 5h / 实际 3.5h | 0/0/1/1（D2/D1）+ 返工 D3 | 1 | 契约冲突 | 动"看似有问题的输出"前先查既有测试契约；CI 首轮全绿再申请合入 |

**技能使用**: `cameltv-agent-team`（完整批次）；`cameltv-bug-guard`（规则来源）；`scan-common-bugs.ps1`（回归验证）。

## 发布建议

状态: **READY（需 CI 后端全量回归通过）**   必修复: 0   建议修复: D2 移交 C77-1
