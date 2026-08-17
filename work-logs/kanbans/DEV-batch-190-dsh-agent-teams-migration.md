# DEV-batch-190-dsh-agent-teams-migration 看板

> 项目：Agent Team 工作流移植到 dsh-agent-teams（模式②船长） | 批次模式：light
> 执行器：DeepSeek_Harness（agent-team workflow）| worktree：`F:\CamelTv-worktrees\DeepSeek_Harness-batch-190-dsh-agent-teams-migration`

## 当前位置

📍 Batch 190 → Slice 1（文档+脚本改造）→ ✅编码 / 🔄QA 验收 / ⏳审批

## 任务列表

| Slice | 内容 | 状态 | 产出 |
|-------|------|------|------|
| S1 | SKILL.md 双执行模式表 + 三选执行器 | ✅ | `.claude/skills/cameltv-agent-team/SKILL.md` |
| S2 | 船长手册 docs/agent-team/dsh-agent-teams.md | ✅ | 新建文档 |
| S3 | start-deepseek-harness-agent-team.ps1 + 3 处脚本文案 | ✅ | scripts/git/ 4 文件 |
| S4 | AGENTS.md §2.3/§2.5 + local-dev-workflow.md 同步 | ✅ | AGENTS.md、docs/agent-team/local-dev-workflow.md |
| S5 | CHANGELOG + spec + .agents 副本同步 | ✅ | CHANGELOG.md、plans、.agents/skills/ |
| S5b | ADR-0014 执行器枚举同步（batch-173 支持，本批补文档） | ✅ | docs/adr/0014（4629432） |
| S5c | SKILL.md 多窗口示例/措辞补 DeepSeek Harness（两提交） | ✅ | SKILL.md（3dfabd4、f4fccdb） |
| S6 | 轻量批次工件（PRD-lite/QA/Leader/看板） | 🔄 | test-platform-v2/work-logs/ |
| S7 | 模式②全链路实战验收（AgentTeams 团队演练） | 🔄 | 团队 batch-190-dsh-agent-teams-migration |

## 验收记录

- [x] 4 个 ps1 语法校验通过（PowerShell AST Parser）
- [x] `start-agent-team-task.ps1 -Executor DeepSeek_Harness` 实际创建 worktree 成功（本批自身即运行时验证）
- [x] AgentTeams 依赖强制：t2 依赖 t1 未完成时认领被拒绝
- [x] Product 成员抽检 PRD-lite（t1）：有条件通过，唯一 P2 = C75-3 audit 证据（已实测：EXIT=1，11 个历史孤儿条件，本批未新增）
- [ ] QA 成员门禁核对（t2，已派发含 C75-3 证据）
- [ ] Leader 判决 + 一次总确认（推送+PR+合入）

## 批次记录

- 产出：SKILL.md 双模式、dsh-agent-teams.md 手册、start-deepseek-harness-agent-team.ps1、三执行器文案统一、AGENTS.md 同步、工件 ×4
- 审批：等待用户一次总确认
- 耗时：TBD（复盘卡填）
