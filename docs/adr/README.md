---
title: "架构决策记录 (ADR) — 索引"
owner: "tech-lead"
last_reviewed: "2026-06-26"
status: "active"
expires: "2027-06-26"
tags: ["adr", "architecture", "decisions", "index"]
related: ["template.md", "0001-use-python-fastapi-monostack.md", "../document-standards.md"]
---

# Architecture Decision Records (ADR)

> 架构决策记录——记录重要的架构决策及其背景、后果和弃选方案。
> 格式遵循 [Michael Nygard 的 ADR 模式](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)。

## 决策索引

| ADR | 标题 | 状态 | 日期 |
|-----|------|------|------|
| [0001](0001-use-python-fastapi-monostack.md) | 采用 Python FastAPI 纯单栈 | ✅ 已采纳 | 2025-12 |
| [0002](0002-sqlite-with-postgresql-upgrade-path.md) | SQLite 优先，保留 PostgreSQL 升级路径 | ✅ 已采纳 | 2025-12 |
| [0003](0003-frontend-backend-physical-separation.md) | 前后端物理隔离架构 | ✅ 已采纳 | 2025-12 |
| [0004](0004-jwt-bcrypt-rbac-auth.md) | JWT + BCrypt + RBAC 认证授权方案 | ✅ 已采纳 | 2025-12 |
| [0005](0005-zustand-over-redux.md) | Zustand 替代 Redux 作为前端状态管理 | ✅ 已采纳 | 2026-01 |
| [0006](0006-shadcn-ui-over-antd.md) | shadcn/ui 替代 Ant Design 作为 v2 前端 UI 库 | ✅ 已采纳 | 2026-01 |
| [0007](0007-deepseek-llm-test-case-generation.md) | DeepSeek LLM 驱动 AI 测试用例生成 | ✅ 已采纳 | 2026-03 |
| [0008](0008-jenkins-github-actions-dual-cicd.md) | Jenkins + GitHub Actions 双通道 CI/CD | ✅ 已采纳 | 2026-01 |

## ADR 状态

| 状态 | 含义 |
|------|------|
| ✅ 已采纳 (Accepted) | 已实施且当前仍在使用 |
| 🟡 提议中 (Proposed) | 提出但尚未决策 |
| ❌ 已废弃 (Superseded) | 被后续 ADR 替代（需标注替代者） |
| 📦 已弃用 (Deprecated) | 不再适用但未正式替代 |

## 新建 ADR

1. 复制 [template.md](template.md)
2. 命名为 `NNNN-{slug}.md`（NNNN 为连续编号）
3. 填写各章节
4. 在本 README 的索引表中新增一行
5. 提交 PR

**何时需要 ADR**：
- 选择一项新技术/框架/工具（有多个备选方案时）
- 做出影响多个模块的架构变更
- 放弃一项已采用的模式或技术
- 设定项目级的编码/设计约束

**何时不需要 ADR**：
- 单一模块内部的实现细节
- 可轻易回退的决策
- 团队已有共识的常规选择
