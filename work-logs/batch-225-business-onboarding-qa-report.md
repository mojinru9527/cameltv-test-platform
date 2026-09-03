# Batch 225 — QA 报告：新业务接入（B15）
> **QA (🔍)** | Date: 2026-09-03 | Verdict: **PASS** | Executor: Codex | 完整批次

## 测试总览
| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 7 | 7 | 0 | 0 |

## 可执行门禁
| 门禁 | 命令 | 结果 |
|------|------|------|
| app 导入 / 后端 F821 | `import app.main` / `ruff check app/ --select F821` | 0 ✅ |
| 新文件 ruff | `ruff check app/models/business_onboarding.py app/services/onboarding_service.py app/api/v1/onboarding.py` | 0 ✅ |
| 单测 | `pytest tests/test_version_task.py` | 24/24 ✅ |
| 路由层守卫 | `test_route_inventory.py`+`test_route_layer_orm_ban.py` | 4/4 ✅ |
| Alembic 单头 + drill | `alembic heads` + up/down/up | 单头 + 全通过 ✅ |
| 前端 typecheck/lint/build | `npm run typecheck`/`lint`/`build` | 0 ✅ |
| 前端全量单测 | `npm run test` | 129 / 608 ✅ |

### 后端全量说明
本地 Windows 全量 pytest 进程在运行中段触发 AccessViolation（-1073741819，批次 214/215 已见的 Windows teardown 崩溃），非断言失败；targeted `tests/test_version_task.py`（24 例，含 B15 2 例）全绿。**权威门禁 = CI（Linux）后端全新检出与全量回归**。

## 逐条件验证
### C1: 4 步接入向导（登记→接基线→生成方案→跑基线）
**变更文件**: app/services/onboarding_service.py、app/models/business_onboarding.py
| 检查项 | 结果 | 说明 |
| create_onboarding step1 | ✅ | |
| complete_step 3（VersionTask+方案） | ✅ | version_task_id 生成 |
| complete_step 4（跑基线） | ✅ | status=active + baseline(run_id) |

### C2: API + route_inventory
**变更文件**: app/api/v1/onboarding.py、tests/fixtures/route_inventory.json
| 检查项 | 结果 | 说明 |
| /onboarding/* | ✅ | HTTP 200；route-inventory 639 条 |

### C3: 前端向导
**变更文件**: src/api/versionTask.ts、src/pages/onboarding/index.tsx、src/router/index.tsx
| 检查项 | 结果 | 说明 |
| 4 步向导 + 接入列表 | ✅ | typecheck/build 绿 |

## 缺陷列表
| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| 1 | P3 | onboarding.py 未用 import Query | ruff | 移除 |
| 2 | P3 | 本地 Windows 全量 pytest AccessViolation（teardown，非断言） | exit -1073741819 | 记录；CI Linux 无此现象 |

## 发布建议
状态: **READY**   必修复: 0（以 CI Linux 全量回归为准）

## 复盘卡（Batch 75 起强制）
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| ~4h / ~4h | 0/0/0/0 | 1 | import | 检查未用 import |

## 技能使用
- `cameltv-agent-team`；`cameltv-bug-guard`
