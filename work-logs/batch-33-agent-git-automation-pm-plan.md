---
title: "Batch 33 Agent Git 自动审计 PM 计划"
owner: "pm"
last_reviewed: "2026-07-22"
status: "active"
tags: ["agent-team", "git"]
---

# 交付切片

| Slice | 内容 | 验收 |
|---|---|---|
| 1 | 固定 AI 入口与 metadata 强校验 | Claude 入口写入 claude；ExpectedOwner 错误被拒绝 |
| 2 | pre-push 自动验证 | 合法 push/删除通过；metadata 篡改/main push 被拒绝 |
| 3 | PR 审计 | PR 前失败、Draft 基础审计通过、checks 未全绿时最终审计失败 |
| 4 | Actions 与行尾 | 策略 workflow 通过；属性固定 LF；无大规模无关 diff |
| 5 | 真实 PR/ruleset | 三项 required checks 通过后仅 squash 合入并自动删分支 |

依赖顺序：1 → 2 → 3/4 → 5。所有代码仅在 `feature/batch-33-agent-git-automation` worktree 修改。
