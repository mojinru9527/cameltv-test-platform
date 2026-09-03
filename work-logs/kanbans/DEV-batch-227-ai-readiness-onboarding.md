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
| 1 | 版本与需求上下文 | ✅ | 🔄 | ⏳ | ⏳ | ⏳ |
| 2 | 聚合就绪检查 | ✅ | ⏳ | ⏳ | ⏳ | ⏳ |
| 3 | 一页式接入体验 | ✅ | ⏳ | ⏳ | ⏳ | ⏳ |
| 4 | QA、PR、合入 | ✅ | ⏳ | ⏳ | ⏳ | ⏳ |

## 当前位置

`Batch 227 → Slice 1 → 编写失败测试`。上一批 Batch 226 已合入；本批已从最新 main 建立并验证独立 worktree。

## 风险

| 风险 | 等级 | 处理 |
|------|------|------|
| “已配置”误显示为“可用” | P1 | 只有最近真实健康态 ok 才算 AI ready |
| 页面暗示普通用户启动基础设施 | P1 | 只读状态 + 管理入口，无启动按钮 |
| B15 与 AITDE Runtime 依赖混淆 | P1 | 分开 baseline_ready / durable_ready |
| 内网 Runner 尚未接入 VersionTask 同步执行 | P2 | 明确能力边界，本批不宣称支持 |
