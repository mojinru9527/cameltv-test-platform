# Batch 313（M5 / TA-032.5）— Agent Skills 开放标准封装：PRD-lite

> **mode: light** · **理由**：Skill 文档 + 校验脚本（无运行时/迁移）。
> **分支**：feature/batch-313-m5-agent-skills · **基线**：origin/main `b87c90939`

## 范围

6 个 skill（`.claude/skills/<agent>/SKILL.md`）：

| skill | Agent |
|-------|-------|
| a0-requirement | A0 需求评估 |
| a2-test-design | A2 测试设计/评审 |
| a3-workflow-planner | A3 工作流规划 |
| a4-failure-triage | A4 失败归因 |
| a5-change-impact | A5 变更影响 |
| a6-learning-curator | A6 学习策展 |

统一契约：frontmatter `name/description` + `## 输入` / `## 输出` / `## 安全边界`；
`scripts/ci/check-aiqe-skills.ps1` 校验并接入 `ai-delivery-policy`。

## 验收

| # | 标准 | 证据 |
|---|------|------|
| A1 | 6 个 skill 齐备且契约一致 | `check-aiqe-skills.ps1` → PASS |
| A2 | CI 接入 | workflow 新步骤 |
| A3 | 安全边界写明 | 每个 skill `## 安全边界` |

## 非目标

- 三处（Claude Code/Codex/Cursor）真机加载截图（需外部客户端，人工验收）。
