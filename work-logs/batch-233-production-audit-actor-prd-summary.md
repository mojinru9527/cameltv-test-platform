# Batch 233 — Production Audit Actor
> **Product (🟦)** | Date: 2026-09-13 | Status: Approved | mode: full

## 1. 问题陈述
生产环境操作与生产接口执行的审计记录当前没有认证操作人：`production_operation:allowed` 和 `apitest:execute_prod` 都使用默认 `user_id=0`、`username=""`。这会破坏生产操作的追责与合规性，用户无法从审计日志回答“谁触发了这次生产操作”。

Batch 230 已定位并登记 C230-1；本轮专门关闭该条件，不扩展业务范围。

## 2. 成功指标
| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 生产操作审计身份 | 0 | 100% 写入认证用户 id + 稳定登录名 | 本批测试 |
| 生产接口执行审计身份 | 0 | direct/quick/task/plan 入口全部透传 | 本批测试 |
| 审计失败策略 | 部分静默 | 生产审计不可写时 fail-closed | 本批测试 |
| schema 变更 | 0 | 0（复用现有 audit 字段和任务 creator_id） | 本批测试 |

## 3. 非目标
- 不新增审计页面、API 或数据库列。
- 不改权限模型、RBAC 规则和生产确认语义。
- 不执行真实生产变更；真实浏览器证据使用本地/测试应用服务。

## 4. 用户故事 + 验收标准
- As a QA/审计人员, I want production audit rows to contain the actor identity, so that production actions are attributable.
- 验收：Given an authenticated user executes a production-sensitive operation / When the operation is recorded / Then `sys_audit_log.user_id` equals the user id and `username` equals the stable login name.
- 验收：Given an API task worker executes a production case later / When `apitest:execute_prod` is recorded / Then the task creator is used as actor.
- 验收：Given audit persistence raises / When production protection is evaluated / Then execution fails closed and does not proceed without the audit row.

## 5. 技术考量
- 现有 `AuditLog` 已有 `user_id` / `username` 字段，无 migration。
- worker 没有 `CurrentUser`，必须使用 `ApiExecutionTask.creator_id` 恢复操作人。
- 计划执行已有 `executor_id`，直接传入服务层。

## 6. 上线计划
| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 本地/测试 | QA | 相关 pytest + F821 + app import 全绿 |
| PR 合入 | main | required checks + 最终审计通过 |
