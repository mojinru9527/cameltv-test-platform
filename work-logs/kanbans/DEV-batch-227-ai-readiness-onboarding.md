# Dev 看板 — Batch 227 AI 全链路就绪向导

> Executor: Codex | Workflow: agent-team | Created: 2026-09-03

## 项目信息

| 字段 | 值 |
|------|-----|
| 分支 | `feature/batch-227-ai-readiness-onboarding` |
| 基线 | `origin/main@55e70ae1` |
| PRD | `work-logs/batch-227-ai-readiness-onboarding-prd-summary.md` |
| PM | `work-logs/batch-227-ai-readiness-onboarding-pm-plan.md` |
| Design | `work-logs/batch-227-ai-readiness-onboarding-design-spec.md` |
| 预计工时 | 5h |

## 切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 |
|---|-------|:----:|:----:|:----:|:----:|:----:|
| 1 | 版本与需求上下文 | ✅ | ✅ | ✅ | ✅ | ⏳ |
| 2 | 聚合就绪检查 | ✅ | ✅ | ✅ | ✅ | ⏳ |
| 3 | 一页式接入体验 | ✅ | ✅ | ✅ | ✅ | ⏳ |
| 4 | QA、PR、合入 | ✅ | ✅ | ✅ | 🔄 | ⏳ |

## 当前位置

`Batch 227 → Slice 4 → 等待一次总确认`。本地 QA、证据与 Leader 条件判决已完成，尚未推送远端或创建 PR。

## 风险

| 风险 | 等级 | 处理 |
|------|------|------|
| “已配置”误显示为“可用” | P1 | 只有最近真实健康态 ok 才算 AI ready |
| 页面暗示普通用户启动基础设施 | P1 | 只读状态 + 管理入口，无启动按钮 |
| B15 与 AITDE Runtime 依赖混淆 | P1 | 分开 baseline_ready / durable_ready |
| 内网 Runner 尚未接入 VersionTask 同步执行 | P2 | 明确能力边界，本批不宣称支持 |

## 批次记录

- 本地回归：后端 2407 passed；前端 616 passed；定向 41 passed；typecheck/lint/build/F821 通过。
- 浏览器：体育 16.0.0 完整需求保存、OpenAPI 导入、外部条件 fail-closed、三视口无溢出。
- 已修复：同项目同版本重复接入 500；长需求保存后移动端信息过载。
- 已修复：同版本不同需求冲突改为在 OpenAPI 访问前拒绝，不产生导入副作用。
- 已修复：C 条件审计兼容已关闭删除线 ID 与历史区间简写，恢复 0 hard / 0 warning。
- 待办：用户一次总确认 → push → Draft PR → required checks → 最终审计 → Leader APPROVED → squash merge。
