---
title: "Batch 35 Agent Team 双确认门禁 QA 报告"
owner: "qa"
last_reviewed: "2026-07-22"
status: "needs_work"
tags: ["qa", "agent-team", "git", "confirmation"]
---

# 当前判决

`NEEDS_WORK`。需求、实现与本地验证已通过；真实 Draft PR、首轮远端门禁和用户第二次确认尚未完成。

# 验收矩阵

| 条件 | 状态 | 证据 |
|---|---|---|
| 用户开始确认 Codex | ✅ | 当前对话，2026-07-22 |
| 缺少开始确认拒绝且零副作用 | ✅ | 自测确认目录和分支均未创建 |
| schema v3 开始 confirmed / 完成 pending | ✅ | Claude/Codex 双执行器正例与 Batch 35 自身元数据 |
| 结束确认缺失、错配、脏工作区拒绝 | ✅ | 三类负向用例全部通过 |
| 正确结束确认与严格验证 | ✅ | 临时仓库 completion confirmed 后严格验证通过 |
| schema v1/v2 兼容且不能绕过最终门禁 | ✅ | direct v2、Agent Team v2、owner-only v1 用例通过 |
| Draft PR 首轮 CI 可执行 | ⏳ | 待真实 PR |
| pending 阻断最终审计 | ⏳ | 待真实 PR |
| 用户结束确认 | ⛔ | 必须在首轮 CI 后问询并等待 |

# 保护声明

Batch 35 仅修改 Git/Agent Team 治理文件；不修改测试平台业务代码。原 `F:\CamelTv` 工作区及既有安全备份保持不动。

# 本地执行证据

| 检查 | 结果 |
|---|---|
| TDD 红测 | PASS：旧实现因缺少完成确认入口按预期失败 |
| PowerShell parser | PASS：全部变更脚本（含新完成确认入口）无语法错误 |
| `test-ai-worktree-tools.ps1` | PASS：双执行器、双确认、v1/v2 兼容、push 保护全覆盖 |
| Batch 35 元数据 | PASS：schema=3、workflow=agent-team、executor=codex、start=confirmed、completion=pending |
| pending 严格校验 | PASS：`-RequireCompletionConfirmation` 按预期拒绝 |
| pre-push / workflow YAML | PASS |
| `git diff --check` | PASS |
| 文档保鲜 `--ci` | PASS：0 过期、0 警告；既有 NO-FM 为非阻断提示 |
