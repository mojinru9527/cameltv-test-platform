---
title: "Batch 36 CI 按变更范围分层 Leader 判决"
owner: "leader"
last_reviewed: "2026-07-23"
status: "approved"
tags: ["leader", "ci", "github-actions"]
---

# 当前判决

`APPROVED`，但仅在本文件所在证据提交满足以下条件后生效：

1. PR #61 的三项 required checks 与全部扩展检查再次为 `COMPLETED/SUCCESS`；
2. `audit-ai-pr.ps1 -ExpectedWorkflow agent-team -ExpectedExecutor codex -RequireSuccessfulChecks` 通过；
3. PR 保持 `MergeState=CLEAN`，由 Draft 标记为 Ready 后仅以 squash 合入 `main`；
4. 合并后确认远端任务分支删除、控制仓库同步至合并后的 `main`；
5. 任一条件不满足，本判决自动退回 `PENDING`。

# 抽检重点

- 顶层 path filter 不能导致 required workflow 消失。
- detector 失败不能因 dependent job 被 skipped 而假绿。
- 未识别路径必须双端执行，不能用维护成本换取漏测风险。
- PR #61 首轮 11/11 SUCCESS；workflow 变更正确走双端全量，两个 required 汇总均实际验证。
- 用户已在首轮全绿与 pending 负测后确认执行器仍为 Codex，并明确授权最终审计、Ready、squash 与安全清理。

# 知识审计

- CI 范围矩阵、完整 PR diff 防绕过、required 汇总 fail-closed 规则已写入 ADR-0014、AGENTS.md、Agent Team skill 与分类器契约测试。
- 本批次不修改平台业务代码，不新增或改变平台功能 C 条件。
- 当前环境没有可调用的知识入库工具；治理知识已在仓库事实源持久化，不以外部 RAG 写入阻断交付。
