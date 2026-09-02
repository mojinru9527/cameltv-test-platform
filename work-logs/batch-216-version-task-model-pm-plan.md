# Batch 216 — PM Plan
> **PM (🟨)** | Date: 2026-09-05 | Executor: Codex | 完整批次

## 规格摘要
**原始需求**: B6 VersionTask 统一事实源（后端+DB）。
**目标时间**: 单头 migration + 可逆 drill；旧数据可读不双写。

## 开发任务
### [ ] Task 1: VersionTask 模型（表 + 状态机 + 关联）
**描述**: 新增 `app/models/version_task.py`：`VersionTask`（project_id/title/version/source/source_mission_id/source_bundle_id/requirement_doc_id/release_bundle_id/environment_id/status/verdict/coverage/summary/scope/risk/created_by/qa_owner_id）+ `VersionTaskExecution`（多态 execution 关联）+ `VersionTaskDefect`（缺陷关联）。在 `app/models/__init__.py` 注册。
**验收标准**: `import app.models` 成功；`VersionTask.__tablename__ == "version_task"`。
**涉及文件**: `app/models/version_task.py`、`app/models/__init__.py`

### [ ] Task 2: Alembic 单头迁移 + 可逆 drill
**描述**: 新增 `alembic/versions/20260905_version_task_model.py`（down_revision=`20260904_aitde_v40_governance`），建 3 表 + 索引；downgrade 反序删表。
**验收标准**: `alembic heads` 单头=本文件；upgrade→downgrade→upgrade 全通过。
**涉及文件**: `alembic/versions/20260905_version_task_model.py`

### [ ] Task 3: Schema + Service（状态机 / 兼容映射）
**描述**: `app/schemas/version_task.py`（Create/Update/Transition/Out/ListItem/links，JSON 列 validator）；`app/services/version_task_service.py`（create/list/get/update/transition/add_execution/add_defect/compat_mission_view/compat_mission_list；`TRANSITIONS` 状态机；`_mission_to_task_dict` 只读映射）。
**验收标准**: 合法流转成功、非法流转抛 `APIException(code=1)`；compat 只读不写库。
**涉及文件**: `app/schemas/version_task.py`、`app/services/version_task_service.py`

### [ ] Task 4: API 路由 + 注册
**描述**: `app/api/v1/version_task.py`（/version-tasks CRUD + /transition + /executions + /defects + /compat/missions）；在 `api/v1/router.py` 注册；`tests/fixtures/route_inventory.json` 增 9 条路由。
**验收标准**: `import app.main` 成功；route-inventory 测试绿。
**涉及文件**: `app/api/v1/version_task.py`、`app/api/v1/router.py`、`tests/fixtures/route_inventory.json`

### [ ] Task 5: 测试
**描述**: `tests/test_version_task.py`：模型/状态机/关联/compat 不双写 3 例 + API CRUD/transition/link 2 例 + 非法流转 1 例。
**验收标准**: `python -m pytest tests/test_version_task.py -q` 6 通过。
**涉及文件**: `tests/test_version_task.py`

## 质量要求
- [x] 响应式（Desktop + Tablet） — 纯后端不适用
- [x] OpenAPI 同步 — 新路由已入 route_inventory；OpenAPI 自动生成
- [ ] 单元测试覆盖 — version_task 6 例 + 全量回归
- [x] 无障碍（ARIA/键盘） — 不适用
- [ ] 无 console 报错/告警 — 后端无前端
