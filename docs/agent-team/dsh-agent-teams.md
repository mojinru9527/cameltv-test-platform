# DSH AgentTeams 船长手册（模式②）

> Batch 190 起 | 事实源：`.claude/skills/cameltv-agent-team/SKILL.md`（双执行模式）+ 本文档
> 适用执行器：**DeepSeek Harness**（需已安装 `@nanmicoder/dsh-agent-teams` 插件，web profile bundle）
> 与模式①（Claude Code/Codex 单会话角色扮演）产出相同工件，仅「谁来执行」不同。

## 1. 前置条件

- DeepSeek Harness Web 已安装 `@nanmicoder/dsh-agent-teams`（`dsh plugin --profile web add @nanmicoder/dsh-agent-teams`，装后重启 web 生效）。
- 会话工具集出现 `agent_teams_*` 九件套：`create / add_member / remove_member / create_task / claim_task / update_task / send_message / status / delete`。
- 团队状态持久化在 `<workspace>/.agent-teams/`；Web 面板实时展示成员/任务/依赖/消息。
- 限制：**一个船长会话同时只能带一个活跃团队**（并发批次须开不同 DSH 会话）；成员默认 `maxMembers=8`、`memberMaxDepth=1`（成员不能当船长开团队）。

## 2. 团队模型与批次模式映射

**船长 = 当前 DSH 会话，兼任 Leader**（协调、抽检、总确认交互、最终判决、合入）。

| 档位 | 成员 | 任务图 |
|------|------|--------|
| 完整批次 | 5 成员：`product` / `pm` / `design` / `dev` / `qa` | T1 PRD → T2 PM → T3 Design → T4 Dev → T5 QA → 船长判决 |
| 轻量批次 | 2 成员：`product`（PRD-lite）+ `qa` | T1' PRD-lite → T2' QA → 船长判决 |

成员是持久化 subagent：自动快照船长当前 provider/model/effort；跨轮次唤醒继续同一上下文。

## 3. 完整批次执行协议（可复制）

### 3.1 建团队 + 加成员

```
agent_teams_create("batch-{N}-{name}", "{批次目标描述：一句话，含 PRD 方向}")
agent_teams_add_member ×5:
  name=product  role=Product  （PRD 工件）
  name=pm       role=PM        （PM 计划）
  name=design   role=Design    （设计规范）
  name=dev      role=Dev       （代码+看板）
  name=qa       role=QA        （QA 报告）
```

### 3.2 建任务（带依赖）

```
agent_teams_create_task(
  subject="T1 Product: 产出 PRD",
  description="按 DEPARTMENTS.md Product 节产出 work-logs/batch-{name}-prd-summary.md；先读 C-CONDITIONS.md；含批次模式判定",
  assignee=product)
agent_teams_create_task(subject="T2 PM: 产出 PM 计划", description=..., dependencies=["T1"], assignee=pm)
agent_teams_create_task(subject="T3 Design: 产出设计规范", ..., dependencies=["T2"], assignee=design)
agent_teams_create_task(subject="T4 Dev: 代码+看板", ..., dependencies=["T3"], assignee=dev)   # 按切片可拆 T4a/T4b…，同一 dev 成员
agent_teams_create_task(subject="T5 QA: 产出 QA 报告", ..., dependencies=["T4"], assignee=qa)
```

依赖未完成的认领会被插件拒绝——流水线顺序由依赖图强制。

### 3.3 认领 + 派发（工件即交接载体）

```
agent_teams_claim_task(task_id, assignee=product)
agent_teams_send_message(to=product, content="任务 {task_id}：{完整指令 + DEPARTMENTS.md 对应节要点 + 前序工件全文}")
```

**关键规则：成员是独立上下文，看不到船长会话。** 每次派发消息必须包含：
1. 任务 id 与交付工件路径（`work-logs/batch-{name}-*.md`）
2. DEPARTMENTS.md 对应部门的角色规则与模板骨架
3. **前序工件全文**（T2 派发时附 PRD 全文；T3 附 PRD+PM 全文；依此类推）
4. 本批特有约束（C 条件、KB 检索要求、批次模式、git 门禁要点）

### 3.4 收件与状态推进

- 成员完成后 `agent_teams_update_task(task_id, status=completed, output="{工件摘要}")`。
- 船长用 `agent_teams_status` 轮询；**成员可能完成工作但漏更新任务状态**（插件已知限制）——以 `work-logs/` 工件落盘为准核对，必要时 `send_message` 补醒并要求更新状态。
- 打回/返工：`agent_teams_update_task(task_id, status=failed)` 或派发新消息给同一成员继续（同一成员上下文连续）。

### 3.5 船长收尾（Leader 职责，模式①的 Leader 工件照常）

1. 抽检各部门工件 → 写 `work-logs/batch-{name}-leader-verdict.md`（含「流程回写」小节 + 复盘卡）
2. 设定下一批 C 条件 → 同步 `C-CONDITIONS.md`
3. 向用户展示变更摘要并做**一次总确认**（推送 + Draft PR + required checks 通过后合入 main）——与模式①相同门禁
4. `agent_teams_status` 核对全部任务 completed 且输出收齐 → `agent_teams_delete` 归档团队
5. 更新看板 `work-logs/kanbans/DEV-{name}.md`

## 4. 轻量批次协议

```
agent_teams_create("batch-{N}-{name}", "...")
agent_teams_add_member ×2: product / qa
agent_teams_create_task(T1' PRD-lite, assignee=product)     # mode: light + 豁免理由
agent_teams_create_task(T2' QA 报告, dependencies=[T1'], assignee=qa)
→ 船长判决（leader-verdict 含流程回写+复盘卡）→ 总确认 → 合入 → delete 团队
```

## 5. Git 门禁（与模式①相同，执行器三选）

```
pwsh scripts/git/start-agent-team-task.ps1 -Executor DeepSeek_Harness -UserConfirmedExecutor -Kind feature -Task batch-{N}-{name} -Scope {范围} -FrontendPort {端口} -BackendPort {端口}
pwsh scripts/git/verify-ai-worktree.ps1 -RequireClean -RequireMetadata -ExpectedWorkflow agent-team -ExpectedExecutor DeepSeek_Harness
# …开发与提交（每切片 commit，总确认前不 push）…
gh pr create --draft --base main --head feature/batch-{N}-{name} ...
pwsh scripts/git/audit-ai-pr.ps1 -ExpectedWorkflow agent-team -ExpectedExecutor DeepSeek_Harness
pwsh scripts/git/audit-ai-pr.ps1 -ExpectedWorkflow agent-team -ExpectedExecutor DeepSeek_Harness -RequireSuccessfulChecks
```

也可用便捷入口 `scripts/git/start-deepseek-harness-agent-team.ps1`（同构包装，固定 `-Workflow agent-team`）。

## 6. 常见坑

| 坑 | 对策 |
|----|------|
| 成员看不到船长上下文 | 派发消息必须带前序工件全文；宁长勿短 |
| 成员完成但状态未更新 | 以工件落盘为准，补醒成员更新状态 |
| 消息过大 | 前序工件若超长，分两条消息发（先指引后全文）或让成员读文件路径（成员工作目录=worktree） |
| 一个船长只带一个团队 | 并发批次开独立 DSH 会话 |
| 忘记删团队 | 合入后立即 `agent_teams_delete`，保留历史由 Web 面板归档 |
| 双份技能漂移 | 改 `.claude/skills/cameltv-agent-team/` 后必须同步 `.agents/skills/cameltv-agent-team/`（git-ignored 工作副本）+ CHANGELOG 条目 |

## 7. 何时用模式② vs 模式①

- **用模式②（DSH 船长）**：你在 DeepSeek Harness 里开发；需要 Web 面板可视化团队状态；需要成员上下文跨轮次持久；需要任务依赖强制顺序。
- **用模式①（单会话角色扮演）**：你在 Claude Code / Codex 里开发；或团队规模超出插件限制；或需离线/无插件环境。

## 8. 关联

- SKILL.md（门禁事实源）· DEPARTMENTS.md（角色模板）· pipeline-modes.md（批次档位）· AGENTS.md（Git 门禁）
- 插件：`@nanmicoder/dsh-agent-teams`（npm；状态目录 `<workspace>/.agent-teams/`）
