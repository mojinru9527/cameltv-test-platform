# Batch 169 — PM Plan
> **PM (🟨)** | Date: 2026-08-13

## 开发任务
### [ ] Task 1: execute-all 异步化（C168-2）
**描述**: ExecuteAllBody 增 async_mode；路由 async_mode=true 时 BackgroundTasks 后台执行并立即返回；前端传 async_mode 并轮询 stats.pending。
**验收**: async 请求 <5s 返回；后台执行结束后 executions 可见；async_mode=false 行为不变。
**文件**: backend/app/api/v1/test_plan.py、services/test_plan_service.py、schemas；frontend/src/api/testplan.ts、pages/testplan/PlanDetail.tsx

### [ ] Task 2: UI 执行超时可配置 + 编译稳定
**描述**: settings.ui_run_timeout_seconds 默认 90；SYSTEM_PROMPT 禁用 networkidle、默认超时、等待选择器。
**验收**: 单条 UI 执行 90s 内返回；新 spec 不含 networkidle。
**文件**: backend/app/core/config.py、services/case_compiler_service.py、services/test_plan_service.py

## 质量要求
- [x] 后端全量 pytest + ruff F821  - [x] 前端 typecheck/lint/build/vitest
- [x] 旧契约默认兼容  - [x] 无 console 报错
