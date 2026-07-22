---
title: "Batch 33 Agent Git 自动审计 PRD"
owner: "product"
last_reviewed: "2026-07-22"
status: "approved"
tags: ["agent-team", "git", "automation"]
---

# 问题

现有规范能隔离 worktree 和保护 `main`，但 owner 依赖手填，pre-push 不验证 metadata，Agent Team 缺少统一 PR 审计命令，Windows 行尾还可能制造假脏状态。

# 成功标准

1. Claude、Codex、Agent Team 使用不同固定入口，调用者不能覆盖 owner。
2. 非法 owner/branch/base/目录/scope/端口或脏工作区在 push 前被阻断。
3. Agent Team 能用一个命令确认 PR 的本地/远端 SHA、base/head、scope、required checks 和 squash-only 策略。
4. GitHub 独立策略 job 阻断非法分支、本地文件和常见凭据夹带，并加入 main required checks。
5. `.gitattributes` 消除 Windows 行尾假脏状态且不产生无关代码差异。

# 非目标

- 不尝试通过进程名、窗口标题或私有环境变量识别 AI。
- 不修改测试平台业务功能或生产配置。
- 不用 owner 声明替代 GitHub 身份、代码审查或 required checks。
