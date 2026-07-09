# 🧹 Batch-B 仓库卫生债 — 巡检发现与处置

> 触发背景：推进「知识中心 M0+M1」PR（#15）时发现 develop 的**已提交(tracked)代码
> 在全新检出/CI 下根本无法导入**。深挖后确认这是一类**系统性仓库卫生债**，非单一特性引入。
> 本文档登记全部发现、已处置项与遗留 backlog。

**巡检日期**：2026-07-09  
**巡检人**：Dev 部门（配合 PR #15 收口）

---

## 已处置（本批 PR）

| # | 发现 | 严重度 | 处置 |
|---|------|:------:|------|
| B-1 | **CI 门禁未覆盖 develop**：`pr-check.yml` 仅 `on: pull_request: branches: [main, master]`，而团队日常主分支是 `develop` → 所有 develop PR 绕过后端 pytest + 前端 tsc 门禁，是 tracked 基线长期腐化的根因。 | **P1** | 新增 `.github/workflows/develop-import-smoke.yml`：develop PR/push 触发「全新检出后端可导入 + alembic 单头」最小冒烟（必绿）。 |
| B-2 | **tracked 基线不可导入**：`models/__init__` 与 `router` 引用从未提交的 `report_template`/`version_mission`，全新检出即 ImportError。 | **P1** | 已由 PR #15 的 hygiene 提交（`130858d`）补齐 6 模块 + 迁移 0007–0011 + `label.tsx`；develop 现 `import app.main` OK（已验）。 |
| B-3 | **本地 DB 可被误提交**：`.gitignore` 无 `*.db`，`test-platform-v2/app.db`、`cameltv.db` 处于可提交状态。 | **P2** | `.gitignore` 增补 `*.db`/`*.sqlite*` 及 `.verify-*/` 临时校验 worktree。 |

## 遗留 backlog（需团队/维护者，风险较高或跨部门）

| # | 发现 | 严重度 | 归属 | 说明 |
|---|------|:------:|------|------|
| B-4 | **alembic 从零升级失败**：`alembic upgrade head`（空库）在 `0002` 报 `duplicate column name: imported_func_count` —— `0001 initial_schema` 已含该列，`0002` 再 `add_column` 重复。`0005/0010` 亦向 `requirement_document` 追列，疑存同类漂移。dev 用 `auto_create_tables` 故长期潜伏；PG 生产靠增量迁移侥幸未触发。 | **P2** | 平台维护者 | 需将相关 `add_column` 改幂等（先 inspect 列存在性）或重整 `initial_schema` 与后续迁移的边界。**属既有历史，非本次引入**，且触多文件，宜单独 PR 谨慎回归。 |
| B-5 | **共享测试夹具漂移**：`conftest.py` 的 `client`/`auth_headers` 因登录响应体 shape 漂移 + `:memory:` 缺 StaticPool 而失败 → 完整 `pytest tests/` 在 develop 为红，故本批冒烟门禁未纳入完整套件。 | **P2** | 平台维护者 | 修复后即可把 `pr-check.yml` 的完整套件触发扩展到 develop，形成硬门禁。知识测试已自带独立夹具规避。 |
| B-6 | **大量在制工作悬空未提交**：develop 工作树 41 改动 + 218 未跟踪（`version_mission`/`report_template` 前端页、`swagger_doc_discovery`、`template_service`、数十 `scripts/`、`work-logs/` 等）。部分（apitest 二次验收本体，如 `ApiDebugPanel` 抽取）正由并行同事提交（见 `34099d9`）。 | **P2** | 各特性归属 Dev | 建议**按特性拆分聚焦 PR** 逐一入库；**避免与并行 apitest 提交冲突**——不动 `apitest.py`/`test_case.py`。此前延后的 apitest/test_case 入库 hook（知识 5 事件源余项）随其本体 PR 一并补入。 |

## 机制改进建议（防复发）

1. **门禁跟随主分支**：任何新增日常分支（如 develop）都应同步纳入 CI 触发，避免「门禁看错分支」。
2. **修复 B-4/B-5 后**，把 `pr-check.yml` 完整套件扩展到 develop，冒烟门禁可退役或保留为快速前置。
3. **提交前自检**：新增被 tracked 代码 import 的模块必须与其引用同批提交（可用本仓 `import app.main` 冒烟本地预跑）。
