# Batch 148 — PM 计划（P0 缺陷契约 + 执行根因可见/环境预检）

> **PM (🟨)** | Date: 2026-08-11 | 与 PRD 对齐，不加豪华需求

## 规格摘要
**原始需求**: FIX-147-P0-01/02（C147-1/C147-2） | **目标时间**: 当日完成开发 + QA + 合入

## 开发任务

### [ ] T1: 批次脚手架
**描述**: worktree/分支/PRD/PM/Design/看板 六件套就位并提交
**验收**: `verify-ai-worktree.ps1` 通过；工件齐全
**涉及文件**: work-logs/batch-148-*.md、work-logs/kanbans/DEV-batch-148-*.md

### [ ] T2: 后端缺陷契约修复（P0-01 后端侧）
**描述**: `DefectCreate.assignee_id` 改 `Optional[int]=None`；`defect_service.create_defect` 将 None 归一为 0 写入模型
**验收**: POST /defects 不传 assignee_id → HTTP 200 code=0；传 null 同样通过；传 0 通过
**涉及文件**: backend/app/schemas/defect.py、backend/app/services/defect_service.py

### [ ] T3: 前端错误提取链修复（P0-01 崩溃根因）
**描述**: `client.ts` 422 `detail` 数组 → 可读字符串；`DefectFormDialog` doSave 加 catch + 弹窗内错误提示，失败不关闭
**验收**: 单测覆盖「数组 detail 不崩溃」；对话框失败态显示错误并保持打开
**涉及文件**: frontend/src/api/client.ts、frontend/src/pages/defect/DefectFormDialog.tsx、新单测

### [ ] T4: 执行字段模型 + 迁移（P0-02 后端）
**描述**: `TestExecution` 加 status_code/error_type/error_message 三列 + Alembic 迁移（inspector 守卫）
**验收**: `alembic heads` 单头；迁移在空库可 upgrade/downgrade
**涉及文件**: backend/app/models/test_plan.py、backend/alembic/versions/20260811_batch148_execution_error_fields.py

### [ ] T5: 执行记录回填 + 历史解析（P0-02 后端）
**描述**: execute_all_cases/auto_execute_api_cases 写独立字段；`_execution_to_dict` 对空字段从 actual_result 回填；`ExecutionOut` 增加三字段
**验收**: 新执行记录三字段非空；历史 JSON 记录读取后三字段可解析
**涉及文件**: backend/app/services/test_plan_service.py、backend/app/schemas/test_plan.py

### [ ] T6: 环境/Token 预检（P0-02 后端）
**描述**: 服务层 `ensure_plan_execution_ready`：API 用例计划必须选环境；环境属当前项目；相对路径需 base_url；缺失 `${var}` 变量拦截
**验收**: 无环境 → code!=0 明确提示且 0 条新执行记录；缺 base_url/缺 token → 对应提示
**涉及文件**: backend/app/services/test_plan_service.py（+ 复用 environment_service）

### [ ] T7: 前端执行历史列 + 环境选择器（P0-02 前端）
**描述**: PlanDetail 头部加执行环境 Select（sentinel 空值）；批量执行/一键执行带 environment_id；执行历史表加失败原因/HTTP 状态/失败阶段三列（error_type 中文映射，历史解析展示）
**验收**: 未选环境点执行 → 前端 toast 拦截；选择后请求带 environment_id；失败行三列有值
**涉及文件**: frontend/src/api/testplan.ts、frontend/src/pages/testplan/PlanDetail.tsx

### [ ] T8: 后端/前端测试 + 文档
**描述**: 后端补 defect 契约/预检/字段回填测试；前端补 DefectFormDialog 失败态 + client 422 detail 测试；`docs/common-pitfalls.md` 记录「422 detail 数组必须字符串化」经验
**验收**: 受影响 pytest/vitest 通过；typecheck/build 通过；无 console.log/调试遗留
**涉及文件**: backend/tests/*、frontend/src/**/*.test.*、docs/common-pitfalls.md

## 质量要求
- [x] 响应式（Desktop + Tablet）— 执行历史表横向滚动保持
- [x] OpenAPI 同步 — ExecutionOut/DefectCreate 变更
- [x] 单元测试覆盖 — 后端契约+预检、前端失败态
- [x] 无障碍（ARIA/键盘）— 新增 Select/列保持 label
- [x] 无 console 报错/告警
