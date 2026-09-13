# Batch 233 — PM Plan
> **PM (🟨)** | Date: 2026-09-13

## 规格摘要
**原始需求**: 关闭 `C230-1`，为 `production_operation:allowed` 与 `apitest:execute_prod` 写入认证操作人。
**目标时间**: 1 个 Agent Team 批次。

## 开发任务
### [ ] Task 1: 统一审计身份解析
**描述**: 在 audit service 增加按 `user_id` 解析稳定登录名的 helper；未知用户返回空字符串但保留 id，禁止使用昵称。
**验收标准**: 已存在用户得到 `username`；未知用户不抛错。
**涉及文件**: `test-platform-v2/backend/app/services/audit_service.py`
**参考**: PRD §4/§5

### [ ] Task 2: production_operation_guard 透传操作人
**描述**: `require_allowed_operation` 增加 `user_id` 参数并写入 `production_operation:allowed` audit；更新全部调用点。
**验收标准**: 认证操作触发 guard 后 audit 的 `user_id/username` 正确。
**涉及文件**: `app/services/production_operation_guard.py`, `api/v1/{apitest_tasks,integration,release_bundles_core,test_case_crud}.py`
**参考**: PRD §4

### [ ] Task 3: API 执行审计透传操作人
**描述**: `quick_execute` / `execute_api_case` 增加可选 `actor_user_id`，贯通 dataset、dependency、plan 和 task worker 调用链；`_check_prod_protection` 写入操作人且审计失败 fail-closed。
**验收标准**: direct route、quick route、worker、plan executor 均写入正确操作人。
**涉及文件**: `app/services/api_execution_service.py`, `api_task_worker.py`, `test_plan_service.py`, API routes
**参考**: PRD §4/§5

### [ ] Task 4: 回归与条件关闭
**描述**: 增加身份、worker creator、fail-closed 回归；运行 ruff/import/pytest；更新 C-CONDITIONS。
**验收标准**: 相关测试全绿，C230-1 具备 Closed 证据。
**参考**: PRD §2/§6

## 质量要求
- [x] OpenAPI 不需要变更（未新增接口/字段）
- [x] 单元测试覆盖
- [x] 无 migration
- [x] 无前端改动
