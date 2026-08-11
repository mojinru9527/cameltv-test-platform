# Batch 151 — 本地端到端冒烟证据（2026-08-11）

> 环境：worktree 独立 SQLite + 前端 5241 + 后端 8071。

## 失败自动链路（开关开启）
- 计划 `auto_defect_on_fail=true` + API 用例执行失败 1 条
- **自动缺陷**：`[AI分诊] B151SMOKE-接口用例 — flaky_env`，execution_id=1（缺陷↔执行↔用例预填）✅
- **自动报告**：`失败自动报告-B151SMOKE-自动链路计划-202608111944` ✅
- 通知：plan_failed 模板已接入（单测 patch 验证调用；冒烟未配置渠道）
- 关闭开关时 0 自动写入（pytest 覆盖）

## 功能用例入计划
- 计划详情 cases 同时含 `api` 与 `manual`（B151SMOKE-功能用例）✅
- AddCasesModal 类型筛选（全部/功能/接口/UI）截图 `add-cases-type-filter.png`
- 计划详情截图 `plan-detail-cases.png`

## 硬门禁
| 门禁 | 结果 |
|------|------|
| ruff F821 | ✅ |
| 受影响 pytest | ✅ 36 passed（含自动链路 5） |
| alembic heads + 迁移 | ✅ 单头 20260811_batch151_auto_defect |
| 前端 typecheck/build | ✅ |
| 前端全量 vitest | ✅ 113 files / 456 tests |
