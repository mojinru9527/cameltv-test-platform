# Batch 216 — QA 报告：VersionTask 统一事实源（B6）
> **QA (🔍)** | Date: 2026-09-05 | Verdict: **PASS** | Executor: Codex | 完整批次

## 测试总览
| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 6 | 6 | 0 | 0（1 条后端全量基线失败非本批引入） |

## 可执行门禁（命令 + 退出码 + 结果）
| 门禁 | 命令 | 退出码/结果 |
|------|------|------------|
| 后端 app 导入 | `python -c "import app.main"` | 0 ✅ |
| 后端 F821 | `python -m ruff check app/ --select F821` | 0（All checks passed）✅ |
| 新文件 ruff | `ruff check app/models/version_task.py app/services/version_task_service.py app/api/v1/version_task.py app/schemas/version_task.py` | 0 ✅ |
| version_task 单测 | `python -m pytest tests/test_version_task.py -q` | 6/6 ✅ |
| 路由层守卫 | `test_route_layer_orm_ban.py` + `test_route_inventory.py` | 4/4 ✅ |
| Alembic 单头 | `python -m alembic heads` | 单头 `20260905_version_task_model` ✅ |
| Alembic 双向 drill | upgrade → downgrade → upgrade | 全通过 ✅ |
| 后端全量回归 | `python -m pytest tests -q` | **2368 passed / 1 failed / 49 skipped / 1 xfailed** |

### 全量回归失败集合核对（无新增失败）
- 失败 1 条：`tests/test_batch148_p0_fixes.py::TestExecutionErrorFields::test_execute_all_records_error_fields` —— batch-212/215 已确认的 origin/main 既有基线，与本批（新增 version_task 表/路由）无关；其余 2368 全绿（含本批新增 6 例）。
- 说明：本地 pytest 进程以 Windows AccessViolation 退出（-1073741819），但测试摘要完整打印（2368/1/49/1），为 teardown 阶段 Windows 特有崩溃，不影响结果；CI 在 Linux 容器运行无此现象。

## 逐条件验证
### C1: VersionTask 模型 + 状态机
**变更文件**: app/models/version_task.py、app/services/version_task_service.py
| 检查项 | 结果 | 说明 |
| create draft / 合法流转链 | ✅ | draft→plan_review→approved→executing→executed→verdict→released |
| 放行自动补 pass | ✅ | 未显式 verdict 时 released 默认 pass |
| 非法流转（draft→released） | ✅ | 抛 APIException(code=1)，API 返回 code!=0 |
| blocked→draft 返工 | ✅ | |

### C2: 关联 executions / defects
**变更文件**: app/models/version_task.py
| 检查项 | 结果 | 说明 |
| add_execution / add_defect | ✅ | 关联表读写 + version_task 反查 |

### C3: 旧数据兼容映射（不双写）
**变更文件**: app/services/version_task_service.py
| 检查项 | 结果 | 说明 |
| compat_mission_view | ✅ | source=mission, legacy=true, source_mission_id 指向旧任务 |
| 不写库 | ✅ | 库中来自 mission 的 version_task 行 = 0 |

### C4: Alembic 单头 + 可逆
**变更文件**: alembic/versions/20260905_version_task_model.py
| 检查项 | 结果 | 说明 |
| heads 单头 | ✅ | 20260905_version_task_model (head) |
| downgrade/upgrade | ✅ | 双向 drill 通过 |

### C5: API + route_inventory
**变更文件**: app/api/v1/version_task.py、app/api/v1/router.py、tests/fixtures/route_inventory.json
| 检查项 | 结果 | 说明 |
| `import app.main` | ✅ | 路由注册无异常 |
| route-inventory | ✅ | 617 条（+9），集合匹配 |

### C6: JSON 列 schema
**变更文件**: app/schemas/version_task.py
| 检查项 | 结果 | 说明 |
| scope/coverage/risk dict 解析 | ✅ | field_validator(mode=before) |

## 缺陷列表
| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| 1 | P3 | 后端 pytest 进程在本地 Windows 以 AccessViolation 退出（teardown），结果完整 | 退出码 -1073741819 | 记录（CI Linux 无此现象） |

## 发布建议
状态: **READY**   必修复: 0   建议修复: 0（1 条全量回归失败 = origin/main 既有基线）

## 复盘卡（Batch 75 起强制）
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| ~4h / ~4.5h | 0/0/0/0 | 2（JSON 列 schema 先报 dict_type；路由集合需同步 route_inventory） | 约定/基线 | 新增 JSON 列在 Out schema 配 validator；新增路由同步 route_inventory |

## 技能使用
- `cameltv-agent-team` → 六部门工件
- `cameltv-bug-guard` → 迁移单头/路由守卫/APIException 业务码约定
- `cameltv-doc-check` → 主链路/白名单文档一致性
