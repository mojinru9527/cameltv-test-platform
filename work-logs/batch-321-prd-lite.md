# Batch 321（M7 / TA-037）— AGENTS.md 规整：PRD-lite

> **mode: light** · **理由**：仓库级文档 + 校验脚本。
> **分支**：feature/batch-321-m7-agents-md · **基线**：origin/main `9400c2474`

## 范围

- `AGENTS.md` 新增「5.5 AIQE 专项规范」：入口文档、批次门禁、MCP/Skill 使用；
- `scripts/ci/check-agents-md.ps1` 校验关键章节/链接；
- Codex 新 session 可据此找到规格/ops/rollback/MCP/Skills。

## 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | AIQE 章节 | `AGENTS_GUARD=PASS` |
| A2 | 入口链接齐全 | 同上 |
| A3 | 门禁命令可执行 | ops/rollback 文档已有 |
