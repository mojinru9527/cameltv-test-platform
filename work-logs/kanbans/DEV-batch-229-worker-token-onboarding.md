# Dev 看板 — Batch 229 Worker Token Onboarding

> Executor: Codex | Workflow: agent-team | Created: 2026-09-04

## 项目信息

| 字段 | 值 |
|------|-----|
| 分支 | `fix/batch-229-worker-token-onboarding` |
| 基线 | `origin/main@29daf57f` |
| PRD | `work-logs/batch-229-worker-token-onboarding-prd-summary.md` |
| PM | `work-logs/batch-229-worker-token-onboarding-pm-plan.md` |
| Design | `work-logs/batch-229-worker-token-onboarding-design-spec.md` |
| 预计工时 | 4.5h |

## 切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 |
|---|-------|:----:|:----:|:----:|:----:|:----:|
| 1 | Worker Token 鉴权契约 | ✅ | 🔄 | ⏳ | ⏳ | ⏳ |
| 2 | 前端可发现生成链路 | ✅ | ⏳ | ⏳ | ⏳ | ⏳ |
| 3 | 一次性配置与撤销入口 | ✅ | ⏳ | ⏳ | ⏳ | ⏳ |
| 4 | Runbook 与启动器 fail-fast | ✅ | ⏳ | ⏳ | ⏳ | ⏳ |
| 5 | QA、PR、合入 | ✅ | ⏳ | ⏳ | ⏳ | ⏳ |

## 当前位置

`Batch 229 → Slice 1 → TDD 红灯`。已完成根因与方案核对；下一步先写 scoped API Token heartbeat 失败测试。

## 已确认根因

| 根因 | 等级 | 处理 |
|------|------|------|
| Token UI 默认只生成 `trigger` | P1 | 用途选择映射最小作用域 |
| heartbeat 仅接受网页登录 JWT | P1 | 专用 API Token scope 鉴权 |
| Runtime 只让用户阅读 Runbook | P1 | 页面直达预选 Worker Token 流程 |
| 空 Token 启动后循环 401 | P1 | 启动器进程拉起前 fail-fast |

## 风险

| 风险 | 等级 | 处理 |
|------|------|------|
| Worker Token 获得过宽权限 | P0 | 仅 `workers:register`，错误 scope 403 |
| 创建响应中的明文泄露 | P0 | 一次显示、关闭清空、证据不截秘密 |
| 改动影响网页登录 Worker 管理 | P1 | list/drain/disable 保持现有 RBAC 并回归 |
| 旧 CI Token 意外注册 Worker | P1 | 集成测试固定拒绝 |

## 相关工件

| 工件 | 状态 |
|------|:----:|
| PRD | ✅ |
| PM 计划 | ✅ |
| 设计规范 | ✅ |
| 实施计划 | ✅ |
| QA 报告 | ⏳ |
| Leader 判决 | ⏳ |
