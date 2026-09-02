# Batch 217 — QA 报告：版本验收建任务向导（B7）
> **QA (🔍)** | Date: 2026-09-05 | Verdict: **PASS** | Executor: Codex | 完整批次

## 测试总览
| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 9 | 9 | 0 | 0（1 条后端全量基线失败非本批引入） |

## 可执行门禁（命令 + 退出码 + 结果）
| 门禁 | 命令 | 退出码/结果 |
|------|------|------------|
| 后端 app 导入 | `python -c "import app.main"` | 0 ✅ |
| 后端 F821 | `python -m ruff check app/ --select F821` | 0 ✅ |
| 新文件 ruff | `ruff check app/models/version_task_plan.py app/models/version_task.py app/services/version_task_service.py app/api/v1/version_task.py app/schemas/version_task.py` | 0 ✅ |
| version_task 单测 | `python -m pytest tests/test_version_task.py -q` | 8/8 ✅ |
| 路由层守卫 | `test_route_inventory.py` + `test_route_layer_orm_ban.py` | 4/4 ✅ |
| Alembic 单头 + drill | `alembic heads` + upgrade→downgrade→upgrade | 单头 + 全通过 ✅ |
| 前端 typecheck | `npm run typecheck` | 0 ✅ |
| 前端 lint | `npm run lint` | 0 ✅ |
| 前端 build | `npm run build` | 0 ✅ |
| 前端全量单测 | `npm run test` | 129 files / 608 tests ✅ |
| batch54 语义 token 守卫 | `batch54-production-governance.test.ts` | 8/8 ✅ |
| 后端全量回归 | `python -m pytest tests -q` | **2370 passed / 1 failed / 49 skipped / 1 xfailed** |

### 全量回归失败集合核对（无新增失败）
- 失败 1 条：`tests/test_batch148_p0_fixes.py::TestExecutionErrorFields::test_execute_all_records_error_fields` —— batch-212/215/216 已确认的 origin/main 既有基线；本批（新增 version_task_plan_item 表/路由/前端页）无关。其余 2370 全绿（含本批新增 2 例）。

## 逐条件验证
### C1: 方案条目模型 + 迁移
**变更文件**: app/models/version_task_plan.py、alembic/versions/20260906_version_task_plan_item.py
| 检查项 | 结果 | 说明 |
| 单头迁移 + drill | ✅ | 20260906_version_task_plan_item (head)；双向 drill 通过 |

### C2: 生成 + 审核 service
**变更文件**: app/services/version_task_service.py
| 检查项 | 结果 | 说明 |
| generate_plan | ✅ | 写入 2 条，order_index 递增 |
| adopt/modify/ask/remove | ✅ | 状态 adopted/modified/asked/removed |
| 非法 action | ✅ | 抛 APIException(code=1) |

### C3: API + route_inventory
**变更文件**: app/api/v1/version_task.py、tests/fixtures/route_inventory.json
| 检查项 | 结果 | 说明 |
| plan/generate + plan + plan/{id}/review | ✅ | HTTP 200 |
| route-inventory | ✅ | 620 条（+3），集合匹配 |

### C4: 前端向导 + 审核面板
**变更文件**: src/api/versionTask.ts、src/pages/version-tasks/index.tsx、src/router/index.tsx
| 检查项 | 结果 | 说明 |
| 3 步向导（建任务→审方案→确认） | ✅ | 结构 + 状态流转 |
| 审核面板（采纳/修改/追问/删除 + 置信度 + 待确认） | ✅ | |
| typecheck/build | ✅ | |
| batch54 语义 token（无固定色板） | ✅ | `text-amber-600` → `text-muted-foreground` |

## 缺陷列表
| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| 1 | P3 | 首版使用固定色板 `text-amber-600` 被 batch54 守卫拦截 | batch54 test | 已修复（语义 token） |
| 2 | P3 | `@/ui` Button variant 命名与 shadcn 不同（primary/secondary/ghost/danger） | typecheck | 已对齐 |

## 发布建议
状态: **READY**   必修复: 0   建议修复: 0（1 条全量回归失败 = origin/main 既有基线）

## 复盘卡（Batch 75 起强制）
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| ~5h / ~5.5h | 0/0/0/0 | 3（Button variant 命名、PageShell 需 title、固定色板） | 组件约定 | 用 @/ui 前先读其 props/variant 与语义 token 守卫 |

## 技能使用
- `cameltv-agent-team` → 六部门工件
- `cameltv-ui-conventions` → shadcn/ui 语义组件与 token
- `cameltv-bug-guard` → batch54 语义色板守卫、路由守卫
