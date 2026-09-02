# Batch 213 — Leader Verdict（首页我的待办 / B3 home-todo）
> **Leader (🎯)** | Date: 2026-09-02 | Decision: APPROVED

## 评审摘要
| 维度 | 评分 | 备注 |
|------|------|------|
| 实现质量 | A | 后端复用既有模型无新表；前端遵循 shadcn/`AsyncState`/中文映射/四态；首页落地为刻意产品决策 |
| 风险 | 低 | 新增只读 `/dashboard/todo`；不删旧接口；`/missions` 仍可达；无埋点 |
| 覆盖 | 好 | 后端 pytest（in-memory 真实 SQLite + 种子数据）+ 前端 612 vitest + typecheck/build/lint + app 导入 + ruff F821；后端全量回归 2362 passed / 1 baseline failed（`test_batch148_p0_fixes`，独立于本批，见 QA 报告） |

## 关键决策（已批准）
1. **首页落地 = 「我的待办」**：覆盖 V40-019 AITDE mission-first 默认落地。理由：平台重构定位「AI 版本验收工作台」，登录第一眼即「我的待办」为 B3/M0 出口标准；AITDE 引擎不再抢首页，经「版本验收」菜单 + `/missions` 路由仍深度可达。低风险（导航项与路由保留）。
2. **待放行桶 = `ReleaseBundle.status='active'`**：在 B9（放行页/完整验收状态机）落地前，用现有 active 状态近似「当前版本待验收」。已记录到交接区，B9 迁移到真实待放行语义。
3. **不删旧数字宫格接口**（`/dashboard/stats`、`/dashboard/cross-project`）：保持兼容，仅替换前端「工作台」展示。

## 抽检通过
- ✅ `backend/app/api/v1/dashboard.py:100` — `GET /todo` 路由，`R[DashboardTodo]` 响应。
- ✅ `backend/app/services/dashboard_service.py:272` — `get_todo_items` 聚合四桶，`project_id` 过滤 + 空桶兜底。
- ✅ `frontend/src/pages/workbench/index.tsx` — 我的待办四区，`AsyncState` 四态，条目 `Link` 直达。
- ✅ `frontend/src/router/index.tsx` — `PlatformHomeEntry` 默认 `/workbench`。
- ✅ `test-platform-v2/frontend npm test` — 612 passed；`test-platform-v2/backend pytest tests/test_dashboard_todo.py` — 2 passed。
- ✅ QA 报告含「代码实现逻辑审计」与「真实数据 mock / 防假成功」（in-memory 真实 SQLite 种子数据，非假成功）。

## 判决
**APPROVED** → 按 AGENTS.md 一次总确认（推送 + Draft PR + required checks 全绿后 squash 合入 main）。合入后从 main 更新并清理本 worktree。

## 下一批次 Leader 条件（如有）
- 无新增 C 条件。
- 移交：待放行完整验收状态机随 B9（batch-219）落地；VersionTask 统一事实源随 B6（batch-216）。

## 流程回写（Batch 75 起强制）
| 发现 | 处理 | 落点 |
|------|------|------|
| 前端图标先 import 后未引用导致 lint 拦截 | 先写 import 即引用 + lint 前置 | 本次 Dev 已修正；记入复盘卡 |
| 「待放行」在 VersionTask 未建前语义借用 active 状态 | 记录到交接区，B9 迁移 | 本批 Leader 判决 + 路线图 §5 交接区 |
