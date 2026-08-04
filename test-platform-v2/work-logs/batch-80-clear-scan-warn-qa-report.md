# Batch 80 — QA 报告（C79-1 WARN 高价值项）

> **QA (🔍)** | Date: 2026-08-04 | Verdict: **PASS**

## 测试总览

| 条件数 | 通过 | 失败 | 阻塞 |
|-------|------|------|------|
| 12 | 12 | 0 | 0 |

## 可执行门禁（命令、退出码与日志摘要）

**CI 分类**：变更域 = `test-platform-v2/backend/**` + `scripts/git/` + `.claude/skills/` → 后端 required；本地全量 pytest 已执行（C78-1）。

| 检查项 | 命令 | 退出码 | 结果 |
|--------|------|:------:|------|
| ruff F821（cipher + 测试） | `ruff check ... --select F821` | 0 | ✅ |
| scan 复扫 | `scan-common-bugs.ps1 -RepositoryPath <wt>` | 2 | ✅ HARD=0，WARN 231→230（cameltv-dev-key 清零） |
| scan SelfTest | `-SelfTest` | 0 | ✅ PASS |
| cipher 单测 | `pytest tests/test_cipher.py` | 0 | ✅ 4 passed |
| 污染复验 | `pytest tests/test_cipher.py tests/test_wiki_sync_availability.py` | 0 | ✅ 9 passed（无状态污染） |
| 本地全量 pytest | `.venv python -m pytest tests -q` | 0 | ✅ **1027 passed** / 3 skipped |
| C 条件门禁 | `audit-cconditions.ps1 -RequireLatestBatch` | 0 | ✅ |

## 逐条件验证（PRD §2 成功指标）

### M1: cameltv-dev-key 清零
✅ cipher.py 回退密钥移除，改用 effective_secret_key；scan 复扫 0 命中；回归测试断言源码无该字符串。

### M2: cipher 单测
✅ 4 条：显式密钥 roundtrip / 开发自动生成 roundtrip / 生产缺失报 RuntimeError / 无硬编码回退。

### M3: 404 双约定
✅ bug-guard 新增铁律（判别表）；scan 规则消息改为双约定语义并同行跳过 envelope 断言。

### M4: scan HARD
✅ 0（WARN 230，均为已分类豁免或复核项）。

### M5: 本地全量 pytest
✅ 1027 passed（较上批 +4 cipher 单测）。

## 缺陷列表

| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| D1 | P1（本批返工） | 首轮 cipher 测试直接改全局 settings 单例，污染后续测试（146 ERROR） | 隔离实例注入后全量 1027 passed | Closed |
| D2 | P3（存量） | 41 处 HTTP 404 测试断言经核查均为隔离/守卫正确契约 | bug-guard 双约定登记 | 豁免（文档化） |

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 4h / 实际 3h | 0/1/0/1 | 1 | 测试污染 | 测试配置类单例一律注入隔离实例；全量回归在提交前必跑 |

**技能使用**: `cameltv-agent-team`（完整批次）；`cameltv-bug-guard`（404 双约定）；`scan-common-bugs.ps1`（回归）。

## 发布建议

状态: **READY**   必修复: 0   建议修复: 0（其余 WARN 已分类豁免，C80-1 跟踪）
