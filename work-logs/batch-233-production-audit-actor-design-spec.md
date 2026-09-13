# Batch 233 — Design Spec
> **Design (🎨)** | Date: 2026-09-13 | Status: Ready

## 0. 技术体系确认
后端 FastAPI + SQLAlchemy；`AuditLog` 已有 `user_id`、`username` 字段，无 schema 变更。无 UI/前端改动。

## 1. 身份契约
| 字段 | 来源 | 规则 |
|------|------|------|
| `user_id` | `CurrentUser.user.id` / `ApiExecutionTask.creator_id` / `executor_id` | 正整数；0 仅保留给系统/旧调用 |
| `username` | `User.username` | 稳定登录名；禁止 nickname、禁止空字符串覆盖真实用户 |

## 2. 调用链
| 入口 | 身份来源 | 目标审计 |
|------|---------|---------|
| production operation route | `CurrentUser.user.id` | `production_operation:allowed` |
| quick execute route | `CurrentUser.user.id` | `apitest:execute_prod` |
| single case execute route | `CurrentUser.user.id` | `apitest:execute_prod` |
| API task worker | `ApiExecutionTask.creator_id` | `apitest:execute_prod` |
| plan API execution | `executor_id` | `apitest:execute_prod` |
| dependency/dataset recursive execution | 原入口 actor 继续透传 | `apitest:execute_prod` |

## 3. 失败策略
`write_audit` 失败时，生产保护路径不得继续。`production_operation_guard` 继续 fail-closed；`_check_prod_protection` 移除 `except: pass`，让审计不可用成为可观测失败。

## 4. 测试设计
- 直接调用 guard：认证 user id/username 写入正确。
- 直接调用 quick/case：prod audit 写入正确。
- worker：creator_id 被恢复为 actor。
- 审计写入失败：生产执行被阻断。
- 非生产/无 environment 路径：不写 prod audit，不回归。

## 5. 设计签核
结论：通过。无视觉组件、无状态展示、无响应式改动。
