# Batch 221 — PM Plan
> **PM (🟨)** | Date: 2026-09-05 | Executor: Codex | 完整批次

## 规格摘要
**原始需求**: B11 版本沉淀 + 复用建议（后端+DB）。

## 开发任务
### [ ] Task 1: VersionKnowledgeRecord 模型 + 迁移
**描述**: `app/models/version_knowledge.py`（version/verdict/coverage/risk/plan_summary/defect_count）+ `alembic/versions/20260908_version_knowledge_record.py`（chained B8 head）。
**验收标准**: import ok；alembic 单头；drill 通过。

### [ ] Task 2: 沉淀 + 复用 service
**描述**: `record_version_knowledge(db, task_id)`；`get_knowledge_record(db, task_id)`；`get_reuse_suggestions(db, project_id, limit)`；release_task 自动调 record。
**验收标准**: 放行后知识落库；复用建议返回采纳/修改条目。

### [ ] Task 3: API + route_inventory
**描述**: `GET /version-tasks/knowledge/reuse`、`GET /version-tasks/{task_id}/knowledge`；route_inventory 629。
**验收标准**: 路由守卫绿（无 ORM 直查）。

### [ ] Task 4: 测试
**描述**: tests/test_version_task.py 增 2 例（release 沉淀 + reuse API）。
**验收标准**: 17 通过。

## 质量要求
- [x] OpenAPI 同步 — 2 新路由
- [ ] 单元测试 — 17
- [ ] 无 console 报错
