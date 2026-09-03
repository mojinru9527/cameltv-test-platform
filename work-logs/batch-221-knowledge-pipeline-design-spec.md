# Batch 221 — Design Spec
> **Design (🎨)** | Date: 2026-09-03 | Status: 就绪 | Executor: Codex | 完整批次

## 0. 技术体系确认
后端 FastAPI + SQLAlchemy；无前端改动（纯后端+DB）。

## 1. 数据模型
### VersionKnowledgeRecord
| 字段 | 类型 | 语义 |
|------|------|------|
| task_id / project_id | int | 关联 version_task / 项目 |
| version / title / verdict | string | 版本标识与结论 |
| coverage / risk / plan_summary | text(JSON) | 覆盖/风险/方案 |
| defect_count | int | 缺陷数 |
- task_id 唯一（一个版本任务一条知识记录）。

## 2. 状态设计核对（四态）
无 UI；API 返回 {} 为空（未沉淀）。

## 3. 设计 QA 走查发现（P0–P3）
### ⚪ P3-1 路由直查 ORM
knowledge 端点直查 `db.query(VersionKnowledgeRecord)` 触 route-layer ORM ban。→ 已移入 `get_knowledge_record` service。

## 4. 设计签核
结论：**通过**（版本沉淀 + 复用建议，路由走 service）。
