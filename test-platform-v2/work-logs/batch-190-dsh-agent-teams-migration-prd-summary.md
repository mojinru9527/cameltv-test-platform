# Batch 190 — PRD-lite：六部门 Agent Team 流水线移植到 dsh-agent-teams（DSH 船长模式）

> **mode: light**（内部流程工具/纯文档类轻量批次，无新接口/新配置/新依赖）
> 豁免理由：本批全部为 Agent/Git 本地工具与技能文档改动（`.claude/skills/cameltv-agent-team/`、`docs/agent-team/`、`scripts/git/`、`AGENTS.md`），不触碰 test-platform-v2 产品代码，按 pipeline-modes.md 轻量批次三件套 + 看板执行。
> **非目标**：不新增后端接口、不改 Schema、不做数据迁移；test-platform-v2 `/dsh-tasks` 支持 AgentTeams 团队模式（子项目 B）不在本批，另行完整批次。
> 来源：用户要求（2026-08-17）——「把 agent team skill 功能移植到 dsh-agent-teams 上，后续用它在测试平台开发上」。

## 1. 问题陈述

仓库 `cameltv-agent-team` 技能定义六部门流水线（Product→PM→Design→Dev→QA→Leader），执行方式为**单会话角色扮演**（模式①）。Batch 172 起 DeepSeek Harness 已是平台执行引擎（ADR-0018），Batch 181–189 由 DSH 单会话（workflow=direct）跑完整流水线；`@nanmicoder/dsh-agent-teams@0.1.5` 插件已装入 web profile 并生效（会话出现 `agent_teams_*` 九件套）。

痛点：
1. 六部门仍由单会话依次扮演——成员无独立持久化上下文，跨轮次交接依赖手工复制，无团队状态可视化。
2. 技能/Git 脚本对 DSH 执行器支持不完整：脚本 ValidateSet 已含 `DeepSeek_Harness`（batch-173），但技能文案、AGENTS.md 仍是「Claude Code 还是 Codex」二选，无 DSH 船长执行协议。
3. `.agents/skills/`（DSH 技能发现根）与 `.claude/skills/`（版本化事实源）双副本无显式同步规则。

## 2. 成功指标

| 指标 | 目标 |
|------|------|
| 双执行模式 | SKILL.md 明确定义模式①（单会话）/模式②（DSH 船长），产出相同工件 |
| 船长协议 | `docs/agent-team/dsh-agent-teams.md` 含完整/轻量批次可复制命令序列（建团队→加成员→建任务→认领→派发→收件→判决→删团队） |
| 执行器三选 | SKILL.md / DEPARTMENTS.md / AGENTS.md / 三个 ps1 脚本文案统一「Claude Code / Codex / DeepSeek Harness」 |
| 便捷入口 | `start-deepseek-harness-agent-team.ps1` 可运行（-Workflow agent-team） |
| 双副本同步 | `.claude/skills/` 与 `.agents/skills/` 内容一致（本批已同步，手册写明规则） |
| 质量 | 改动的 3 个 ps1 语法校验通过；仓库自检门禁（本批为 docs/scripts 类，无前后端重测试） |

## 3. 用户故事 + 验收标准

- **US-1** 作为 DSH 用户，说「走 agent team」后按船长手册建团队：5 成员（完整批次）/2 成员（轻量批次），任务依赖图强制顺序。
  - 验收：Given 插件已装，When 按手册执行协议，Then `agent_teams_create/add_member/create_task/claim_task/send_message/update_task/status/delete` 全链路可用（首轮用本批自身走一次验收）。
- **US-2** 作为任意执行器用户，开工三选问题含 DeepSeek Harness 选项。
  - 验收：Given 技能/AGENTS.md/ps1 文案，When 检查，Then 三执行器枚举一致（`claude|codex|DeepSeek_Harness`）。
- **US-3** 作为流程维护者，改技能后有明确同步规则。
  - 验收：Given 手册「常见坑」表，When 读 dsh-agent-teams.md，Then 双副本同步规则与 CHANGELOG 要求可执行。

## 4. C 条件核对

- C75-1 mode:light 已记录 ✅（本文档）
- C75-3 audit-cconditions：本批未设新 C 条件 ✅
- C104-5 worktree 核验：本批全部写入位于 worktree `F:\CamelTv-worktrees\DeepSeek_Harness-batch-190-dsh-agent-teams-migration`（git status 核对）✅

## 5. 风险

| 风险 | 缓解 |
|------|------|
| 模式②与插件实际行为不符（成员上下文/消息限制） | 手册写清插件已知限制（状态漏更、单船长、maxMembers）；首轮实战验收后按流程回写修订 |
| 双副本漂移 | 手册强制同步规则；本批已同步并哈希核对 |
| 文案改三执行器影响既有 claude/codex 流程 | 仅扩展枚举与文案，脚本逻辑/ValidateSet 未动（原本就含 DeepSeek_Harness） |
