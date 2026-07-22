# Agent Team Git Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 Claude、Codex 和 Agent Team 通过固定入口创建可追溯 worktree，并让本地 hook、PR 审计和 GitHub 门禁自动判断 push/PR 是否符合单一 `main` 主干规范。

**Architecture:** 启动入口是身份事实源，不通过进程名猜测 AI；`.ai-worktree.json` 记录 owner、branch、base、scope 和端口。`verify-ai-worktree.ps1` 校验本地身份与分支，pre-push 在任务分支写入远端前自动调用它，`audit-ai-pr.ps1` 再核对 GitHub PR、远端 SHA、范围、检查和仓库合并策略；GitHub Actions 提供与本地环境无关的最终策略门禁。

**Tech Stack:** Git worktree、PowerShell 7、POSIX pre-push hook、GitHub CLI/API、GitHub Actions、`.gitattributes`。

---

### Task 1: 固定 AI 启动入口

**Files:**
- Create: `scripts/git/start-claude-task.ps1`
- Create: `scripts/git/start-codex-task.ps1`
- Create: `scripts/git/start-agent-team-task.ps1`
- Modify: `scripts/git/test-ai-worktree-tools.ps1`

- [ ] **Step 1: 添加失败断言**

在临时仓库中通过 Claude 入口创建任务，并断言 `.ai-worktree.json.owner == "claude"`、目录名前缀为 `claude-`；用 Codex 身份校验 Claude worktree 必须失败。

- [ ] **Step 2: 运行自测并确认失败**

Run: `pwsh -NoProfile -File scripts/git/test-ai-worktree-tools.ps1`

Expected: FAIL，因为固定入口和 ExpectedOwner 校验尚不存在。

- [ ] **Step 3: 实现三个薄入口**

三个入口只接收 `Kind/Task/Scope/FrontendPort/BackendPort/RepositoryPath/DestinationRoot`，分别把不可由调用者覆盖的 `Owner=claude/codex/agent-team` 转交给 `new-ai-worktree.ps1`。

- [ ] **Step 4: 运行入口测试**

Run: `pwsh -NoProfile -File scripts/git/test-ai-worktree-tools.ps1`

Expected: 固定入口身份与目录断言通过。

### Task 2: worktree 身份与 push 硬校验

**Files:**
- Modify: `scripts/git/verify-ai-worktree.ps1`
- Modify: `.githooks/pre-push`
- Modify: `scripts/git/test-ai-worktree-tools.ps1`

- [ ] **Step 1: 增加 metadata 负向测试**

测试缺少 metadata、owner 不匹配、metadata branch 不等于当前分支、目录名不等于 `{owner}-{task}` 时验证失败；删除远端任务分支仍允许。

- [ ] **Step 2: 扩展 verifier**

增加 `-RequireMetadata` 和 `-ExpectedOwner`；校验 owner 枚举、branch/base/task/目录名、scope 非空、前后端端口范围且不相等，并输出 Ahead/Behind 供 Agent Team 判断是否需要同步 `main`。

- [ ] **Step 3: 加固 pre-push**

任何写入 `refs/heads/feature|fix|hotfix|release/*` 的 push 先运行 verifier；直接写入或删除 `main/master/develop` 始终拒绝；纯标签与已合并任务分支删除不要求 metadata。

- [ ] **Step 4: 运行 hook 自测**

Run: `pwsh -NoProfile -File scripts/git/test-ai-worktree-tools.ps1`

Expected: 合法任务 push 成功，metadata 篡改后的 push 失败，main push 失败，任务分支删除成功。

### Task 3: Agent Team PR 交付审计

**Files:**
- Create: `scripts/git/audit-ai-pr.ps1`
- Modify: `.github/pull_request_template.md`
- Modify: `.claude/skills/cameltv-agent-team/SKILL.md`

- [ ] **Step 1: 实现本地与远端一致性检查**

脚本必须验证工作区干净、metadata 合法、当前分支已设置 `origin/{branch}` upstream、本地 HEAD 等于远端 SHA、PR base 为 `main`、head 等于当前分支、默认主干为 `main`、仓库仅允许 squash 且自动删除任务分支。

- [ ] **Step 2: 实现范围与检查审计**

PR changed files 必须匹配 metadata scope 中的精确路径或目录前缀；`-RequireSuccessfulChecks` 时，“后端全新检出与全量回归”“前端全新检出与全量回归”“AI/Git 交付策略”必须全部 SUCCESS。

- [ ] **Step 3: 在 PR 模板和 Agent Team Leader 门禁中接入**

PR 模板记录 AI Owner；Leader 在 APPROVED 前运行：

```powershell
pwsh scripts/git/audit-ai-pr.ps1 -RequireSuccessfulChecks
```

- [ ] **Step 4: 用本批次真实 PR 验证**

Expected: push 后、PR 创建前审计会因 PR 不存在失败；创建 Draft PR 后基础审计通过；检查完成前 `-RequireSuccessfulChecks` 失败；全部检查通过后成功。

### Task 4: GitHub 策略门禁与行尾一致性

**Files:**
- Create: `.github/workflows/ai-delivery-policy.yml`
- Create: `.gitattributes`
- Modify: `scripts/git/install-git-guardrails.ps1`
- Modify: `AGENTS.md`
- Modify: `docs/adr/0014-single-main-trunk-ai-worktrees.md`

- [ ] **Step 1: 添加 PR 策略工作流**

工作流仅接受 `feature/fix/hotfix/release` 的 kebab-case head 分支，拒绝提交 `.ai-worktree.json`、`.env`、`.env.local`、数据库和常见密钥模式，job 显示名固定为“AI/Git 交付策略”。

- [ ] **Step 2: 固定文本行尾**

`.gitattributes` 使用 `* text=auto eol=lf`，仅为 `.bat/.cmd` 指定 CRLF；安装脚本设置仓库级 `core.autocrlf=false`，避免 Windows 系统配置制造假脏文件。

- [ ] **Step 3: 更新共同规范**

文档明确固定入口、metadata 身份边界、pre-push 自动验证、PR 审计命令和远端 Actions/ruleset 是最终强制层。

- [ ] **Step 4: 本地静态验证**

Run: PowerShell parser、PyYAML、`git diff --check`、敏感信息扫描、`git check-attr`。

Expected: 全部 PASS，`git add --renormalize --dry-run` 不产生无关大规模改动。

### Task 5: 真实 PR 与规则闭环

**Files:**
- Create: `work-logs/batch-33-agent-git-automation-qa-report.md`
- Create: `work-logs/batch-33-agent-git-automation-leader-verdict.md`
- Create: `work-logs/kanbans/DEV-batch-33-agent-git-automation.md`

- [ ] **Step 1: 提交并推送任务分支**

Expected: 新 pre-push 自动调用 verifier 后允许 push，远端 `main` 不变。

- [ ] **Step 2: 创建 Draft PR 指向 main**

Expected: “AI/Git 交付策略”与既有六项检查启动；基础 PR 审计通过，成功检查审计暂时失败。

- [ ] **Step 3: 将新策略 job 加入 main ruleset required checks**

Expected: Draft/未完成检查时 PR 显示 BLOCKED；三个 required checks 全绿后可转 Ready。

- [ ] **Step 4: Leader 最终审计并 squash 合并**

Run: `pwsh scripts/git/audit-ai-pr.ps1 -RequireSuccessfulChecks`

Expected: PASS；PR 只能 squash 合入，任务远端分支自动删除，控制 worktree 更新后无假脏状态。

## Self-review

- Spec coverage: 固定入口、push 校验、PR 审计、GitHub 门禁与行尾一致性均有实现和真实验证任务。
- Placeholder scan: 无 TBD/TODO；所有命令、文件和期望结果均明确。
- Type consistency: owner 固定为 `claude|codex|agent-team|human`；required check 名称在脚本、workflow 与 ruleset 中一致。
