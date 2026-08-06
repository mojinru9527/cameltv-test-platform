# 🗂️ Dev 部门项目看板 — Batch 106（生产启用 + 组织权限映射 + 项目邀请链接）

## 📋 项目信息

| 字段 | 值 |
|------|-----|
| **项目名称** | 生产启用 / 组织权限映射 / 项目邀请链接（C104-2/4 + C105-1/2） |
| **关联 PRD** | [batch-106-production-permissions-invites-prd-summary.md](../batch-106-production-permissions-invites-prd-summary.md) |
| **执行器** | codex（用户明确确认） |
| **Worktree** | F:\CamelTv-worktrees\codex-batch-106-production-permissions-invites |
| **分支** | feature/batch-106-production-permissions-invites |
| **端口** | 前端 5216 / 后端 8046 |

## 🎯 交付切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | 批次工件 + 看板 | ✅ | ✅ | ✅ | ✅ | ⏳ | PRD/PM/Design 已落盘 |
| 2 | 组织权限映射（rbac + 测试） | ⬜ | ⬜ | ⬜ | ⬜ | ⏳ | |
| 3 | 项目邀请链接（模型/迁移/接口/注册集成 + 测试） | ⬜ | ⬜ | ⬜ | ⬜ | ⏳ | |
| 4 | 前端邀请链接 + 注册页参数 | ⬜ | ⬜ | ⬜ | ⬜ | ⏳ | |
| 5 | 生产启用清单 + 演练证据 | ⬜ | ⬜ | ⬜ | ⬜ | ⏳ | |
| 6 | QA 硬门禁 + 回归 + 报告 + Leader + 总确认 | ⬜ | ⬜ | ⬜ | 🔄 ⬅️ | ⏳ | **当前位置**：准备编码 |

## 📍 当前位置

```
Batch 106 — 生产启用 + 组织权限映射 + 项目邀请链接
├── ✅ PRD / PM / Design 工件落盘（mode: full）
├── ✅ worktree 自最新 main（e916279，含 Batch 103/104/105）创建
├── ✅ 子模块 lanhu-mcp 初始化（C89-1）
└── 🔄 安装依赖 → Slice 2 编码（TDD）
```

## 🧰 自检清单

- [ ] ruff F821 / app 导入 / Alembic 单头
- [ ] 受影响模块 pytest + vitest（记录退出码）
- [ ] 双 404 约定（C86-1）/ Token 不落日志
- [ ] 首个补丁落点验证在 worktree（C104-5）
