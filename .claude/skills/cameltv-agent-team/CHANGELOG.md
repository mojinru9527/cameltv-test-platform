# cameltv-agent-team 技能变更日志

> 技能版本化唯一日志。凡修改 `SKILL.md` / `DEPARTMENTS.md` 必须在本文件追加一条。格式：日期 | 批次 | 变更摘要 | 动因。

## 2026-08-17 | Batch 190 | DSH AgentTeams 船长模式（执行方式双模式化）

- **变更**：SKILL.md「流水线」节新增执行模式表（模式①单会话角色扮演保留；模式②DSH AgentTeams 船长模式：船长=Leader、五成员 product/pm/design/dev/qa、带依赖任务图）；Git 工作流与 DEPARTMENTS.md Dev 节的执行器三选问题同步为「Claude Code / Codex / DeepSeek Harness」；多窗口并行示例与措辞补第三执行器；新增 `docs/agent-team/dsh-agent-teams.md` 船长手册（完整/轻量批次协议、工件交接规则、常见坑、双模式选用）；新增 `scripts/git/start-deepseek-harness-agent-team.ps1` 便捷入口；start-agent-team-task.ps1 / new-ai-worktree.ps1 / verify-ai-worktree.ps1 报错文案同步三执行器；AGENTS.md §2.3/§2.5、local-dev-workflow.md、ADR-0014 同步。DEPARTMENTS.md 模板本体不变（工件事实源）。
- **动因**：DeepSeek Harness 已装 `@nanmicoder/dsh-agent-teams` 插件（batch-172 起 DSH 已是平台执行引擎），用户要求把六部门流水线从单会话角色扮演移植为 DSH 船长+持久化成员执行，用于后续测试平台开发；脚本层 batch-173 已支持 DeepSeek_Harness 执行器，本次补齐技能/文档/文案。

## 2026-08-07 | Batch 115 | 批次合并与发布节奏

- **变更**：SKILL.md 新增「批次合并与发布节奏」节（同域小修复归并轻量批次、纯文档/证据合并提交、合代码 ≠ 发版本）；新增事实源 `docs/agent-team/release-cadence.md` 并加入 SKILL.md 关联；AGENTS.md §2.6 新增发布节奏小节、§4 CI 门禁说明同步（push→main 改为合并冒烟、pr-check 改每日定时观察、CI 工作流/deploy 不再触发双端全量）；deploy/CLAUDE.md、docs/testing-strategy.md、pipeline-modes.md、local-dev-workflow.md 同步。
- **动因**：用户反馈 PR 校验规则过严、校验时间长、版本发布过频影响开发节奏；主干随时合并、版本按窗口聚合，减少每 PR 检查项与每次合并的 CI 开销。
## 2026-08-04 | Batch 83 | 新增本地开发操作备忘

- **变更**：新增 `docs/agent-team/local-dev-workflow.md`（主干视图 / worktree 隔离 / 批次生命周期 / push 门禁 / 常见坑速查）；SKILL.md「关联」节新增该文档链接。
- **动因**：用户要求把本地开发工作流固化为 Agent Team 常驻资产；此前 F:\CamelTv 曾停在旧分支导致"pull 不切分支、脚本缺失"等困扰（batch-82 实测）。

## 2026-08-07 | Batch 115 | 批次合并与发布节奏

- **变更**：SKILL.md 新增「批次合并与发布节奏」节（同域小修复归并轻量批次、纯文档/证据合并提交、合代码 ≠ 发版本）；新增事实源 `docs/agent-team/release-cadence.md` 并加入 SKILL.md 关联；AGENTS.md §2.6 新增发布节奏小节、§4 CI 门禁说明同步（push→main 改为合并冒烟、pr-check 改每日定时观察、CI 工作流/deploy 不再触发双端全量）；deploy/CLAUDE.md、docs/testing-strategy.md、pipeline-modes.md、local-dev-workflow.md 同步。
- **动因**：用户反馈 PR 校验规则过严、校验时间长、版本发布过频影响开发节奏；主干随时合并、版本按窗口聚合，减少每 PR 检查项与每次合并的 CI 开销。
## 2026-08-04 | Batch 83 | Agent Team 确认门禁收敛为一次总确认

- **变更**：SKILL.md/DEPARTMENTS.md/AGENTS.md/pipeline-modes.md 将「逐次 push 确认 + 二次完成确认」收敛为一次总确认（推送+创建 Draft PR+required checks 通过后合入 main）；`audit-ai-pr.ps1` 最终审计不再强制完成确认；本地开发操作备忘同步更新。
- **动因**：用户要求减少重复确认；推送/PR/合入属于同一次交付授权，一次明确答复即可；直接任务仍保留逐次 Push 确认（AGENTS.md §2.4）。

## 2026-08-04 | Batch 76 | Dev 步骤接入自动避坑扫描

- **变更**：SKILL.md Dev 步骤新增「自动避坑扫描」（提交前运行 `scan-common-bugs.ps1`，HARD>0 必须处理或注明豁免）；`cameltv-bug-guard` 关联新增该工具。
- **动因**：避坑清单从"读"升级为"机器拦截"；真实仓库首扫即发现 67 处 HARD（含 Batch 37 P0-01 `R.err` 7 处、P0-02 密码 print）。

## 2026-08-04 | Batch 75 | 双档流水线 + 自我进化 + 复盘卡 + 验收证据库

- **变更**：SKILL.md 增加「批次模式（完整/轻量）」「自我进化（流程回写 + CHANGELOG 强制）」「复盘卡」「验收证据库」四节；DEPARTMENTS.md 重构 Leader 模板为独立第 6 节、QA/Leader 模板加入复盘卡、Product 模板加入技能使用行与轻量批次判定。
- **动因**：审计发现 Batch 54–61 工件不完整且无豁免记录；SKILL.md 自 Batch 36/37 后 10 天无更新；无量化复盘指标；验收证据重复劳动。

## 2026-07-23 | Batch 36 | CI 范围门禁

- **变更**：SKILL.md 增加 CI 分层核对规则（完整 base/head diff 分类，未知/CI/部署必须双端全量）。
- **动因**：文档/工具类提交被误触发全量回归。

## 2026-07-23 | Batch 35 | 双用户确认

- **变更**：增加执行器双确认状态机（开工确认 + 完成确认）。
- **动因**：无法从客户端/进程推断实际执行器，防止身份伪造。

## 2026-07-22 | Batch 34 | 执行器身份模型

- **变更**：Agent Team 与 Executor 分离；文档不再把 Agent Team 当作实际 AI。
- **动因**：工作流与实际宿主混淆导致审计失败。

## 2026-07-22 | Batch 33 | AI Git 交付审计自动化

- **变更**：引入 `audit-ai-pr.ps1` / `verify-ai-worktree.ps1` 等脚本化门禁。
- **动因**：人工审计不可扩展，PR 门禁需要可执行校验。

## 2026-07-22 | Batch 31/32 | 单一 main 主干迁移

- **变更**：develop/main 双主干迁移为单一 main；新增多窗口 worktree 隔离与防冲突规则。
- **动因**：双主干导致文件丢失与合并回退（如 C-CONDITIONS 被覆盖）。

## 2026-07-22 | Batch 28 | C 条件追踪闭环

- **变更**：Leader 设定的 C 条件必须同步写入 `C-CONDITIONS.md`；Product 开工必须先读条件并在 PRD 中纳入或豁免。
- **动因**：26 个孤儿 C 条件无人跟踪。

## 2026-07-21 | Batch 26 | Agent Team RAG 集成

- **变更**：新增「KB 自动检索（RAG）」章节；部门执行前按模块检索历史缺陷/知识。
- **动因**：知识库建成后需接入开发/QA 流程，让第二大脑可查。

## 2026-07-20 | Batch 19 | 六部门流水线初建

- **变更**：创建 SKILL.md + DEPARTMENTS.md（Product→PM→Design→Dev→QA→Leader 六部门 + 工件模板 + Git 工作流）。
- **动因**：Batch 19 复盘要求 Agent Team 有标准化可追溯的交付流程。
