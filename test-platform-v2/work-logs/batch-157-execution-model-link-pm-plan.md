# Batch 157 — PM 计划（执行模型双向关联）

> **PM (🟨)** | Date: 2026-08-12

**原始需求**: PRD batch-157  **目标时间**: 本批次（约 4h）

## 开发任务
### [ ] S1: 脚手架（PRD/PM/Design/看板）
**涉及**: work-logs/batch-157-*、kanbans/DEV-batch-157

### [ ] S2: 迁移 + 模型 + schema
- 迁移 20260812_batch157_exec_link（两列幂等）
- TestExecution.api_task_id；ApiExecutionTaskItem.test_execution_id
- ApiTaskItemOut.test_execution_id；_execution_to_dict.api_task_id

### [ ] S3: 计划 API 执行登记任务+快照
- test_plan_service.execute_all_cases / auto_execute_api_cases
- 辅助函数 _ensure_plan_api_task / _register_api_task_snapshot

### [ ] S4: 前端展示
- PlanDetail 执行历史「API 任务」列
- TaskTab 明细「关联计划执行」

### [ ] S5: 单测 test_batch157_exec_link.py
- 计划执行 → 任务+item 双向关联；apidest 独立任务无关联

### [ ] S6: QA 硬门禁 + 证据

## 质量要求
- [x] 迁移单头 + 幂等
- [x] 不改变同步执行语义
- [x] 无 N+1（每计划运行 1 任务 + 每 API 用例 1 item，线性）
- [x] 既有测试不回归
