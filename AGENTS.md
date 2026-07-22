---
title: "CamelTv Agent 工作流规范"
owner: "qa-team"
last_reviewed: "2026-07-22"
status: "active"
expires: "2027-01-22"
tags: ["agent", "workflow", "git", "branching", "pr"]
related: ["CLAUDE.md", ".github/pull_request_template.md", "docs/engineering-standards.md"]
---

# AGENTS.md — AI Agent 工作流规范

> 本文档为仓库级 Agent 指令，适用于 Claude Agent、Codex、及其他 AI 编码助手。
> 定义 Agent 在此仓库中的分支、提交、PR 和自检流程。**违反即 Block PR。**

## 1. 分支命名

| 类型 | 格式 | 示例 |
|------|------|------|
| 功能开发 | `feature/{kebab-case-描述}` | `feature/knowledge-search` |
| Bug 修复 | `fix/{kebab-case-描述}` | `fix/login-timeout` |
| 发布分支 | `release/{kebab-case-版本}` | `release/v2-3-0` |
| 热修复 | `hotfix/{kebab-case-描述}` | `hotfix/sql-injection` |

**禁止使用**: `codex/xxx`、`agent/xxx`、或任何非标准前缀。分支命名遵循 [CLAUDE.md](CLAUDE.md) 关键约定。

## 2. Git 工作流（强制）

### 2.1 核心规则

```
feature/* 或 fix/*
    → push 到 GitHub
    → 创建 PR 指向 main
    → squash merge 到 main
```

- ❌ **禁止直接 push 到 `main`**
- ❌ **禁止在控制 worktree 上开发或用 stash/checkout 切任务**
- ✅ **只 push 功能分支，通过 PR 合并**
- ✅ **每个 Claude Code、ChatGPT/Codex、Agent Team 任务使用独立 worktree**

### 2.2 GitHub 分支保护

| 分支 | 删除 | 强推 | 变更方式 | 审批要求 |
|------|------|------|---------|---------|
| `main` | 禁止 | 禁止 | 必须 PR + required checks | 当前单人仓库不强制他人审批 |
| `feature/*` | 允许 | 允许 | 直接 push | N/A |

### 2.3 标准操作流程

```bash
# 1. 检查工作区状态，保护已有修改
git status

# 2. Agent Team 必须先在聊天中问用户“本任务由 Claude Code 还是 Codex 执行？”并停下等待明确答复
# 收到答复后才允许拉取远端状态和创建 worktree；不得根据 IDE、客户端或进程名猜测
git fetch origin

# 3. 从唯一主干创建独立 worktree
# Agent Team 是工作流，必须显式声明实际运行它的 Claude Code/Codex 执行器
pwsh scripts/git/start-agent-team-task.ps1 -Executor codex -UserConfirmedExecutor -Kind feature -Task {描述} -Scope test-platform-v2/frontend -FrontendPort 5174 -BackendPort 8001
# 在 Claude Code 中运行 Agent Team 时用 -Executor claude
# 不走 Agent Team 的直接任务才使用 start-claude-task.ps1 / start-codex-task.ps1

# 4. 在新 worktree 开工前执行
pwsh scripts/git/verify-ai-worktree.ps1 -RequireClean -RequireMetadata -ExpectedWorkflow agent-team -ExpectedExecutor codex

# 5. 开发 + 频繁提交（遵循 worktree-reset-hazard 策略）

# 6. 提交前本地自检（见第 3 节）

# 7. Push 功能分支（只 push 功能分支！）
git push -u origin feature/{描述}

# 8. 创建 Draft PR 指向 main
gh pr create --draft --base main --head feature/{描述} --title "..." --body "..."

# 9. 先做基础审计并等待 Draft PR 首轮 checks
pwsh scripts/git/audit-ai-pr.ps1 -ExpectedWorkflow agent-team -ExpectedExecutor codex

# 10. 首轮验证完成后，Agent Team 再问用户“实际执行器仍为 Codex/Claude 吗，是否授权最终审计与合并？”并停下等待
# 收到明确答复后记录完成确认；身份必须与开始确认一致
pwsh scripts/git/confirm-agent-team-completion.ps1 -Executor codex -UserConfirmedCompletion

# 11. 完成确认证据推送且对应 checks 全绿后，才允许最终审计
pwsh scripts/git/audit-ai-pr.ps1 -ExpectedWorkflow agent-team -ExpectedExecutor codex -RequireSuccessfulChecks
```

### 2.4 多窗口并行（Agent Team）

使用 `git worktree` 隔离工作目录，每个窗口独立分支：
- 每个 Agent Team 窗口 = 一个 worktree + 独立分支
- 所有分支从 `origin/main` 切出
- 每个 worktree 使用独立 `.ai-worktree.json`、前后端端口、SQLite 和 `.env`
- `.ai-worktree.json` 分开记录 workflow（`direct|agent-team`）和 executor（`claude|codex|human`）
- Agent Team 入口要求在聊天中问询并等待用户明确选择 `claude|codex`，然后才可传入 `-UserConfirmedExecutor`；Git 无法从进程名、IDE、客户端、代码风格或 diff 可靠猜测实际 AI
- Agent Team 在 Draft PR 首轮验证后必须再次问询实际执行器和最终交付授权；未运行 `confirm-agent-team-completion.ps1` 时，最终 PR 审计必定失败
- Claude Code 位于 VS Code、Codex 位于 ChatGPT 客户端不影响隔离；隔离由独立 worktree、分支、端口和元数据实现，两个客户端不得打开同一任务 worktree 并行修改
- 目录按 executor 隔离；分支仍按业务任务命名，pre-push 自动核对 workflow/executor、目录、分支和范围
- 分支按任务命名；AI 执行器只写入忽略的本地元数据，pre-push 自动核对 metadata 与当前目录/分支
- 详见 [ADR-0014](docs/adr/0014-single-main-trunk-ai-worktrees.md) 与 `scripts/git/` 可执行工具

## 3. 提交前自检清单（强制）

> 每次 `git push` 前必须通过以下检查。与 [.github/pull_request_template.md](.github/pull_request_template.md) 对齐。

### 3.1 代码质量

- [ ] **硬门禁通过**: 后端 `ruff check app/ --select F821`，前端 `npm run typecheck && npm run build`
- [ ] **相关测试通过**: 后端执行受影响模块 Pytest，前端执行受影响模块 Vitest
- [ ] **全量回归已记录**: PR 前执行后端 `pytest`、前端 `npm test`；若存在已知基线失败，必须列出基线与本分支失败集合，确认无新增失败，禁止只写“历史问题”
- [ ] **无调试遗留**: 无 `console.log`、`print`、`breakpoint`、`debugger`
- [ ] **无硬编码密钥**: 无密码、Token、API Key、私钥

### 3.2 架构一致性

- [ ] 未违反 [CLAUDE.md](CLAUDE.md) 架构原则
- [ ] API 变更已同步 OpenAPI schema
- [ ] 新增依赖已评估（体积、License、维护状态）

### 3.3 文档保鲜

- [ ] **CLAUDE.md**: 模块/约定变化已同步更新
- [ ] **README.md**: 安装/配置/命令变化已更新
- [ ] **ADR**: 架构决策已新增或更新状态
- [ ] **仓库知识**: 重要经验/约定已写入 `docs/adr/`、`docs/common-pitfalls.md` 或 `work-logs/`；个人 Memory 不是交付证据

### 3.4 前端额外规则（React）

> 违反以下任一条 = Block PR。详见 [docs/engineering-standards.md](docs/engineering-standards.md#4-react-副作用与-api-请求规范强制)。

- [ ] **useEffect 清理**: 每个含异步操作的 useEffect 有 cleanup（cancelled 标志或 AbortController）
- [ ] **useCallback 无循环依赖**: 依赖数组不含内部会 SET 的状态变量
- [ ] **无 N+1 请求**: 不在循环中逐条发 API 请求
- [ ] **TabsContent forceMount**: 非活跃 tab 不挂载子组件
- [ ] **Network 验证**: 每个 GET 请求只出现 1 次有效请求

### 3.5 提交文件审查

- [ ] 只提交本次任务范围文件，不夹带无关变更
- [ ] 无备份文件 (`.bak`, `.orig`, `*~`)
- [ ] 无数据库文件 (`.db`, `.sqlite`)
- [ ] 无 IDE/OS 临时文件 (`.DS_Store`, `Thumbs.db`)
- [ ] 无 node_modules、venv、__pycache__

## 4. CI 门禁说明

### 4.1 当前状态

| 工作流 | 触发条件 | 覆盖范围 |
|--------|---------|---------|
| `main-quality-gate.yml` | PR → `main` | 阻断：后端导入/F821/Alembic/全量 pytest，前端 typecheck/Vitest/build |
| `pr-check.yml` | PR → `main` | 扩展：覆盖率、PG 迁移、a11y 与 lint 观察 |
| `ai-delivery-policy.yml` | PR → `main` | 阻断：分支命名、本地 metadata/env/数据库夹带、常见凭据模式 |

### 4.2 已知差距

- 全量 Ruff、mypy、覆盖率阈值和 a11y 中仍有历史债务，暂由扩展工作流报告；运行时 F821、全量测试、类型检查和构建必须阻断
- 单人仓库无法要求 PR 作者自己审批，因此远端以 required checks、禁止强推/删除和 Agent Team PR 审计作为合并门禁
- `lanhu-mcp` 是后端蓝湖 Provider 的运行/开发依赖，必须通过 `.gitmodules` 在干净检出中初始化

**Agent 应对**: 在 CI 补齐前，Agent 必须在本地手动执行第 3 节自检清单并把命令、退出码、失败集合写入 QA 报告；不能依赖文档工件或 CI 名称推断质量。

## 5. 变更摘要模板

每次 `git push` 前，Agent 应向用户展示：

```
## 变更摘要
**分支**: feature/{名称}
**目标**: main
**变更文件**:
  - path/to/file1.py — 修改说明
  - path/to/file2.tsx — 修改说明
**自检结果**:
  - ruff: ✅ / ❌
  - pytest: ✅ / ❌
  - tsc: ✅ / ❌
  - vitest: ✅ / ❌
**风险**: 无 / 低 / 中 / 高（说明）
```

## 6. 关联资源

- 仓库入口: [CLAUDE.md](CLAUDE.md)
- PR 模板: [.github/pull_request_template.md](.github/pull_request_template.md)
- 工程规范: [docs/engineering-standards.md](docs/engineering-standards.md)
- 测试策略: [docs/testing-strategy.md](docs/testing-strategy.md)
- CI 流程: [deploy/CLAUDE.md](deploy/CLAUDE.md)
- ADR: [ADR-0014 单一 main 主干与 AI Worktree 隔离](docs/adr/0014-single-main-trunk-ai-worktrees.md)
