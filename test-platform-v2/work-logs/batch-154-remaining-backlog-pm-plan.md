# Batch 154 — PM 计划（四项收口）

> **PM (🟨)** | Date: 2026-08-11

## 开发任务
### [ ] T1: 脚手架
### [ ] T2: 迁移 + 模型/schema（dataset_id、case_id）
**涉及**: alembic/versions/20260811_batch154_links.py、models/test_case.py、models/ui_test.py、schemas/test_case.py、schemas/ui_test.py
### [ ] T3: WS1 数据集参数化（后端兜底 + CaseDrawer + ApiCaseTab）
**涉及**: api_execution_service.py、CaseDrawer.tsx、ApiCaseTab.tsx
### [ ] T4: WS2 图谱治理（backfill + evolve 加固 + 删除级联）
**涉及**: knowledge/entity_service.py、knowledge/knowledge_cleanup.py、api/v1/knowledge.py、defect/requirement/test_case service
### [ ] T5: WS3 UI 映射（case_id 贯通 + 回写 + from-cases + uitest UI）
**涉及**: ui_test_service.py、api/v1/ui_test.py、uitest/index.tsx
### [ ] T6: WS4 env 统一入口 + 孤儿清理
**涉及**: docs/env-unified-guide.md、scripts/env-inventory.ps1、tracked 孤儿删除
### [ ] T7: 测试 + QA
**涉及**: backend/tests/test_batch154_remaining.py、前端相关测试

## 质量要求
- [x] 迁移幂等
- [x] 单测覆盖四项
- [x] 无 console/调试遗留
