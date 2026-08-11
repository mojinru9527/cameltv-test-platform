# Batch 149 — PM 计划（统计口径收敛 + 计划列表进度）

> **PM (🟨)** | Date: 2026-08-11 | 与 PRD 对齐，不加豪华需求

## 规格摘要
**原始需求**: FIX-147-P1-01/02（C147-3/C147-4） | **目标时间**: 当日开发 + QA + 合入

## 开发任务

### [ ] T1: 批次脚手架
**描述**: worktree/PRD/PM/Design/看板就位
**验收**: verify-ai-worktree 通过
**涉及文件**: work-logs/batch-149-*

### [ ] T2: statistics_service 统一统计源
**描述**: 新建服务：total_cases/api_cases/total_plans、execution_total/pass/fail、cases_in_plans/cases_executed/cases_passed、by_type；全部批量查询防 N+1
**验收**: 单测覆盖数字口径（含 is_deleted 用例不计入总数、执行记录不因用例删除丢失）
**涉及文件**: backend/app/services/statistics_service.py

### [ ] T3: dashboard 接入统一统计 + 修复执行计数
**描述**: get_dashboard_stats 的用例/计划/执行/类型统计改用 statistics_service（priority_distribution 保留本地）
**验收**: 接口 case_type_stats[].execution_pass/fail 与 test_execution 一致；total_cases=7879 口径
**涉及文件**: backend/app/services/dashboard_service.py

### [ ] T4: trace 补 is_deleted + 接入统一统计
**描述**: get_project_coverage 的 total_cases/by_type 用 statistics_service；cases_in_plans/cases_executed/cases_passed 补 is_deleted=False；by_domain 补过滤
**验收**: 追溯总数与 dashboard 一致；已执行/已通过与执行记录一致
**涉及文件**: backend/app/services/trace_service.py

### [ ] T5: PlanOut 补 stats 字段（计划列表 0/0）
**描述**: `PlanOut` 增加 `stats: PlanStats = PlanStats()`；确认 list_plans 响应带 stats
**验收**: GET /test-plans 每项含 stats.total/pass_；前端进度非 0/0
**涉及文件**: backend/app/schemas/test_plan.py

### [ ] T6: 测试
**描述**: statistics_service 口径单测 + plan 列表 stats API 测试 + trace is_deleted 测试 + dashboard 执行计数测试
**验收**: 受影响 pytest 全绿
**涉及文件**: backend/tests/test_batch149_statistics.py

### [ ] T7: 前端验证
**描述**: 计划列表进度展示依赖 r.stats；工作台/追溯展示不变（数据源已统一）。本地冒烟三端数字一致
**验收**: 冒烟截图 + 数字一致性日志
**涉及文件**: 无前端代码改动（如冒烟发现需要则补）

## 质量要求
- [x] OpenAPI 同步（PlanOut.stats）
- [x] 单元测试覆盖（统计口径）
- [x] 无 console 报错/告警
