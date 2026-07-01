---
title: "PR 模板"
owner: "qa-team"
last_reviewed: "2026-06-26"
status: "active"
tags: ["template", "pull-request", "code-review"]
---

# Pull Request

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
- [ ] 代码通过 lint 检查（`ruff check` / `npx tsc --noEmit`）
- [ ] 新增/修改代码有对应的测试
- [ ] 测试全部通过（`pytest` / `vitest`）
- [ ] 无遗留的调试代码（`console.log`, `print`, `breakpoint`）

### 架构一致性
- [ ] 未违反架构原则（见 `CLAUDE.md` 架构原则 + [docs/adr/](docs/adr/)）
- [ ] 新增依赖已评估（体积、License、维护状态）
- [ ] API 变更已更新 OpenAPI schema

### 文档保鲜 📋
> 参考：[docs/document-standards.md](docs/document-standards.md)

- [ ] **CLAUDE.md**：如有模块/约定变化，已同步更新对应层级的 CLAUDE.md
- [ ] **README.md**：如有安装/配置/命令变化，已更新相关 README
- [ ] **ADR**：如涉及架构决策，已新增 ADR 或更新已有 ADR 状态
- [ ] **Memory**：重要经验/约定变化，已在 Memory 系统中记录
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
