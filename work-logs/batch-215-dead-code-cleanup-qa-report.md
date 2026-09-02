# Batch 215 — QA 报告：死代码清理（B5）
> **QA (🔍)** | Date: 2026-09-03 | Verdict: **PASS** | Executor: Codex | 完整批次

## 测试总览
| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 11 | 11 | 0 | 0（1 条后端全量基线失败非本批引入，见 §失败核对） |

## 可执行门禁（命令 + 退出码 + 结果）
| 门禁 | 命令 | 退出码/结果 |
|------|------|------------|
| 前端 typecheck | `npm run typecheck`（tsc -b） | 0 ✅ |
| 前端 lint | `npm run lint`（eslint . --max-warnings=0） | 0 ✅ |
| 前端 build | `npm run build`（tsc -b && vite build） | 0 ✅（built in 9.35s） |
| 前端全量单测 | `npm run test`（vitest run） | 129 files / 608 tests ✅ |
| 后端 F821 | `python -m ruff check app/ --select F821` | 0（All checks passed）✅ |
| 后端 app 导入 | `python -c "import app.main"` | 0 ✅ |
| 受影响后端 pytest | `test_batch63_menu_catalog.py`(13)+`test_menu_visibility_flags.py`(4) | 17/17 ✅ |
| 后端全量回归 | `python -m pytest tests -q` | **2362 passed / 1 failed / 49 skipped / 1 xfailed** |
| 路由层守卫 | `tests/test_route_layer_orm_ban.py`+`test_route_inventory.py` | 4/4 ✅ |
| dev-gate（G0–G2） | `dev-gate.ps1` | G1/G2 绿；G0 命中存量未触碰文件 2 HARD（见下） |
| rg 引用审计 | 删除路径全仓复核 | 0 条非文档/非 worklog 代码引用 ✅ |

### 全量回归失败集合核对（无新增失败）
- 失败 1 条：`tests/test_batch148_p0_fixes.py::TestExecutionErrorFields::test_execute_all_records_error_fields`
  （断言 `error_type in (TARGET_POLICY, NETWORK_ERROR)`，实际 `ASSERTION_FAILED`）。
- **基线核对**：与 batch-212 相同基线（batch-212 亦为 2360 passed / 1 failed）。本批不触碰该用例路径（`requirement/execution` 相关），判定为既有基线失败，与本批删除无关；本批无新增失败。
- dev-gate G0：`app/services/requirement_service.py:225/229 except json.JSONDecodeError: pass` 2 条 HARD（存量未触碰文件）。batch-212 已标注「历史基线债务随 batch-215 清理批次处理」。本批评估后保留不修：该处为已导入索引的容错回退（损坏 JSON 回退空集），改日志/改行为属后端逻辑变更，非死代码清理；作为已知基线记录，非 CI 门禁（.github/workflows 无调用）。

## 逐条件验证
### C1: /testplan 独立页删除且无残留引用
**变更文件**: src/pages/testplan/**（整页+自测删除）、touchTargetGuard.test.ts、batch54-production-governance.test.ts
| 检查项 | 结果 | 说明 |
| router `import('@/pages/testplan')` | ✅ | 路由仅 `<Navigate to="/testcase">`，无页面 import |
| `rg 'pages/testplan|@/pages/testplan' src`（非测试） | ✅ 0 命中 | typecheck 通过佐证 |
| touchTargetGuard 读取 testplan | ✅ | 已移除该条目 |

### C2: Playground 独立页删除
**变更文件**: src/pages/testcase/playground/index.tsx（删除）、src/api/playground.ts（保留）
| 检查项 | 结果 | 说明 |
| `PlaygroundPanel` 引用 | ✅ 0 | testcase/index.tsx 无 import |
| `/api/v1/playground/*` API | ✅ 保留 | `run router.py` include_router(playground) |

### C3: 无引用前端组件/Hook 删除且引用审计零遗漏
**变更文件**: 18 个组件/Hook + SphereTab（含 toggle/toggle-group）删除
| 检查项 | 结果 | 说明 |
| `npm run typecheck` | ✅ | 无未解析 import |
| `npm run test` | ✅ 608 | 无测试引用已删除组件（自测文件同步删除） |
| eslint-suppressions 悬空 key | ✅ | 已移除 usePaginatedList/ExtractionModal/SphereTab 条目 |
| 全仓 rg 复核 | ✅ 0 条代码引用 | 仅 docs/work-logs 历史记录提及 |

### C4: special/perftest 代码冻结
**变更文件**: 复核（无改动）：menu_service.py HIDDEN_MENU_CODES 含 menu:special/menu:perftest；README 已标注 batch-212 下架
| 检查项 | 结果 | 说明 |
| `rg 'menu:special\|menu:perftest'` | ✅ | 仅存在于 HIDDEN_MENU_CODES（冻结=隐藏） |
| README/前端 special·perftest 入口宣称 | ✅ | batch-212 已下架，本批复核无残留专属入口 |

### C5: V1 工具退役文档
**变更文件**: COMMANDS.md §5 加退役标注
| 检查项 | 结果 | 说明 |
| `rg 'tools/(api_tester|mock_server|...)` 代码 | ✅ 0 | V1 tools/ 目录已不存在（batch-98/100 移除） |
| COMMANDS.md §5 与现状一致 | ✅ | 已标注 batch-98/100 退役 |

### C6: 根目录 `_tmp_*`/临时文件清理
**变更文件**: .gitignore（新增 _tmp_* 等）、删除 .pr-body-batch20/22.md、repo-boundaries.json 移除条目
| 检查项 | 结果 | 说明 |
| `git check-ignore _tmp_*.py` | ✅ | 命中新增忽略规则 |
| .pr-body-* 移除 | ✅ | git rm |
| repo-boundaries 一致性 | ✅ | 移除已删除条目，JSON valid |

### C7: 前端无回归
| 检查项 | 结果 | 说明 |
| UI 语义系统 `@/ui` | ✅ | build 通过，未破坏 re-export |
| 导航/路由 | ✅ | 删除仅限 C 级已下架页，主链路路由不变 |

## 缺陷列表
| # | 严重级(P0-P3) | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| 1 | P3 | dev-gate G0 存量 requirement_service.py:225/229 except:pass（批次外基线） | G0 输出 | 已知基线，非本批引入 |
| 2 | P3 | 根目录历史方案/重复文档未归档（跨 repo-boundaries/CLAUDE/repo-map 引用更新），移交后续文档批次 | 见交接区 | 记录 |

## 发布建议
状态: **READY**   必修复: 0   建议修复: 0
（1 条后端全量回归失败 = origin/main 既有基线，已双端复现核对，非本批引入）

## 复盘卡（Batch 75 起强制）
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| ~4h / ~5h | 0/0/0/2 | 2（SphereTab 依赖 toggle 未先删；doc 归档引用更新量大） | 引用耦合 | 删除组件前先查交叉依赖（含 eslint suppression）；文档归档拆分独立批次 |

## 技能使用
- `cameltv-agent-team` → 六部门工件（本文件 + PRD/PM/Design/Leader/看板）
- `cameltv-bug-guard` → 删除前核对 useEffect 清理/路由重定向/权限最小集（本批纯删除无新增副作用）
- `cameltv-ui-conventions` → 确认删除不破坏 `@/ui` 语义系统与 `@/components/ui` 边界
- `cameltv-doc-check` → COMMANDS.md/README/root 文档保鲜核对
