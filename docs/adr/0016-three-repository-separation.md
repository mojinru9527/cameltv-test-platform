---
title: "ADR-0016: 测试平台三仓分离（前端 / 后端 / 运维平台）"
owner: "arch-team"
created: "2026-08-02"
last_reviewed: "2026-08-02"
status: "accepted"
expires: "2027-02-02"
tags: ["adr", "architecture", "repository", "repo-split", "frontend-backend", "ops-platform"]
related:
  - "0003-frontend-backend-physical-separation.md"
  - "0015-operations-release-control-plane.md"
  - "../../docs/architecture/batch-64-architecture-analysis.md"
  - "../../repo-boundaries.json"
---

# ADR-0016：测试平台三仓分离（前端 / 后端 / 运维平台）

## 状态

✅ 已采纳（执行按 P0–P4 分阶段，每阶段独立批次）

## 日期

2026-08-02

## 背景

ADR-0003 实现了 `test-platform-v2/` 内 `backend/` 与 `frontend/` 的**目录级物理分离**：
独立 Dockerfile、独立 CI 阶段、仅 REST 契约通信。但目录级分离不足以支撑以下管理诉求：

1. **按版本分仓排期**：某些版本只做前端、某些版本只做后端，需要仓库级独立版本与 PR/CI 生命周期。
2. **运维平台发布**：前端、后端、数据库迁移需要组成不可分割的 release unit，并统一由运维发布控制面
   （ADR-0015）编排发布；单仓内无法把运维控制面作为独立交付对象演进。
3. **V1 退役节奏**：`test-platform/`（V1）与 V2 同仓，拆分后 V1 可独立走退役审计，不再干扰 V2 主线。
4. **团队/关注点隔离**：前端、后端、运维三个关注点的变更面、依赖与发布窗口不同。

同时，仓库根目录存在无归属的误提交文件，缺少机器可校验的路径归属约束——拆仓前必须建立边界事实源。

## 决策

采用**三仓分离**目标架构，并以 `repo-boundaries.json` 作为路径归属事实源：

| 仓库 | 内容 | 发布物 |
|------|------|--------|
| `cameltv-test-frontend` | `test-platform-v2/frontend/`（React + shadcn/ui + Vite） | Nginx/Vercel 静态站点 |
| `cameltv-test-backend` | `test-platform-v2/backend/` + `lanhu-mcp/`（FastAPI + 执行引擎） | 后端镜像 |
| `cameltv-ops-platform` | `deploy/` + release-control 事实层 + 发布 API/UI（ADR-0015 Phase 2） | 运维平台镜像 |

共享资产（`docs/`、`tests/`、`work-logs/`、CI 模板、根元数据）留在当前仓库作为共享根目录，
不强制独立成仓；`test-platform/`（V1）标记为 `deprecated-v1`，退役受覆盖矩阵门禁。

### 关键约束

1. **契约事实源不变**：后端 `/openapi.json` → 前端 `npm run gen:api`；禁止跨仓 import。
2. **版本模型**：三仓各自 SemVer；对外产品版本以蓝湖「更新日志」手写版本为准；
   发布单元 = release manifest（ADR-0015 §4.1），一次构建一个 `release_id`。
3. **边界强制**：`scripts/repo-split/validate_repo_boundaries.py --check` 必须通过；
   新增顶层路径必须先声明归属（最长前缀优先）。
4. **拆仓方式**：每个仓库独立批次执行（git filter-repo/subtree 或等价受控迁移），
   保留提交历史与 ADR 追溯；禁止一次性大爆炸迁移。

## 后果

### 正面影响

- ✅ 前端/后端/运维可独立排期、独立版本、独立发布，匹配「某些版本做前端、某些做后端」的管理模型。
- ✅ 运维平台（ADR-0015 Phase 2）获得独立演进边界，不把 CD 逻辑塞进业务页面。
- ✅ V1 退役可独立审计，不阻塞 V2 主线。
- ✅ 路径归属机器可校验，杜绝无主路径与意外跨仓耦合。

### 负面影响 / 权衡

- ⚠️ 拆仓期间 CI/PR/依赖管理需要双轨并行，存在迁移成本。
- ⚠️ 需要维护三套仓库的门禁、Secret 与发布配置（以 release manifest 收敛）。
- ⚠️ 共享资产（tests/、docs/）需要明确的消费方式（当前仓库共享目录或独立资产仓）。
- ⚠️ 契约变更的跨仓同步成本提高（以 OpenAPI 自动生成缓解）。

## 弃选方案

### 方案 A：维持单仓目录分离（现状）

- 优点：零迁移成本。
- 缺点：无法仓库级独立版本/发布；运维平台无法独立演进；V1 退役绑定 V2 主线。
- 放弃原因：不满足用户明确的管理与发布诉求。

### 方案 B：前后端两仓（不做运维平台仓）

- 优点：比三仓简单。
- 缺点：运维发布控制面无处安放，ADR-0015 Phase 2 只能塞进后端仓，混淆业务与 CD 边界。
- 放弃原因：运维平台是独立的交付对象与关注点。

### 方案 C：四仓（共享资产也独立成仓）

- 优点：边界最纯粹。
- 缺点：tests/docs 与代码仓强关联，独立成仓增加消费成本。
- 放弃原因：共享目录 + 边界校验已满足隔离需求，不必过度拆分。

## 关联

- ADR-0003（目录级分离，历史语义保留，交付目标由本 ADR 替代）
- ADR-0015（运维发布控制面）
- [架构解析报告](../../docs/architecture/batch-64-architecture-analysis.md)
- [repo-boundaries.json](../../repo-boundaries.json)
