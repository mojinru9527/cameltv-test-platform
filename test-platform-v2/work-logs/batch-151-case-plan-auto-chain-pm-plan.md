# Batch 151 — PM 计划（功能用例入计划 + 失败自动链路）

> **PM (🟨)** | Date: 2026-08-11

## 开发任务
### [ ] T1: 脚手架
### [ ] T2: TestPlan.auto_defect_on_fail + 迁移 + schema
**涉及**: models/test_plan.py、alembic/versions/20260811_batch151_auto_defect.py、schemas/test_plan.py
### [ ] T3: 失败自动链路 service + router 后台任务 + notify plan_failed
**涉及**: services/test_plan_service.py、api/v1/test_plan.py、services/notify_service.py
### [ ] T4: AddCasesModal 类型筛选 + 徽标
**涉及**: pages/testplan/AddCasesModal.tsx
### [ ] T5: PlanDrawer 开关
**涉及**: pages/testplan/PlanDrawer.tsx
### [ ] T6: 测试 + 冒烟
**涉及**: backend/tests/test_batch151_auto_chain.py、AddCasesModal.test.tsx

## 质量要求
- [x] 迁移幂等
- [x] 开关默认关闭（生产数据安全）
- [x] 后台任务独立 session
- [x] 单测覆盖自动三件套
