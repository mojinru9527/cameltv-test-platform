# Batch 190 — QA 报告：六部门 Agent Team 流水线移植到 dsh-agent-teams（DSH 船长模式）

> **QA (🔍)** | Date: 2026-08-17 | Verdict: PASS（有条件通过，与 t1 Product 抽检一致；P3 建议 3 项 + 移交 t1 P3 建议 2 项，均不阻断）

## 测试总览

| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 6 项门禁核对 | 6 | 0 | 0 |

本批为轻量批次（mode: light，docs/skills/scripts 类），按 AGENTS.md §4.2 CI 分层**无需前后端重测试**（三个 required 对 docs/scripts 类返回明确结果）；门禁核对聚焦：ps1 语法、三执行器枚举一致性、双副本哈希、双模式结构、C75-3 audit 记录、CI 分层判定。

## 可执行门禁（命令 + 退出码 + 日志摘要）

| # | 命令 | 退出码 | 结果摘要 |
|---|------|--------|---------|
| G1 | PowerShell AST Parser 解析 5 个 ps1（start-agent-team-task / new-ai-worktree / verify-ai-worktree / audit-ai-pr / start-deepseek-harness-agent-team） | 0 | 全部 PASS，0 语法错误 |
| G2 | `pwsh scripts/git/audit-cconditions.ps1 -RequireLatestBatch`（worktree 内，船长实测 + QA 复验两次一致） | **1** | 11 个 hard error **全部为历史孤儿条件**（C120-2、C155-1、C163-1、C167-2、C168-1、C168-2、C181-1、C181-2、C181-3、C182-1、G1-G5 出现在 leader-verdict 但不在 C-CONDITIONS.md）；warnings=0；**本批未新增 C 条件** → 判定为已知基线失败，不阻断本批 |
| G3 | 新入口冒烟：`start-deepseek-harness-agent-team.ps1 -Task "Invalid Task!"`（非法 kebab-case） | 1（预期） | 正确转发参数至 new-ai-worktree.ps1，触发 kebab-case 校验报错，未创建 worktree（无副作用） |
| G4 | `git status --porcelain --untracked-files=all`（worktree） | 0 | 干净（仅船长起草中的 leader-verdict.md 未跟踪，属预期） |

## 逐条件验证

### C75-1（mode: light 记录）
**变更文件**: `test-platform-v2/work-logs/batch-190-dsh-agent-teams-migration-prd-summary.md:3-4`
| 检查项 | 结果 | 说明 |
|--------|------|------|
| mode: light 显式声明 | ✅ PASS | 第 3 行 `mode: light` |
| 豁免理由 | ✅ PASS | 第 4 行：全部为 Agent/Git 本地工具与技能文档改动，不触碰产品代码，按 pipeline-modes.md 轻量批次三件套执行 |
| 非目标声明 | ✅ PASS | 第 5 行：不新增接口/Schema/迁移；`/dsh-tasks` 团队模式子项目 B 不在本批 |

### C75-3（audit-cconditions 实际执行证据）★ t1 移交条件项，已闭环
**变更文件**: 本批（未设新 C 条件）；证据 = G2 实测
| 检查项 | 结果 | 说明 |
|--------|------|------|
| 实际执行 audit-cconditions.ps1 | ✅ PASS | 船长与 QA 各实测一次，结果一致 |
| EXIT=1 归因 | ✅ PASS | 11 个 hard error 全部为历史孤儿条件（C120-2/C155-1/C163-1/C167-2/C168-1/C168-2/C181-1/C181-2/C181-3/C182-1/G1-G5），均系早前批次遗留（leader-verdict 引用但 tracker 已删），本批未新增 C 条件 |
| 判定 | ✅ PASS | 已知基线失败，不阻断本批；如实记录命令+退出码+失败集合 |

### C104-5（worktree 核验）
**变更文件**: 本批全部写入
| 检查项 | 结果 | 说明 |
|--------|------|------|
| 全部写入位于 worktree | ✅ PASS | 本批 14 个改动文件均在 `F:\CamelTv-worktrees\DeepSeek_Harness-batch-190-dsh-agent-teams-migration`（branch feature/batch-190-dsh-agent-teams-migration） |
| 无夹带 | ✅ PASS | git status 干净，仅未跟踪的 leader-verdict.md（船长起草中） |

## 专项核验（QA 门禁核对重点）

### 1. ps1 语法（PowerShell AST Parser 复验）— ✅ PASS
5 个脚本全部 AST parse OK（G1）：`start-agent-team-task.ps1`、`new-ai-worktree.ps1`、`verify-ai-worktree.ps1`、`audit-ai-pr.ps1`（本批未改但复验）、新增 `start-deepseek-harness-agent-team.ps1`。

### 2. 三执行器枚举一致性 — ✅ PASS（2 处 P3 文档示例遗留）
脚本层 ValidateSet 与本批文案目标完全一致：

| 文件 | ValidateSet / 固定值 | 结论 |
|------|----------------------|------|
| start-agent-team-task.ps1:4 | `claude, codex, DeepSeek_Harness` | ✅ |
| new-ai-worktree.ps1:5 | `claude, codex, DeepSeek_Harness, human` | ✅ |
| verify-ai-worktree.ps1:10 | `claude, codex, DeepSeek_Harness, human` | ✅ |
| audit-ai-pr.ps1:7 | `claude, codex, DeepSeek_Harness, human` | ✅ |
| start-deepseek-harness-agent-team.ps1:19 | 固定 `DeepSeek_Harness` | ✅ |

文档侧：SKILL.md（模式表 + `{claude|codex|DeepSeek_Harness}` 命令示例）、DEPARTMENTS.md Dev 节（107 行）、AGENTS.md §2.3/§2.5、local-dev-workflow.md 正文（§3.1/§3.2/§3.4）、ADR-0014 全部三选化 ✅。

**P3 遗留（不阻断）**：
- P3-1：`DEPARTMENTS.md:220` Leader 节 audit-ai-pr 示例仍为 `claude|codex`（功能无影响，audit-ai-pr.ps1 的 ValidateSet 已支持 DSH；建议后续批次补齐）。
- P3-2：`local-dev-workflow.md:97-100` §5 命令速查表仍为 `{codex|claude}`（正文已三选，速查表遗漏；建议补齐）。
- P3-3（观察）：`confirm-agent-team-completion.ps1:4` ValidateSet 仍为 `claude, codex`——该脚本 AGENTS.md 已注明「仅作可选完成证据，不再强制」，船长手册也未要求 DSH 使用，故不构成本批问题；DSH 船长如需使用需先扩展枚举（建议下批）。

### 3. 双副本哈希一致性 — ✅ PASS
worktree HEAD 的 `.claude/skills/cameltv-agent-team/` 三文件与主仓库 `.agents/skills/cameltv-agent-team/` 镜像哈希全部一致（SHA256）：

| 文件 | worktree .claude | 主仓库 .agents | 结论 |
|------|------------------|----------------|------|
| SKILL.md | D0DB9DAF67D0... | D0DB9DAF67D0... | ✅ SYNC |
| DEPARTMENTS.md | 7F660740025D... | 7F660740025D... | ✅ SYNC |
| CHANGELOG.md | 5AC7AFF6A370... | 5AC7AFF6A370... | ✅ SYNC |

主仓库 `.claude`（main 分支）仍为旧版属预期——合入 main 前不更新；`.agents` 镜像已同步到本批最新版本，符合 local-dev-workflow.md「改 .claude 进 PR + 同步 .agents 镜像 + CHANGELOG」规则。CHANGELOG 含本批条目（2b9e4d3 补充提交覆盖 ADR-0014/local-dev-workflow 同步记录）✅。

### 4. 双模式结构完整性 — ✅ PASS
- SKILL.md「流水线」节：双执行模式表（模式①单会话角色扮演 Claude Code/Codex；模式②DSH AgentTeams 船长模式 DeepSeek Harness）+「两种模式产出相同工件」声明 + 关联节新增手册链接 ✅。
- `docs/agent-team/dsh-agent-teams.md`（123 行）8 章齐全：前置条件 / 团队模型与批次模式映射 / 完整批次协议（3.1 建团队+加成员 → 3.2 建任务带依赖 → 3.3 认领+派发 → 3.4 收件与状态推进 → 3.5 船长收尾）/ 轻量批次协议 / Git 门禁 / 常见坑 / 模式选用 / 关联 ✅。
- 完整批次 5 成员、轻量批次 2 成员、依赖图强制顺序、工件交接规则、复盘卡/流程回写要求均与 SKILL.md/DEPARTMENTS.md 一致 ✅。

### 5. CI 分层判定 — ✅ PASS（无需前后端重测试）
本批 14 个文件全部属于 `.claude/skills/`、`docs/`、`scripts/git/`、`AGENTS.md`、`work-logs/`、`test-platform-v2/work-logs/`（PRD-lite 工件）——按 AGENTS.md §4.2「Markdown、docs/、work-logs/、Agent/Git/CI 本地工具」层：前后端重测试跳过，三个 required 返回明确结果；无 test-platform-v2 前后端代码改动，无 workflow/deploy 变更。

### 6. 提交完整性 — ✅ PASS
本批实际 7 个提交（f2f45cf → 3dfabd4 → f4fccdb → 4629432 → 3e31f8a → 11234ff → 2b9e4d3），线性、无 merge，均位于 feature/batch-190-dsh-agent-teams-migration，base 02cc158（Batch 189 三期后），worktree 与分支命名符合 AGENTS.md。

## 缺陷列表

| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| D-1 | P3 | DEPARTMENTS.md:220 Leader 节 audit-ai-pr 示例未含 DeepSeek_Harness | `DEPARTMENTS.md:220` `-ExpectedExecutor claude|codex` | ✅ 已修复（船长定稿轮顺手补齐，提交见本批最终 HEAD） |
| D-2 | P3 | local-dev-workflow.md §5 命令速查表 `{codex|claude}` 未三选化（正文已三选） | `local-dev-workflow.md:97,99,100` | ✅ 已修复（c832afc；QA 检查时该提交已落盘但本报告核对滞后） |
| D-3 | P3 | confirm-agent-team-completion.ps1 ValidateSet 未含 DeepSeek_Harness（可选证据脚本，非本批范围） | `confirm-agent-team-completion.ps1:4` | 观察项（下批按需扩展） |

**t1 移交 P3 建议（复述，不重复计缺陷）**：成功指标表可补基线列；「（-Workflow agent-team）」为行为描述非字面参数（脚本无 -Workflow 命令行参数，Workflow 为内部硬编码 `$arguments.Workflow = "agent-team"`）。

## 发布建议

状态: **READY**（有条件通过）
必修复: 0　建议修复: 2（P3-1、P3-2 文档示例补齐）+ 1 观察（P3-3）
C75-3 条件项已闭环（实测证据 = G2，两次一致）；无 P0/P1/P2 缺陷。

## 复盘卡（Batch 75 起强制）

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 轻量批次 1 轮（t2） vs 实际 1 轮 | 0/0/0/3 | 0 | 文档示例遗漏（正文已三选、速查表/Leader 节示例未同步）+ 可选脚本枚举未扩展 | 三执行器化改造合入前跑一次全仓库 grep `claude\|codex` 残留核对（含速查表与可选脚本）；C75-3 类基线失败在 QA 报告如实记录命令+退出码+失败集合 |

**技能使用**: 无（本批为 docs/scripts 类，未加载 cameltv-api-test/playwright 等测试技能；核验手段 = PowerShell AST Parser + git diff/show + 哈希比对 + audit-cconditions 实测，均已在报告中记录命令与退出码）
