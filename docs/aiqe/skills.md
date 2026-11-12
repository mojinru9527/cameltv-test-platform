# AIQE Skills 跨 Agent 验证

## 目标

同一份 `SKILL.md` 被 Claude Code / Codex / Cursor 加载，行为一致；写动作仍受 MCP 审批门禁。

## 本地校验

```powershell
pwsh scripts/aiqe/verify-skill-compat.ps1 -RepositoryPath .
```

输出：`SKILL_COMPAT=PASS clients=3 skills=6`。

## 三端加载

| 客户端 | 加载方式 | 验证点 |
|--------|----------|--------|
| Claude Code | 仓库根 `.claude/skills/` 自动发现 | skill 出现在列表，契约一致 |
| Codex | 通过 `AGENTS.md` 引用 + `codex mcp` 连接 `aiqe_mcp` | 读取同一 skill，写操作需 token |
| Cursor | `.claude/skills` 引用或 MCP 注册 | 引用同一 Skill 文件 |

## 验收证据（人工）

1. 三端分别加载 `a4-failure-triage`；
2. 输入同一失败样本，均输出“草案 + 证据 + 不自动关缺陷”；
3. 截图/录屏存 `work-logs/aiqe/skill-compat/`（由执行人补充）。

> 三端截图需真实客户端环境；本仓库提供可自动化的契约/目录校验与 MCP stdio 冒烟。
