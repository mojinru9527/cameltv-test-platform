# Batch 218 — QA 报告：版本任务执行与证据（B8）
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
| 新/改文件 ruff | `ruff check app/models/version_task_run.py app/models/version_task.py app/services/version_task_service.py app/api/v1/version_task.py app/schemas/version_task.py` | 0 ✅ |
| version_task 单测 | `python -m pytest tests/test_version_task.py -q` | 11/11 ✅ |
| 路由层守卫 | `test_route_inventory.py` + `test_route_layer_orm_ban.py` | 4/4 ✅ |
| Alembic 单头 + drill | `alembic heads` + upgrade→downgrade→upgrade | 单头 + 全通过 ✅ |
| 前端 typecheck | `npm run typecheck` | 0 ✅ |
| 前端 lint | `npm run lint` | 0 ✅ |
| 前端 build | `npm run build` | 0 ✅ |
| 前端全量单测 | `npm run test` | 129 / 608 ✅ |
| batch54 语义 token 守卫 | `batch54-production-governance.test.ts` | 8/8 ✅ |
| 后端全量回归 | `python -m pytest tests -q` | **2373 passed / 1 failed / 49 skipped / 1 xfailed** |

### 全量回归失败集合核对（无新增失败）
- 失败 1 条：`tests/test_batch148_p0_fixes.py::TestExecutionErrorFields::test_execute_all_records_error_fields` —— batch-212/215/216/217 已确认的 origin/main 既有基线；本批（新增 version_task_run 表/路由/详情页）无关。其余 2373 全绿（含本批新增 3 例）。

## 逐条件验证
### C1: version_task_run 模型 + 迁移
**变更文件**: app/models/version_task_run.py、alembic/versions/20260907_version_task_run.py
| 检查项 | 结果 | 说明 |
| 单头 + drill | ✅ | 20260907_version_task_run (head)；双向 drill 通过 |

### C2: 一键运行 + 覆盖回写
**变更文件**: app/services/version_task_service.py
| 检查项 | 结果 | 说明 |
| start_run | ✅ | progress=100；passed/failed/skipped/blocked 计数 + total |
| coverage 回写（C217-1） | ✅ | task.coverage 含 pass/fail/skip/blocked；task.status→executed |

### C3: 失败四分类 + 缺陷草稿
**变更文件**: app/services/version_task_service.py
| 检查项 | 结果 | 说明 |
| failure kind（business/script/data/environment） | ✅ | item_type 驱动 |
| create_defect_draft | ✅ | Defect(open) + version_task_defect link |

### C4: API + route_inventory
**变更文件**: app/api/v1/version_task.py、tests/fixtures/route_inventory.json
| 检查项 | 结果 | 说明 |
| run / runs / run detail / defect | ✅ | HTTP 200 |
| route-inventory | ✅ | 624 条（+4），集合匹配 |

### C5: 前端详情页
**变更文件**: src/api/versionTask.ts、src/pages/version-tasks/[taskId].tsx、src/router/index.tsx
| 检查项 | 结果 | 说明 |
| 运行按钮 + Progress + 覆盖 + 证据 + 失败转缺陷 | ✅ | typecheck/build 绿 |
| 语义 token / Badge variant | ✅ | variant=destructive；无固定色板 |

## 缺陷列表
| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| 1 | P3 | Badge variant="danger" 无效（Badge 无该 variant） | typecheck | 已改 variant="destructive" |
| 2 | P3 | handleDefect 未用 title 参数 | lint | 已移除 |

## 发布建议
状态: **READY**   必修复: 0   建议修复: 0（1 条全量回归失败 = origin/main 既有基线）

## 复盘卡（Batch 75 起强制）
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| ~5h / ~5.5h | 0/0/0/0 | 2（Badge variant、unused param） | 组件约定 | 用 @/ui 前读 variant/props；及时清 unused |

## 技能使用
- `cameltv-agent-team` → 六部门工件
- `cameltv-ui-conventions` → Badge tone/variant 语义
- `cameltv-bug-guard` → 语义守卫/路由守卫
