# Batch 162 — Design Spec

> **Design (🎨)** | Date: 2026-08-12

## 架构决策
后端: TestSchedule.environment_id（FK→environment）+ schedule_service 校验 + scheduler 透传 execute_all_cases(environment_id)
前端: schedule 表单加「执行环境」Select（复用 /environments 数据）；列表新增「执行环境」列；含 API 计划未选环境时提交拦截（后端为准）
DB: Alembic 迁移 add test_schedule.environment_id（nullable，旧数据 NULL → 需编辑绑定）
## 实现文件
后端: models/test_schedule.py、schemas/test_schedule.py、services/schedule_service.py、core/scheduler.py、api/v1/schedule.py、migration
前端: pages/schedule/index.tsx（表单+列表）
脚本: scripts/backfill-surface-c161.py
## 性能基准
无新增热点；调度执行仍为后台单次执行。
