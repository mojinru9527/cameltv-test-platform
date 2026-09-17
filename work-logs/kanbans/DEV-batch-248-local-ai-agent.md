# 🗂️ Dev 部门项目看板 — batch-248-local-ai-agent

| 字段 | 值 |
|------|-----|
| **项目名称** | Batch 248 — 本地 AI Agent 闭环（平台零推理） |
| **关联 PM 计划** | [work-logs/batch-248-local-ai-agent-pm-plan.md](../batch-248-local-ai-agent-pm-plan.md) |
| **关联 PRD** | [work-logs/batch-248-local-ai-agent-prd-summary.md](../batch-248-local-ai-agent-prd-summary.md) |
| **总预估工时** | 8h |
| **已用批次** | 1 批 |
| **看板创建** | 2026-09-17 |
| **最后更新** | 2026-09-17 |

## 🎯 交付切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 0 | 工件（PRD/PM/Design/看板） | ✅ | ✅ | ✅ | ✅ | ⏳ | |
| 1 | 配置开关 + Agent token + Job 生产端/查询 + stale 回收 | ✅ | ✅ | ✅ | ✅ | ⏳ | 9 tests passed；迁移升降级通过；HARD=0 |
| 2 | 需求拆分/生成切 AiJob（禁用静默空结果） | ✅ | 🔄 ⬅️ | ⏳ | ⏳ | ⏳ | **当前位置** |
| 3 | 结果导入用例库 | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | |
| 4 | 本地 Agent CLI + 接入文档 | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | |
| 5 | 前端 AI 任务页 + AI 配置页入口 | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | |
| 6 | 测试与架构守卫 | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | |

> 状态图例：⏳ 待开始 | 🔄 进行中 | ✅ 已完成 | ❌ 已取消 | 🔒 阻塞中

## 📍 当前位置

```
Batch 248 — Slice 2（需求端点切换）
├── 已完成: Slice 0 工件；Slice 1 后端内核（ai_platform_inference/ai_job_stale_seconds、ai_agent_token 表+迁移、create/list/get_job、token 鉴权、项目隔离认领、stale 回收、model_name 落库、jobs/agent API）
├── 🔄 进行中: extract/generate 改派 AiJob
├── ⏳ 待审批: 一次总确认（推送+PR+合入）— 待 Slice 2-6 完成且 QA 首轮证据齐备
└── ⏳ 下一步: Slice 3 结果导入用例库
```

## 📜 批次记录

### Batch 248 — 本地 AI Agent 闭环 (2026-09-17)
- **产出**: （进行中）worktree `F:\CamelTv-worktrees\codex-batch-248-local-ai-agent`，分支 `feature/batch-248-local-ai-agent`，base `becbf5c6`
- **审批**: 待完成
- **耗时**: 进行中

## ⚠️ 阻塞与风险

| 阻塞项 | 严重度 | 描述 | 需要谁 | 记录时间 |
|--------|:------:|------|--------|----------|
| ~~VPN 代理中断~~ | P1 | `vpn07Core` :7688 拒绝连接导致 `git fetch` 失败，worktree 无法创建（已恢复） | 用户 | 2026-09-17 |
| 生产 AI Key 失效 | P1 | 本批落地后平台不再依赖该 Key；发布前需在生产设置 `AI_PLATFORM_INFERENCE=false` | 运维 | 2026-09-17 |

## 🔗 相关工件

| 工件 | 路径 | 状态 |
|------|------|:----:|
| PM 计划 | [batch-248-local-ai-agent-pm-plan.md](../batch-248-local-ai-agent-pm-plan.md) | ✅ |
| 设计规范 | [batch-248-local-ai-agent-design-spec.md](../batch-248-local-ai-agent-design-spec.md) | ✅ |
| QA 报告 | work-logs/batch-248-local-ai-agent-qa-report.md | ⏳ |
