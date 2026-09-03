# Batch 221 — QA 报告：知识管线（B11）
> **QA (🔍)** | Date: 2026-09-03 | Verdict: **PASS** | Executor: Codex | 完整批次

## 测试总览
| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 7 | 7 | 0 | 0（1 条后端全量基线失败非本批引入） |

## 可执行门禁
| 门禁 | 命令 | 结果 |
|------|------|------|
| app 导入 | `import app.main` | 0 ✅ |
| 后端 F821 | `ruff check app/ --select F821` | 0 ✅ |
| 新/改文件 ruff | `ruff check app/models/version_knowledge.py app/services/version_task_service.py app/api/v1/version_task.py` | 0 ✅ |
| version_task+mainline | `pytest tests/test_version_task.py tests/test_mainline_walkthrough.py -q` | 17/17 ✅ |
| 路由层守卫 | `test_route_inventory.py`+`test_route_layer_orm_ban.py` | 4/4 ✅ |
| Alembic 单头 + drill | `alembic heads` + up/down/up | 单头 + 全通过 ✅ |
| 后端全量回归 | `pytest tests -q` | **2379 passed / 1 failed / 49 skipped / 1 xfailed** |

### 失败核对
`test_batch148_p0_fixes` 为 origin/main 既有基线（batch-212 确认）。其余 2379 全绿（含本批 2 例）。

## 逐条件验证
### C1: 版本沉淀（release 自动记录）
**变更文件**: app/services/version_task_service.py
| 检查项 | 结果 | 说明 |
| release_task 自动 record | ✅ | VersionKnowledgeRecord 落库（version/verdict/coverage） |
| 复用建议 reuse（采纳/修改条目） | ✅ | get_reuse_suggestions 返回 |

### C2: API + 路由（无 ORM 直查）
**变更文件**: app/api/v1/version_task.py、tests/fixtures/route_inventory.json
| 检查项 | 结果 | 说明 |
| GET /knowledge/reuse + /{id}/knowledge | ✅ | HTTP 200 |
| route-inventory | ✅ | 629 条（+2） |
| route-layer ORM ban | ✅ | 移入 service |

## 缺陷列表
| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| 1 | P3 | knowledge 端点直查 ORM 触 route-layer ban | test_route_layer_orm_ban | 移入 get_knowledge_record service |

## 发布建议
状态: **READY**   必修复: 0

## 复盘卡
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| ~4h / ~4h | 0/0/0/0 | 1 | 路由契约 | 路由只调 service；DB 查询放 service |

## 技能使用
- `cameltv-agent-team`；`cameltv-bug-guard` → route-layer ORM ban
