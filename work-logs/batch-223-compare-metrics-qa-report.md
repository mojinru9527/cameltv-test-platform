# Batch 223 — QA 报告：跨版本对比 + 运营指标（B13）
> **QA (🔍)** | Date: 2026-09-03 | Verdict: **PASS** | Executor: Codex | 完整批次

## 测试总览
| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 8 | 8 | 0 | 0（1 条后端全量基线失败非本批引入） |

## 可执行门禁
| 门禁 | 命令 | 结果 |
|------|------|------|
| app 导入 / 后端 F821 | `import app.main` / `ruff check app/ --select F821` | 0 ✅ |
| 新/改文件 ruff | `ruff check app/services/version_task_service.py app/api/v1/metrics.py app/api/v1/version_task.py` | 0 ✅ |
| 单测 | `pytest tests/test_version_task.py` | 20/20 ✅ |
| 路由层守卫 | `test_route_inventory.py`+`test_route_layer_orm_ban.py` | 4/4 ✅ |
| 前端 typecheck/lint/build | `npm run typecheck`/`lint`/`build` | 0 ✅ |
| 前端全量单测 | `npm run test` | 129 / 608 ✅ |
| 后端全量回归 | `pytest tests -q` | **2384 passed / 1 failed / 49 skipped / 1 xfailed** |

### 失败核对
`test_batch148_p0_fixes` 为 origin/main 既有基线（batch-212 确认）。

## 逐条件验证
### C1: 运营指标
**变更文件**: app/services/version_task_service.py、app/api/v1/metrics.py
| 检查项 | 结果 | 说明 |
| get_operations_metrics（人天/周期/漏测/周活跃） | ✅ | 派生聚合 |
| GET /metrics/operations | ✅ | HTTP 200 |

### C2: 跨版本对比
**变更文件**: app/services/version_task_service.py、app/api/v1/version_task.py
| 检查项 | 结果 | 说明 |
| compare_versions（两版本覆盖/结论/缺陷） | ✅ | |
| GET /version-tasks/compare | ✅ | 于 /{task_id} 前声明（避免 422） |

### C3: 前端 /metrics
**变更文件**: src/api/versionTask.ts、src/pages/metrics/index.tsx、src/router/index.tsx
| 检查项 | 结果 | 说明 |
| 4 指标卡片 + 跨版本对比 | ✅ | typecheck/build 绿 |

## 缺陷列表
| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| 1 | P3 | naive vs aware datetime 比较 | 测试 | 用 naive cutoff |
| 2 | P3 | /compare 被 /{task_id} 吞掉 | 422 | 路由前移 |

## 发布建议
状态: **READY**   必修复: 0

## 复盘卡
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| ~4h / ~4h | 0/0/0/0 | 2 | datetime/路由 | 统一 datetime 时区；静态路由在参数路由前 |

## 技能使用
- `cameltv-agent-team`；`cameltv-bug-guard`
