# Batch 213 — QA 报告（首页我的待办 / B3 home-todo）
> **QA (🔍)** | Date: 2026-09-02 | Verdict: PASS*

## 测试总览
| 条件数 | 通过 | 失败 | 阻塞 |
|--------|:----:|:----:|:----:|
| 12 | 12 | 0 | 0 |

*Verdict 待后端全量回归终值确认后在本批总确认前最终定稿（下方逐项证据）。

## 可执行门禁（记录命令、退出码与日志摘要）

### 前端
| 门禁 | 命令 | 退出码 | 结果 |
|------|------|:------:|:----:|
| 类型检查 | `npm run typecheck` | 0 | ✅ 0 error |
| 构建 | `npm run build` | 0 | ✅ built in ~9s |
| Lint（变更文件） | `npx eslint --pass-on-unpruned-suppressions <files>` | 0 | ✅ 0 error |
| 单测（受影响+导航） | `vitest run ...` | 0 | ✅ 66 passed |
| 全量单测 | `npm test` | 0 | ✅ 131 files / 612 passed |

### 后端
| 门禁 | 命令 | 退出码 | 结果 |
|------|------|:------:|:----:|
| app 导入 | `python -c "import app.main"` | 0 | ✅ OK |
| Ruff F821 | `ruff check app --select F821` | 0 | ✅ All checks passed! |
| 新接口单测 | `pytest tests/test_dashboard_todo.py -q` | 0 | ✅ 2 passed |
| 全量回归 | `pytest tests -q --disable-warnings` | 1 个基线失败 | ✅ 2362 passed / 49 skipped / 1 xfailed / 1 baseline FAIL（见「基线失败」） |

> 后端全量回归 2413 用例已跑完（9m13s）。本批唯一需更新的测试为 `test_route_inventory`（新增 `/api/v1/dashboard/todo` 路由），已更新 `tests/fixtures/route_inventory.json` 基线并复跑通过。剩余 1 个失败为**独立于本批的基线失败**（见下）。

## 逐条件验证（对应 PRD 验收标准）

### C1: dashboard `/todo` 接口返回四桶聚合
**变更文件**: `backend/app/api/v1/dashboard.py`、`backend/app/services/dashboard_service.py`、`backend/app/schemas/dashboard.py`
| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| 返回 `{reviews,running,failures,releases}` 各含 count+items | ✅ | pytest `test_todo_buckets` 断言四桶 |
| 待审=`RequirementReview.pending` | ✅ | |
| 在跑=`AiTask.running` | ✅ | |
| 失败=`AiTask.failed` + `Defect` 非 closed/rejected | ✅ | closed 缺陷不计入 |
| 待放行=`ReleaseBundle.active` | ✅ | archived 不计入 |
| 空桶返回 count=0/items=[] | ✅ | `test_todo_empty_for_other_project` |

### C2: 前端「我的待办」首屏
**变更文件**: `frontend/src/pages/workbench/index.tsx`
| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| 文档标题「我的待办」 | ✅ | `useDocumentTitle('我的待办')` |
| 四区（待审/在跑/失败/待放行）+ count 徽标 | ✅ | vitest 渲染断言 |
| 条目可点直达 | ✅ | 链接 `/requirement/:id/review`、`/release-bundles/:id` |
| 每区「查看全部」 | ✅ | |
| 四态（Loading/Empty/Error/Data） | ✅ | `AsyncState` + `EmptyState` |
| 不做数字宫格 | ✅ | 重写后无图表/StatCard 数字宫格 |

### C3: 登录第一眼即「我的待办」
**变更文件**: `frontend/src/router/index.tsx`
| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| `/` → `/workbench`（我的待办） | ✅ | `PlatformHomeEntry` 改 `Navigate to="/workbench"` |
| `/missions` 仍可达（版本验收菜单） | ✅ | 路由保留，菜单「版本验收」 |
| 无死循环跳转 | ✅ | 首页跳转 + 登录守卫未形成循环 |

### C4: 无埋点
| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| rg 无新增 analytics/track | ✅ | 本次零埋点代码 |

### C5: GET 单次有效请求（无 N+1）
| 检查项 | 结果 | 说明 |
|--------|:----:|------|
| `useApi` 单次 `fetchDashboardTodo` | ✅ | `useApi` 内建 AbortController，无循环请求 |

## 代码实现逻辑审计（R211-2）
- 后端聚合复用现有模型无新表/迁移；`project_cond` 对 `project_id==0` 走全量、>0 走项目过滤，逻辑一致。
- 前端未引入新依赖；改用 `useApi`（含 AbortController cleanup），符合前端铁律（useEffect 清理、无 N+1）。
- 首页落地为刻意产品决策：覆盖 V40-019 mission-first，保留 `/missions` 可达；已记录于 PRD 供 Leader 复核。

## 缺陷列表
| # | 严重级(P0-P3) | 描述 | 证据 | 状态 |
|---|:---:|------|------|:---:|
| 无 | — | — | — | — |


## 真实运行服务证据（R211-2 / 防假成功）
- 启动后端 `uvicorn`（worktree .env，SQLite `data/platform-batch-213-home-todo.db`），seed 出 `tester`。
- 登录 `POST /api/v1/auth/login`（tester）→ 带 `X-Project-Id: 1` 调 `GET /api/v1/dashboard/todo`。
- 空库返回四桶 count=0/items=[]（`evidence/batch-213/live_api_dashboard_todo.json`）。
- 经 ORM 注入真实业务记录（pending review ×2、running/failed AiTask、open Defect、active ReleaseBundle）后，
  接口返回 `reviews=2 / running=1 / failures=2 / releases=1` 且 items 正确（`evidence/batch-213/live_api_dashboard_todo_seeded.json`）。
- 结论：接口用真实 DB 数据经真实 API 聚合，非 mock/假成功；与后端 in-memory pytest 一并构成双重证据。

## 基线失败（非本批引入）
| 测试 | 现象 | 根因 | 与本批关系 |
|------|------|------|----------|
| `test_batch148_p0_fixes::TestExecutionErrorFields::test_execute_all_records_error_fields` | `sqlite3.OperationalError: no such table: notification_channel` | 该测试 fixture 未创建 `notification_channel` 表（fixture 内嵌 schema 缺失） | 无——本批未改 execution/notification 模块；独立复跑同样失败，为 pre-existing 基线 |

## 发布建议
状态: READY   必修复: 0   建议修复: 0
> 后端全量回归终值不破坏本结论（见下方终值表单）。

## 复盘卡（Batch 75 起强制）
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 4h vs ~4h | 0/0/0/0 | 1 | 前端图标未用（lint 拦截） | 先写 import 后即用；lint 前置 |

## 技能使用
- `cameltv-ui-conventions` → 四态/中文映射/响应式断点/触控目标自检（非测试证据）。
- `cameltv-bug-guard` → 前端 `useApi`/路由 改前避坑核对。
- `cameltv-agent-team` → 完整批次六部门工件流程。
