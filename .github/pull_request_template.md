---
title: "PR 模板"
owner: "qa-team"
last_reviewed: "2026-06-26"
status: "active"
tags: ["template", "pull-request", "code-review"]
---

# Pull Request

## AI 交付身份

- Workflow：`direct / agent-team`
- Executor：`claude / codex / human`（Agent Team 只能选择 Claude/Codex）
- Agent Team 开始确认：`confirmed / 不适用`（确认时间、聊天入口）
- Agent Team 完成确认：`pending / confirmed / 不适用`（首轮 CI 后再次确认；确认时间）
- Worktree task：
- 声明范围（与 `.ai-worktree.json` 一致）：

## 变更类型

- [ ] 🔧 Bug 修复
- [ ] ✨ 新功能
- [ ] 📝 文档更新
- [ ] ♻️ 重构（无功能变更）
- [ ] 🚀 CI/CD / 部署
- [ ] 🧪 测试
- [ ] 🔒 安全

## 变更说明

<!-- 简要描述此 PR 做了什么，为什么这样做 -->

## 关联

<!-- 关联的 Issue / ADR / 文档 -->
- Issue: #
- ADR: 
- 相关文档: 

---

## 自检清单

### 代码质量
- [ ] 后端运行时硬门禁通过（`ruff check app --select F821`）
- [ ] 前端通过 `npm ci && npm run typecheck && npm run build`
- [ ] 新增/修改代码有对应的测试
- [ ] 相关测试与全量回归通过（`pytest` / `npm test`），命令和退出码已记录
- [ ] Alembic 仅一个 head，revision 长度测试通过
- [ ] 无遗留的调试代码（`console.log`, `print`, `breakpoint`）

### 可执行证据

| 检查 | 命令 | 结果/退出码 | CI 或日志链接 |
|---|---|---|---|
| 后端 |  |  |  |
| 前端 |  |  |  |
| 迁移 |  |  |  |
| UI/关键路径 |  |  |  |

> 文件存在、代码目测或工件齐全不能单独作为 PASS 证据。

### 架构一致性
- [ ] 未违反架构原则（见 `CLAUDE.md` 架构原则 + [docs/adr/](docs/adr/)）
- [ ] 新增依赖已评估（体积、License、维护状态）
- [ ] API 变更已更新 OpenAPI schema

### 文档保鲜 📋
> 参考：[docs/document-standards.md](docs/document-standards.md)

- [ ] **CLAUDE.md**：如有模块/约定变化，已同步更新对应层级的 CLAUDE.md
- [ ] **README.md**：如有安装/配置/命令变化，已更新相关 README
- [ ] **ADR**：如涉及架构决策，已新增 ADR 或更新已有 ADR 状态
- [ ] **仓库知识**：重要经验/约定已写入 ADR、常见陷阱或 work-logs；个人 Memory 不作为交付证据
- [ ] **Worktree 隔离**：分支从最新 `origin/main` 创建，`.ai-worktree.json` 未提交，未在控制 worktree 开发
- [ ] **Agent Team 开始确认**：开发前已在聊天中询问并收到 Claude/Codex 明确答复，启动命令带 `-UserConfirmedExecutor`（direct 任务不适用）
- [ ] **基础 PR 审计**：`pwsh scripts/git/audit-ai-pr.ps1 -ExpectedWorkflow {direct|agent-team} -ExpectedExecutor {claude|codex|human}` 通过，workflow/executor/branch/base/remote SHA/scope 一致
- [ ] **Agent Team 完成确认**：Draft PR 首轮验证后再次询问实际执行器与最终交付授权，并运行 `confirm-agent-team-completion.ps1 -UserConfirmedCompletion`（direct 任务不适用）
- [ ] **最终 PR 审计**：完成确认证据对应的 required checks 全绿后，在同一命令增加 `-RequireSuccessfulChecks` 并通过
- [ ] **常见陷阱**：如发现新的重复性陷阱，已追加至 [docs/common-pitfalls.md](docs/common-pitfalls.md)
- [ ] **术语表**：如有新业务术语引入，已更新 [docs/business-glossary.md](docs/business-glossary.md)

### 安全性
- [ ] 无硬编码密钥/密码/Token
- [ ] 用户输入已校验和转义
- [ ] 敏感操作有权限检查

### 部署（如涉及）
- [ ] Dockerfile 已更新（如依赖变更）
- [ ] CI/CD 配置已更新（如需）
- [ ] 环境变量说明已更新

---

## 截图 / 录屏（如涉及 UI 变更）

<!-- 拖入或粘贴截图 -->

## 给审查者的备注

<!-- 希望审查者重点关注的部分，或已知的权衡 -->
