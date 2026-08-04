# 本地开发操作备忘（Agent Team 版）

> 适用仓库：CamelTv test-platform（单一 main 主干，见 [ADR-0014](../adr/0014-single-main-trunk-ai-worktrees.md)）。
> 目标读者：本地开发者 + Agent Team 各批次执行者。
> 最后更新：2026-08-04（batch-83）。本文件是 Agent Team 的常驻流程资产，改动须同步 SKILL.md「关联」与 CHANGELOG。

## 1. 两条铁律

1. **`F:\CamelTv` 永远保持在 main**：它是"主干视图"，只 `git pull` 看最新代码；不在里面开发、不切任务分支。
2. **每个任务 = 一个独立 worktree + 一个 feature/fix 分支**：开发一律在 `F:\CamelTv-worktrees\{executor}-{task}` 进行，禁止在控制工作区用 stash/checkout 切任务。

为什么：

- `git pull` 只更新"当前所在分支"，永远不会替你换分支——这是"拉了最新代码但工作区还是旧的"的根因（batch-82 实测：F:\CamelTv 曾长期停在 feature/batch-51）。
- 同一个分支不能被两个工作区同时检出（git 强制），天然防互相覆盖。
- main 只能通过 PR 变更；本地 main 的未提交改动不影响远端。

## 2. 目录与角色

| 路径 | 角色 |
|------|------|
| `F:\CamelTv` | 主干视图（main），只同步不开发 |
| `F:\CamelTv-worktrees\codex-{task}` | Codex 执行的任务工作区 |
| `F:\CamelTv-worktrees\claude-{task}` | Claude Code 执行的任务工作区 |
| `.claude/skills/cameltv-agent-team/` | Agent Team 技能（**入库事实源**，改动进 PR） |
| `.agents/skills/cameltv-agent-team/` | Codex 本地技能镜像（git 忽略，不入库；**改动须与 .claude 同步**） |

## 3. Agent Team 标准流程

### 3.1 开工前（硬暂停）

1. 读看板：`work-logs/kanbans/DEV-{项目}.md`（不存在则用 `work-logs/kanbans/_TEMPLATE.md` 创建）。
2. 读 `C-CONDITIONS.md`：PRD 必须纳入或豁免全部 Open 条件。
3. 在聊天中问用户"本任务由 Claude Code 还是 Codex 执行？"并**停下等答复**；不得从 IDE/客户端/进程推断。

### 3.2 创建独立工作区

```powershell
# Codex 执行
pwsh scripts/git/start-agent-team-task.ps1 -Executor codex -UserConfirmedExecutor -Kind feature -Task batch-{N}-{name} -Scope {模块} -FrontendPort {端口} -BackendPort {端口}
# Claude Code 执行
pwsh scripts/git/start-agent-team-task.ps1 -Executor claude -UserConfirmedExecutor -Kind feature -Task batch-{N}-{name} -Scope {模块} -FrontendPort {端口} -BackendPort {端口}
# 开工前验证
pwsh scripts/git/verify-ai-worktree.ps1 -RequireClean -RequireMetadata -ExpectedWorkflow agent-team -ExpectedExecutor {codex|claude}
```

端口必须与现有工作区不冲突（脚本自动检测；查看占用：`git worktree list` + 各 `.ai-worktree.json`）。

### 3.3 开发与提交

- 每切片结束：`git add -- {本切片文件}` → `git diff --cached --name-status` 核对 → commit → push。
- **push 前（每次）**：展示变更摘要，逐字询问："当前待推送范围如下。是否还有其他变动需要合并？如果有，我将暂停推送，完成合并和自检后再重新确认。" 只有用户明确回答"没有其他变动"并明确授权本次 push 才可推送（AGENTS.md §2.4）。
- 提交前自检：`scan-common-bugs.ps1`（HARD>0 处理或豁免，C76-2）、`audit-cconditions.ps1 -RequireLatestBatch`（C75-3）、变更域对应门禁。

### 3.4 PR 与合入

1. 全部 Slice + 首轮 QA 证据 → `gh pr create --draft --base main --head feature/batch-{N}-{name}`。
2. 首轮审计：`pwsh scripts/git/audit-ai-pr.ps1 -ExpectedWorkflow agent-team -ExpectedExecutor {codex|claude}`。
3. **二次硬暂停**：再问用户实际执行器 + 是否授权最终审计/合并；收到明确答复后运行 `pwsh scripts/git/confirm-agent-team-completion.ps1 -Executor {codex|claude} -UserConfirmedCompletion`。
4. required checks 全绿 → 最终审计（`-RequireSuccessfulChecks`）→ Leader APPROVED → 转 Ready → squash 合入 main。
5. 合入后：`git -C F:\CamelTv pull --ff-only origin main` 更新主干视图；按需 `git worktree remove` 清理任务工作区。

## 4. 批次生命周期

一个版本批次完成（开发 + QA + Review + Leader Verdict）→ **先合入 main** → push 主干 → 验证 CI → **从最新 main 创建下一个批次**。

❌ 禁止在上一批次未合并时基于旧 main 开新批；多个并行批次完成时按交付顺序逐个合并、冲突在合并时解决。

## 5. 常见坑速查

| 现象 | 原因 | 处理 |
|------|------|------|
| pull 后工作区还是旧代码 | pull 只更新当前分支，不切分支 | F:\CamelTv 保持在 main；开发用新 worktree |
| `git switch main` 报"main 已被工作区占用" | main 被另一个 worktree 检出 | `git worktree list` 找到占用者，先让它在旧工作区切走/脱离，再使用 main |
| 新代码里的脚本/文件找不到 | 工作区停在旧分支 | 从最新 origin/main 更新或重建工作区 |
| 端口冲突 | 多个工作区 metadata 端口重复 | 换独立端口；脚本启动时自动检测 |
| 周审计误报大量 HARD | scan 未排除普通 `venv/`（batch-82 已修复） | F:\CamelTv 更新到含修复的 main |
| 要改 Agent Team 技能 | `.claude` 是入库事实源，`.agents` 是本地镜像 | 改 `.claude` 进 PR + 同步 `.agents` 镜像 + CHANGELOG |

## 6. 直接任务（不走 Agent Team）

非 Agent Team 的直接任务使用 `scripts/git/start-codex-task.ps1`（Codex）/ `start-claude-task.ps1`（Claude），同样生成独立 worktree + `.ai-worktree.json`；push 门禁、Draft PR、审计流程与 Agent Team 一致。

## 7. 常用命令速查

| 用途 | 命令 |
|------|------|
| 查看工作区与分支占用 | `git worktree list` |
| 主干视图更新 | `git -C F:\CamelTv pull --ff-only`（或 fetch + merge --ff-only） |
| 创建 Agent Team 工作区 | `pwsh scripts/git/start-agent-team-task.ps1 -Executor {codex|claude} -UserConfirmedExecutor -Kind feature -Task ... -Scope ... -FrontendPort ... -BackendPort ...` |
| 创建直接任务工作区 | `pwsh scripts/git/start-codex-task.ps1 -Kind fix -Task ... -Scope ... -FrontendPort ... -BackendPort ...` |
| 工作区隔离验证 | `pwsh scripts/git/verify-ai-worktree.ps1 -RequireClean -RequireMetadata -ExpectedWorkflow {direct|agent-team} -ExpectedExecutor {codex|claude}` |
| PR 审计 | `pwsh scripts/git/audit-ai-pr.ps1 -ExpectedWorkflow {direct|agent-team} -ExpectedExecutor {codex|claude} [-RequireSuccessfulChecks]` |
| C 条件审计 | `pwsh scripts/git/audit-cconditions.ps1 -RequireLatestBatch` |
| WARN 周审计 | `pwsh scripts/git/run-warn-audit.ps1 -RepositoryPath F:\CamelTv` |
