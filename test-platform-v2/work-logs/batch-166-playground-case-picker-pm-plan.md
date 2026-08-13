# Batch batch-166-playground-case-picker — PM Plan
> **PM (🟨)** | Date: 2026-08-13

## 规格摘要
**原始需求**: Playground 从功能用例库勾选 1~N 条用例，批量编译 Playwright spec，执行/截图，结果回填用例，生成 trace/报告，并回写 UI 任务。

## 开发任务
### [ ] Task 1: 后端批量编译/执行 API
**描述**: 在 `playground.py` 增加 batch-compile 与 batch-run；`playground_service.py` 实现 `compile_case_batch` / `run_case_batch`，执行回填用例，写 spec 并创建 UI job。
**验收标准**: - batch-compile 返回逐条 spec_code/has_todo - batch-run 返回逐条 passed/stdout/screenshot/ui_job_id - 用例 last_run_status 回填
**涉及文件**: `backend/app/api/v1/playground.py`, `backend/app/schemas/playground.py`, `backend/app/services/playground_service.py`

### [ ] Task 2: 前端 Playground 用例库批量模式
**描述**: Playground 页增加域/模块/正负向/关键字筛选、用例勾选表格、批量编译/执行按钮、结果展示；保留手动输入模式。
**验收标准**: - 筛选生效 - 勾选 1~N - 批量结果/截图展示 - 无 N+1 请求
**涉及文件**: `frontend/src/pages/playground/index.tsx`, `frontend/src/api/playground.ts`

### [ ] Task 3: 测试与门禁
**描述**: 补充后端 batch compile 测试与前端相关检查；跑 typecheck/build/vitest/ruff/pytest。
**验收标准**: 相关测试通过，required checks 绿。

## 质量要求
- [x] 响应式（Desktop + Tablet）  - [x] OpenAPI 同步  - [x] 单元测试覆盖
- [x] 无障碍（ARIA/键盘）  - [x] 无 console 报错/告警
