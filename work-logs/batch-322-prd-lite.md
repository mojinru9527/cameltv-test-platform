# Batch 322（M7 / TA-038）— Skill 跨 Agent 验证：PRD-lite

> **mode: light** · **理由**：技能契约/清单 + 校验脚本 + 文档。
> **分支**：feature/batch-322-m7-skill-compat · **基线**：origin/main `1d0b58697`

## 范围

- `scripts/aiqe/skill-clients.json`：三客户端清单；
- `scripts/aiqe/verify-skill-compat.ps1`：6 skill 契约 + 3 客户端 + 文档校验；
- `docs/aiqe/skills.md`：三端加载方式与人工截图要求。

## 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | 6 skill 契约 | `SKILL_COMPAT=PASS ... skills=6` |
| A2 | 3 客户端清单 | `clients=3` |
| A3 | 文档存在 | skills.md |

## 非目标

- 真实三端截图（需 Claude Code/Codex/Cursor 实机，人工补充）。
