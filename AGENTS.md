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
| 发布分支 | `release/{版本号}` | `release/v2.3.0` |
| 热修复 | `hotfix/{kebab-case-描述}` | `hotfix/sql-injection` |

**禁止使用**: `codex/xxx`、`agent/xxx`、或任何非标准前缀。分支命名遵循 [CLAUDE.md](CLAUDE.md) 关键约定。

## 2. Git 工作流（强制）

### 2.1 核心规则

```
feature/* 或 fix/*
    → push 到 GitHub
    → 创建 PR 指向 develop
    → 合并到 develop
```

- ❌ **禁止直接 push 到 `develop` 或 `master`**
- ❌ **禁止直接 push 到 `main`**（远端无此分支，文档已过期）
- ✅ **只 push 功能分支，通过 PR 合并**

### 2.2 GitHub 分支保护

| 分支 | 删除 | 强推 | 变更方式 | 审批要求 |
|------|------|------|---------|---------|
| `develop` | 禁止 | 禁止 | 必须 PR | 当前不要求 |
| `master` | 禁止 | 禁止 | 必须 PR | 当前不要求 |
| `feature/*` | 允许 | 允许 | 直接 push | N/A |

### 2.3 标准操作流程

```bash
# 1. 检查工作区状态，保护已有修改
git status

# 2. 拉取远端最新状态
git fetch origin

# 3. 从最新 origin/develop 创建功能分支
git checkout -b feature/{描述} origin/develop

# 4. 开发 + 频繁提交（遵循 worktree-reset-hazard 策略）

# 5. 提交前本地自检（见第 3 节）

# 6. Push 功能分支（只 push 功能分支！）
git push -u origin feature/{描述}

# 7. 创建 PR 指向 develop
gh pr create --base develop --head feature/{描述} --title "..." --body "..."
```

### 2.4 多窗口并行（Agent Team）

使用 `git worktree` 隔离工作目录，每个窗口独立分支：
- 每个 Agent Team 窗口 = 一个 worktree + 独立分支
- 所有分支从 `origin/develop` 切出
- 详见 memory: [[agent-team-branch-isolation]]

## 3. 提交前自检清单（强制）

> 每次 `git push` 前必须通过以下检查。与 [.github/pull_request_template.md](.github/pull_request_template.md) 对齐。

### 3.1 代码质量

- [ ] **Lint 通过**: 后端 `ruff check app/`，前端 `npx tsc --noEmit`
- [ ] **测试通过**: 后端 `pytest`，前端 `vitest`
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
- [ ] **Memory**: 重要经验/约定变化已记录

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
| `pr-check.yml` | PR → `main`/`master` | 完整：lint + typecheck + pytest + vitest + PG 迁移 + a11y |
| `develop-import-smoke.yml` | PR → `develop` | 最小：后端导入冒烟 + Alembic 单头校验 |

**重要**: `pr-check.yml` 当前只监听 `main`/`master`，不监听 `develop`。
因此 PR 合并到 `develop` 时 CI 不会自动执行完整门禁。

### 4.2 已知差距

- PR → `develop` 无自动 pytest/vitest/lint/typecheck（见 [pr-check.yml:4](.github/workflows/pr-check.yml#L4)）
- `pr-check.yml` 多数步骤使用了 `continue-on-error: true`，失败仅警告不阻塞
- Jenkins `Jenkinsfile` Docker Push 仅允许 `main` 分支（远端实际无此分支）
- 文档声称 `main` 为主分支，但 GitHub 默认分支为 `develop`，远端无 `main`

**Agent 应对**: 在 CI 补齐前，Agent 必须在本地手动执行第 3 节自检清单，不能依赖 CI 发现。

## 5. 变更摘要模板

每次 `git push` 前，Agent 应向用户展示：

```
## 变更摘要
**分支**: feature/{名称}
**目标**: develop
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
- Memory: [[agent-team-branch-isolation]], [[worktree-reset-hazard]]
