# Batch 88 — 项目级 RBAC 全项目核验矩阵（C87-3）

> 日期：2026-08-05 | 环境：batch-88 worktree 后端 8044（独立 SQLite，seed 幂等补齐后）

## 1. 项目 × 成员 × 角色矩阵（全部项目）

| 项目 | code | 成员 | 角色 | role_id | 权限点数 |
|------|------|------|------|---------|---------|
| #1 CamelTv 体育平台 | cameltv | admin | 超级管理员 | 1 | *（全部） |
| #1 CamelTv 体育平台 | cameltv | tester | 测试人员 | 2 | 94（扩充后） |
| #2 项目 B（RBAC 核验） | proj-b-rbac | tester | 测试人员 | 2 | 94（扩充后） |

每个非超管成员均有一个项目内角色且权限集非空 → 无权限空洞。

## 2. 行为验证（真实 API）

| 场景 | 结果 |
|------|------|
| tester 在项目 1 建用例 `POST /test-cases` | HTTP 200（修复前 403，B87-Q1） |
| tester 在项目 2 建用例 `POST /test-cases` | HTTP 200 |
| tester 访问非成员项目 3 `POST /test-cases`（X-Project-Id=3） | HTTP 403（隔离不放宽） |
| tester 建系统用户 `POST /system/users` | HTTP 403（不越权） |

## 3. 存量库幂等补齐

后端重启触发 `run_seed()` → tester 角色自动补齐 51 项业务权限（RolePermission 无重复，幂等）；
验证路径：重启前建用例 403 → 重启 seed 补齐后 200。

## 4. 结论

C87-3（B87-Q1）闭环：全项目核验通过，tester 权限矩阵按 Design §1.2 修复，项目隔离语义保持。
