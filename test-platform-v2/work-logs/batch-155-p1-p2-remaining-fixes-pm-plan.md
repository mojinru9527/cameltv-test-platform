# Batch 155 — PM 计划（P1-07 自动链路 + P2 未收口项全修复）

> **PM (🟨)** | Date: 2026-08-11

**原始需求**: PRD batch-155（P1-07 + P2 20 项）  **目标时间**: 本批次（约 20h）

## 开发任务
### [ ] S1: 脚手架（工件 + C147-6 重开）
**涉及**: work-logs/batch-155-*-prd/pm/design、kanbans/DEV-batch-155、C-CONDITIONS.md

### [ ] S2: P1-07 后端自动链路（C147-6）
- models/test_plan.py 补 auto_defect_on_fail（对齐迁移 20260811_batch151_auto_defect）
- schemas/test_plan.py PlanCreate/Update/Out 贯通
- services/test_plan_service.py：执行完成后 failed>0 且开关开 → 后台任务（独立 session）：rule triage → create_defect → create_report → notify plan_failed
- services/notify_service.py：plan_failed 模板/事件
- api/v1/test_plan.py：执行路由挂 BackgroundTasks；开关读写
- backend/tests/test_batch155_auto_chain.py

### [ ] S3: P1-07 前端开关
- types/index.ts + api/testplan.ts 加 auto_defect_on_fail
- PlanDrawer/PlanDetail 开关（Checkbox）+ 展示

### [ ] S4: P2-01 计划执行入口收敛
- PlanDetail.tsx：合并「批量执行/一键执行」为「执行」+ 范围（全部/API）弹窗；手动录入默认「请选择」必选

### [ ] S5: P2-09/10 执行任务管理 + 批量生成
- backend：api_execution_task 删除/重跑端点（认领式重跑）、generateApiCases 支持 service_id 批量
- frontend TaskTab 删除/重跑按钮；AssetTab 服务级「批量生成用例」

### [ ] S6: P2-11/12 架构治理
- api_task_worker/task_worker 原子认领守卫；api_execution_task.test_execution_id 关联（迁移）
- requirement_service↔test_case_service 环：懒加载收敛 + 注释

### [ ] S7: P2-15/18 报告定时 + 调度停用原因
- TestSchedule.job_type='report' 支持 + scheduler 回调生成报告
- TestSchedule.disabled_reason 迁移 + schema + UI 必填/展示

### [ ] S8: P2 前端体验组（02/04/07/08/13/14/16/17/19/20/21/22/23）
- CommandPalette 关闭态不入 a11y 树；弹窗项目名取 currentProject.name；音视频 URL 校验；占位页「未启用」标识；缺口 P0 排序；UI 任务 Trace 列回填/链接；专项更名「专项测试」；发布包空态构建引导；调度/缺陷/报告/通知 aria-label；用例标题可点；计划状态「全部」；集成 Test5 标注不可达/移除；知识中心 Tabs forceMount(visited)

### [ ] S9: QA 硬门禁 + 证据
- ruff F821、pytest（受影响）、alembic 单头、typecheck/build/vitest、冒烟

## 质量要求
- [x] 迁移幂等 + 单头
- [x] 自动链路开关默认关（生产数据安全）
- [x] 后台任务独立 session
- [x] React 副作用四律（cleanup/依赖/无 N+1/Tabs 条件渲染）
- [x] 无 console.log/print 调试残留
