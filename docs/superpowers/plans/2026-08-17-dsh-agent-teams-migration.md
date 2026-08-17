# 子项目 A 设计：六部门 Agent Team 流水线移植到 dsh-agent-teams

> 日期：2026-08-17 | 状态：设计已批准（方案 A1） | 批次模式：轻量批次（docs/skills/scripts 类改动）

## 1. 背景与目标

CamelTv 仓库的 `cameltv-agent-team` 技能（`.claude/skills/cameltv-agent-team/`）定义了六部门流水线
（Product→PM→Design→Dev→QA→Leader），当前执行方式是**工件驱动的手动流水**：单个会话依次扮演六部门、
逐份写出 `work-logs/` 工件。Batch 181 起实际由 DeepSeek Harness 单会话（workflow=direct，
executor=DeepSeek_Harness）跑完整个流水线。

DeepSeek Harness 已安装 `@nanmicoder/dsh-agent-teams@0.1.5`（web profile bundle，已生效），提供
`agent_teams_*` 九件套：创建团队、添加持久化成员、创建带依赖的任务、认领/派发、邮箱直连消息、状态快照、
删除团队；Web 面板实时展示；团队状态落在 `<workspace>/.agent-teams/`。

**目标**：把六部门流水线从「单会话角色扮演」升级为「DSH 船长 + 持久化成员智能体」执行模式——
六部门映射为成员、流水线映射为带依赖的任务图、工件规范原样保留；同时让仓库 Git 门禁正式支持
DeepSeek Harness 作为 Agent Team 执行器。

**范围**：仅子项目 A（开发工作流移植）。子项目 B（test-platform-v2 `/dsh-tasks` 支持 AgentTeams
团队模式）另行设计，作为完整批次用 A 的新工作流开发（自举）。

## 2. 现状盘点（探索结论）

| 项 | 现状 |
|----|------|
| 技能本体 | `.claude/skills/cameltv-agent-team/`（SKILL.md + DEPARTMENTS.md + CHANGELOG.md）仓库版本化；`.agents/skills/cameltv-agent-team/` 内容相同、git-ignored（.gitignore:97），DSH 从该目录发现技能 |
| 执行方式 | SKILL.md 明确「工件驱动的手动流水」；Batch 181–189 由 DSH 单会话（direct）执行，工件标记 `执行：DeepSeek_Harness（direct）` |
| Git 脚本 | batch-173 起已支持 `DeepSeek_Harness` 执行器：`start-agent-team-task.ps1` ValidateSet 含它；`new-ai-worktree.ps1`/`verify-ai-worktree.ps1` 仅阻止 agent-team+human 组合，**DeepSeek_Harness + agent-team 已放行**；`start-deepseek-harness-task.ps1` 为 direct 入口 |
| 文案滞后 | `start-agent-team-task.ps1` 报错文案与 AGENTS.md §2.3、SKILL.md「标准流程」仍写「Claude Code 还是 Codex」二选问题 |
| 插件 | `@nanmicoder/dsh-agent-teams@0.1.5` 已装并生效；默认 `maxMembers=8`、`memberMaxDepth=1`（成员不能当船长） |

## 3. 方案选型（A1 已批准）

| 方案 | 做法 | 结论 |
|------|------|------|
| **A1 仓库技能原生演进** | 改造 SKILL.md 为「双执行模式」：模式①单会话角色扮演（保留，Claude Code/Codex 用）；模式②DSH AgentTeams 船长模式（新增）。DEPARTMENTS.md 模板不动（工件事实源）。新增 `docs/agent-team/dsh-agent-teams.md` 船长手册 | ✅ 选定：单一事实源、仓库版本化、两客户端可用 |
| A2 独立 DSH 技能 | 另写 `.agents/skills/cameltv-agent-team-dsh/` | 双份技能易漂移、双 CHANGELOG |
| A3 纯文档不进技能 | 只写 docs 手册 | 无技能发现/无门禁触发，易被跳过 |

## 4. 船长模式执行协议

### 4.1 团队模型：船长 = Leader，五成员

- **船长**（当前 DSH 会话）：协调、抽检、总确认交互、最终判决（leader-verdict）、合入。
- **成员**（完整批次 5 个）：`product` / `pm` / `design` / `dev` / `qa`。
- **轻量批次 2 个**：`product`（PRD-lite）+ `qa`（QA 报告），判决由船长出。
- 成员为持久化 subagent：快照船长当前 provider/model/effort，无独立 prompt；跨轮次唤醒。

### 4.2 任务依赖图（完整批次）

```
T1 Product → batch-{name}-prd-summary.md      （无依赖）
T2 PM      → batch-{name}-pm-plan.md          （依赖 T1）
T3 Design  → batch-{name}-design-spec.md      （依赖 T2）
T4 Dev     → 代码 + kanbans/DEV-{name}.md      （依赖 T3；按切片可拆 T4a/T4b…，同一 dev 成员）
T5 QA      → batch-{name}-qa-report.md        （依赖 T4）
→ 船长（Leader）：抽检 + batch-{name}-leader-verdict.md + 流程回写 + 复盘卡 → 合入
```

轻量批次：`T1' PRD-lite（product）→ T2' QA（qa）→ 船长判决`。

### 4.3 派发协议

1. `agent_teams_create(name, description)` 建团队，description 写批次目标。
2. `agent_teams_add_member` ×N 加成员。
3. `agent_teams_create_task` 建任务并声明依赖（assignee 指向成员）。
4. `agent_teams_claim_task` 认领（依赖完成才可认领，由插件强制）。
5. `agent_teams_send_message(to=成员)` 唤醒：消息含任务 id + **前序工件全文** + DEPARTMENTS.md 对应节指引。
   **工件即交接载体**——成员是独立上下文，前序产出必须随消息完整传递。
6. `agent_teams_status` 轮询；成员 `agent_teams_update_task` 标记完成并写 output 摘要。
7. 全部完成后船长写 leader-verdict → `agent_teams_delete` 归档团队。

### 4.4 与现有流程的衔接

- 第 0 步读看板、批次模式判定（完整/轻量）、C 条件、KB 检索、复盘卡、流程回写——**全部保留**，规则来源不变（SKILL.md / DEPARTMENTS.md / docs/agent-team/）。
- 总确认（推送+PR+合入）与逐次 push 门禁不变；船长负责与用户交互。
- 单会话角色扮演模式（模式①）保留，未使用 AgentTeams 的客户端（Claude Code/Codex）不受影响。

## 5. Git 门禁适配（小改）

| 文件 | 改动 |
|------|------|
| `scripts/git/start-agent-team-task.ps1` | 报错文案三选：「Claude Code / Codex / DeepSeek Harness」（ValidateSet 已含，逻辑不动） |
| `scripts/git/new-ai-worktree.ps1` | 报错文案同步（仅 human 被拒，逻辑不动） |
| `scripts/git/verify-ai-worktree.ps1` | 报错文案同步（同上） |
| `scripts/git/start-deepseek-harness-agent-team.ps1` | 新增：与 start-deepseek-harness-task.ps1 同构，`-Workflow agent-team` 包装 |
| `AGENTS.md` §2.3 | 三选问题同步；Agent Team 流程说明补充 DSH 执行器 |
| `.claude/skills/cameltv-agent-team/SKILL.md` | 「Git 工作流」节三选问题同步 + 新增「DSH AgentTeams 船长模式」节 |

## 6. 船长手册（新增 `docs/agent-team/dsh-agent-teams.md`）

内容：
- 插件前置（已装、工具九件套、Web 面板、状态目录 `.agent-teams/`）
- 团队模型与批次模式映射表
- 逐步执行协议（4.3 展开成可复制命令序列）
- 成员上下文隔离注意事项（工件全文传递、消息大小、重试）
- 常见坑：成员未更新任务状态、团队删除前先收齐输出、单船长限制
- 与模式①的对照表（何时用哪个）

## 7. 文件清单

**新增**
- `docs/agent-team/dsh-agent-teams.md`（船长手册）
- `scripts/git/start-deepseek-harness-agent-team.ps1`
- `docs/superpowers/plans/2026-08-17-dsh-agent-teams-migration.md`（本文档）

**修改**
- `.claude/skills/cameltv-agent-team/SKILL.md`（双执行模式 + 三选问题）
- `.claude/skills/cameltv-agent-team/CHANGELOG.md`（追加条目）
- `.agents/skills/cameltv-agent-team/SKILL.md` + `CHANGELOG.md`（git-ignored 副本同步）
- `scripts/git/start-agent-team-task.ps1`（文案）
- `scripts/git/new-ai-worktree.ps1`（文案）
- `scripts/git/verify-ai-worktree.ps1`（文案）
- `AGENTS.md`（§2.3 同步）

**不动**
- `DEPARTMENTS.md`（模板事实源）
- `docs/agent-team/pipeline-modes.md`、retro-card-template.md、release-cadence.md 等
- test-platform-v2 产品代码（子项目 B）

## 8. 同步与版本化规则

- 技能事实源 = `.claude/skills/cameltv-agent-team/`（仓库版本化）；`.agents/skills/cameltv-agent-team/`（git-ignored）为 DSH 工作副本，**改技能必须双份同步**（写入船长手册）。
- 按 Batch 75 规则：改 SKILL.md 必须同批提交 CHANGELOG 条目。
- 本次 A 按轻量批次执行：PRD-lite + QA + Leader 三件 + 看板。

## 9. 风险与边界

| 风险 | 缓解 |
|------|------|
| 成员独立上下文丢失前序信息 | 派发消息必须附前序工件全文；队长在 status 核对 output |
| 成员完成工作但未更新任务状态（插件已知限制） | 船长以工件落盘为准核对，必要时 send_message 补醒 |
| 双份技能漂移 | 手册强制双份同步规则；同步脚本可选后续加 |
| SKILL.md 变长 | 模式②细节放船长手册，SKILL.md 只放协议摘要与指针 |
| 单船长限制（一个会话同时只带一个团队） | 手册写明：并发批次需不同 DSH 会话 |

## 10. 子项目 B 预告（不在此次范围）

test-platform-v2 `/dsh-tasks`（ADR-0018，`services/dsh/dsh_runner.run_dsh_task`）增加「团队模式」：
提交自然语言目标 → DSH 以船长+成员方式执行 → 平台追踪团队状态/成员/任务进度。属完整产品批次，
用 A 的新船长工作流开发（自举验证）。
