---
title: "Batch 63 — 全功能点正负面资产矩阵（B60-P1-017）"
owner: "qa-team"
created: "2026-08-02"
status: "active"
tags: ["batch-63", "function-point-matrix", "acceptance-assets"]
related:
  - "../../test-platform-v2/work-logs/batch-63-legacy-issue-closure-qa-report.md"
  - "../../test-platform-v2/work-logs/batch-63-regression-57-62-summary.md"
---

# Batch 63 全功能点正负面资产矩阵

> 规则：功能点 → 正/负面用例位置 → 证据状态 → 缺陷。Mock/组件证据与真实后端证据
> 分层统计，禁止互相冒充。`EXTERNAL-BLOCKED` 不计通过。

## 1. 认证与安全

| 功能点 | 正面证据 | 负面证据 | 状态 |
|---|---|---|---|
| JWT 签发/校验（HS256） | `test_security_jwt.py` 6 项 | 过期/篡改/错误密钥 4 项 | PASS |
| 登录与强制改密 | `test_auth.py`、`test_forced_password_change.py` | 弱密码/旧 JWT/重置 Token fail-closed | PASS |
| 供应链（backend runtime） | `requirements.lock` 无 python-jose/ecdsa | pip-audit 复查（QA 阶段） | PASS（待 audit 复核） |

## 2. 项目隔离与 RBAC

| 功能点 | 正面证据 | 负面证据 | 状态 |
|---|---|---|---|
| 项目 A→B 切换（九域前端矩阵） | `projectIsolationMatrix.test.tsx` 10 项 | 切换后陈旧行清零、每切换 1 次 GET | PASS（本地契约） |
| X-Project-Id 请求头注入 | `projectHeader.test.ts` 2 项 | 无项目时不注入 | PASS |
| 跨项目 API 隔离 | environment/apitest/ui-artifact/batch59 等 75 项 | 跨项目 404/403 零副作用 | PASS |
| 菜单/命令面板/权限一致 | `test_batch63_menu_catalog.py` 4 项、`CommandPalette.test.ts` 3 项 | 无 release:view 隐藏运维入口 | PASS |

## 3. API 测试执行（五入口 + 生产保护）

| 功能点 | 正面证据 | 负面证据 | 状态 |
|---|---|---|---|
| quick/asset 执行 | `test_batch63_production_guard_matrix.py` 正向 1 项 + parity 2 项 | 生产写无 confirm → 400 零网络 | PASS |
| single 用例执行 | `test_batch60_api_production_guard.py` 转发 | 生产写无 confirm → 400 不执行 | PASS |
| group/batch 任务 | `test_batch59_lifecycle_acceptance.py` | 跨项目/生产无确认 → 400/404 零任务行 | PASS |
| 五入口请求构造统一 | `apiExecutionRequest.test.ts` 5 来源 + 契约 3 项 | quick 缺 request → throw | PASS |
| 目标策略（host/重定向/私网） | `test_api_execution_target_policy.py` | 跨 host/重定向改目标 → TARGET_POLICY | PASS |

## 4. 用例服务

| 功能点 | 正面证据 | 负面证据 | 状态 |
|---|---|---|---|
| 模块分类管理 | `CategoryManagerDialog.test.tsx` 7 项（TPv2-B19-C1 关闭） | 无 ID 分类禁用删除 | PASS |
| 批量删除确认 | `testcase/index.test.tsx`（Batch 60 新增） | 取消零请求、确认后提交 | 代码+单测 PASS；浏览器/DB/审计闭环待 QA 复测 |
| 用例导入（Knife4j 自动发现） | `test_openapi_import_knife4j.py` 9 项（TPv2-B21-C2 关闭） | HTML 页回退候选 URL | PASS |

## 5. 知识中心

| 功能点 | 正面证据 | 负面证据 | 状态 |
|---|---|---|---|
| Skills/图谱/Wiki 前置条件 fail-closed | `test_batch60_*` 知识相关 82 项 + `SourceListTab.test.tsx` | 无 AI/无 active bundle → 503/禁用 | PASS |
| 桌面标签布局（B60-P2-006） | 本批 `index.tsx` lg 换行修复 | 1440 无横向滚动（浏览器复核待 QA） | 代码 PASS；浏览器证据待补 |

## 6. 运维发布（只读）

| 功能点 | 正面证据 | 负面证据 | 状态 |
|---|---|---|---|
| release-control 核心 | `deploy/release-control` 22 项 | manifest 非法/篡改/生产命令全拒绝 | PASS |
| 只读 API/UI | `test_ops_release_api.py` 3 项 + 前端 2 项 | 未配置 store → 503 | PASS |

## 7. 外部阻塞（不计通过）

| 功能点 | 状态 | 解除条件 |
|---|---|---|
| Test5/VPN 六服务 R2 | EXTERNAL-BLOCKED | VPN 授权 + 六契约 + 账号 |
| 真实 AI/OCR/蓝湖 | EXTERNAL-BLOCKED | 非生产凭据 + 数据授权 |
| 通知/集成真实端点 | EXTERNAL-BLOCKED | 非生产端点 + 凭据 |
| 真机性能 | EXTERNAL-BLOCKED | 设备 + 采集窗口 |
| 旧 PostgreSQL 迁移 | EXTERNAL-BLOCKED | 脱敏快照 + 断言 |
| 云注册 C58 | EXTERNAL-BLOCKED | 外部注册 + 秘密回填 |

## 8. 统计

| 类别 | 数量 |
|---|---|
| PASS（本地可复核） | 22 个功能点 |
| 代码 PASS + 待浏览器/动态复核 | 2（批量删除闭环、桌面布局） |
| EXTERNAL-BLOCKED | 6 |
