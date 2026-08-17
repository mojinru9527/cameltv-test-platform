# Batch 190 — Leader 判决：六部门 Agent Team 流水线移植到 dsh-agent-teams（DSH 船长模式）

> **Leader (🎯)** | Date: 2026-08-17 | Decision: **APPROVED**（QA 有条件通过已闭环，P3 遗留两项已在本批顺手修复）

## 评审摘要

| 维度 | 评分 | 备注 |
|------|------|------|
| 实现质量 | 高 | 双模式结构完整：SKILL.md 模式表 + 船长手册 123 行 + 便捷入口脚本；三执行器枚举全仓库一致（QA 复验 5 脚本 AST + 文档 6 处） |
| 风险 | 低 | 仅 docs/skills/scripts 改动；脚本逻辑未动（ValidateSet 原本已含 DeepSeek_Harness，batch-173） |
| 覆盖 | 高 | Product 成员抽检（t1）：有条件通过；QA 成员门禁核对（t2）：PASS，C75-3 闭环，P0/P1/P2=0 |

## 关键决策（已批准）

1. **模式②船长 = Leader**：DSH 会话兼任 Leader（协调/抽检/总确认/判决/合入），五成员 product/pm/design/dev/qa（完整批次）、两成员（轻量批次）——用户 2026-08-17 选定，写入 spec。
2. **工件规范不动**：DEPARTMENTS.md 模板本体保留为唯一模板事实源，仅 Dev 节执行器二选改三选；两种模式产出相同工件。
3. **脚本层零逻辑改动**：三处 ps1 仅文案三执行器化；`start-deepseek-harness-agent-team.ps1` 为同构包装。

## 抽检通过（本批实测证据）

- ✅ 4 个 ps1 PowerShell AST 语法解析通过（start-agent-team-task / new-ai-worktree / verify-ai-worktree / start-deepseek-harness-agent-team；QA 复验另含 audit-ai-pr 共 5 个）
- ✅ 执行器枚举一致性：脚本 ValidateSet（4 处）+ 新增入口固定值 + SKILL.md/DEPARTMENTS.md（Dev 节 + Leader 节示例）/AGENTS.md/local-dev-workflow.md/ADR-0014 全部三执行器（QA 报告专项核验 §2）
- ✅ 双副本一致性：.claude/.agents 的 SKILL.md/DEPARTMENTS.md/CHANGELOG.md SHA256 全部 MATCH（QA 复验 §3）
- ✅ 运行时验证：`start-agent-team-task.ps1 -Executor DeepSeek_Harness` 实际创建 worktree 成功（本批自身）；AgentTeams 依赖强制（t2 依赖 t1 未完成时认领被拒）
- ✅ AgentTeams 协议实战：建团队→加成员（product/qa）→建任务（t1/t2 依赖）→认领→派发→t1/t2 完成→output 收齐→工件落盘（QA 报告 114 行）
- ✅ audit-cconditions.ps1 -RequireLatestBatch：EXIT=1，11 个 hard error 均为历史孤儿条件（船长 + QA 两次实测一致）——**本批未新增 C 条件**，C-CONDITIONS.md 未改动，判定为已知基线失败
- ✅ QA 结论（t2）：PASS（有条件通过），C75-3 闭环，P0/P1/P2=0；P3×2 建议（DEPARTMENTS.md:220 示例、local-dev-workflow 速查表）**已在本批顺手修复**（前者本轮，后者 c832afc）；P3×1 观察（confirm-agent-team-completion.ps1 可选脚本，下批按需）
- ✅ 新入口冒烟（QA G3）：`start-deepseek-harness-agent-team.ps1` 非法 task 名被正确拒绝、参数正确转发、无副作用

## 判决

**APPROVED**。QA 有条件通过已闭环（C75-3 audit 证据、P3-1/P3-2 修复），无 P0/P1/P2 缺陷。
合入指令：待用户一次总确认（推送 feature/batch-190-dsh-agent-teams-migration + 创建 Draft PR + required checks 通过后合入 main）后执行；合入前跑 `audit-ai-pr.ps1 -ExpectedWorkflow agent-team -ExpectedExecutor DeepSeek_Harness` 基础审计，checks 全绿后 `-RequireSuccessfulChecks` 最终审计，随后 squash 合入并清理 worktree。

## 下一批次 Leader 条件（如有）

- 无（本批不设新 C 条件）

## 流程回写（Batch 75 起强制）

| 发现 | 处理 | 落点 |
|------|------|------|
| `core.hooksPath` 未配置：`.githooks/pre-push` 存在（batch-33 引入）但 install-git-guardrails.ps1 未被当前环境执行，推送时 pre-push 不会自动触发 | 本批推送前手动运行 verify-ai-worktree.ps1 作为替代门禁；建议后续批次运行 `install-git-guardrails.ps1` 修复 | 本判决 + docs/agent-team/local-dev-workflow.md「常见坑速查」（c832afc） |
| 三执行器文案此前滞后于脚本（batch-173 已支持 DeepSeek_Harness，文档仍是二选） | 本批统一为三选 | SKILL.md/DEPARTMENTS.md/AGENTS.md/ADR-0014/local-dev-workflow.md |

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 轻量批次 1 轮 vs 实际 1 轮 | 0/0/0/3（P3-1/P3-2 已修，P3-3 观察） | 0 | 工具链 | 三执行器化改造合入前跑一次全仓库 grep `claude\|codex` 残留核对（含速查表/Leader 节示例/可选脚本）；C75-3 类基线失败在 QA 报告如实记录命令+退出码+失败集合 |

**技能使用**: AgentTeams 插件（agent_teams_* 九件套实战）；DEPARTMENTS.md 模板；audit-cconditions.ps1 / audit-ai-pr.ps1 / verify-ai-worktree.ps1
