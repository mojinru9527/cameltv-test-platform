# Batch 216 — Design Spec
> **Design (🎨)** | Date: 2026-09-05 | Status: 就绪 | Executor: Codex | 完整批次

## 0. 技术体系确认
后端栈 FastAPI + SQLAlchemy + Alembic。本批**纯后端+DB**（无前端组件改动）。数据模型遵循 `app/models/base.py` 的 `TimestampMixin`（created_at/updated_at）。

## 1. 数据模型规格
### VersionTask（版本验收任务 · 唯一事实源）
| 字段 | 类型 | 语义 |
|------|------|------|
| id / project_id | int | 主键 / 项目 |
| title / version | string | 标题 / 版本号 |
| source | string | manual / mission / bundle |
| source_mission_id | int? FK | 旧智能测试任务指针（只读兼容，不双写） |
| source_bundle_id | int? FK | 发布包指针 |
| requirement_doc_id / release_bundle_id / environment_id | int? FK | 主链路关联（需求源/发布包/环境） |
| status | string | 状态机（draft→plan_review→approved→executing→executed→verdict→released；blocked/cancelled） |
| verdict | string | "" / pass / blocked / conditional |
| coverage / scope / risk | text(JSON) | 覆盖计数 / 范围 / 风险 |
| summary | text | 摘要 |
| created_by / qa_owner_id | int | 所有权 |

### VersionTaskExecution / VersionTaskDefect
多态关联表（runner/apitest/uitest/mission_scenario）与缺陷关联，使「执行记录/缺陷」可从版本任务反查。

## 2. 状态机设计（含可逆 / 打回）
```
draft → plan_review → approved → executing → executed → verdict → released
任一步可 → blocked → draft(返工) ；draft..executing 可 cancelled(终态)
非法流转(如 draft→released) 抛 APIException(code=1)
```
- 放行(released)未显式给结论时默认补 `pass`，保证证据包有「放行结论」。

## 3. 兼容映射（旧数据只读）
`VersionMission` → `VersionTask` 视图映射（`_mission_to_task_dict`）：只读投影，**绝不落库、绝无双写**；`legacy: true` 标记，接口路径 `/version-tasks/compat/missions/{id}`。

## 4. 状态设计核对（四态）
| 场景 | Loading | Empty | Error | 未启用 |
|------|---------|-------|-------|--------|
| 不适用（后端） | 前端 B7 处理 | 前端 B7 处理 | APIException(code=1) | 权限缺失 403 |

## 5. 设计 QA 走查发现（P0–P3）
### ⚪ P3-1 路由集合漂移
新增 9 条 `/version-tasks` 路由需同步 `tests/fixtures/route_inventory.json`，否则 route-inventory 守卫失败。→ **已更新**（count 608→617）。
### ⚪ P3-2 JSON 列 schema 校验
`coverage/scope/risk` 为 Text 存 JSON 字符串，Out schema 需 `field_validator(mode="before")` 解析 dict，否则 model_validate 报 dict_type。→ **已实现**。

## 6. 设计签核
结论：**通过**（B6 后端数据脊梁；状态机 + 兼容映射符合主链路 §4，无 UI 回归）。
