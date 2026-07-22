---
title: "Batch 33 Agent Git 自动审计 QA 报告"
owner: "qa"
last_reviewed: "2026-07-22"
status: "in_progress"
tags: ["qa", "git", "automation"]
---

# 当前证据

| 检查 | 结果 |
|---|---|
| 固定 Claude 入口红测 | PASS：入口不存在时按预期失败 |
| Owner/metadata 入口实现 | PASS：owner=claude；ExpectedOwner=codex 被拒绝 |
| metadata 篡改红测 | PASS：旧 hook 未阻断，准确复现缺口 |
| 加固 hook 自测 | PASS：合法 push/恢复后 push/删除通过；metadata 篡改/main push 拒绝 |
| PowerShell parser | PASS |
| Workflow YAML parser | PASS |
| PR 前负向审计 | PASS：脏/未提交状态被拒绝 |
| 三类固定入口 | PASS：Claude/Codex/Agent Team 分别写入固定 owner |
| Guardrail 安装 | PASS：仓库级 `core.autocrlf=false` |
| Git 自带 sh 语法 | PASS：pre-push 无语法错误 |
| 差异范围 | PASS：0 个意外 tracked 文件；未出现历史文件批量行尾 diff |
| `git diff --check` | PASS |

# 待完成

- 真实 Draft PR 基础审计与 checks 负向/正向审计。
- GitHub `AI/Git 交付策略` 和既有全量门禁。
- main ruleset 第三 required context 与 squash 合并验证。
