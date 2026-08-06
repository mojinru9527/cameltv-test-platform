# 🗂️ Dev 部门项目看板 — Batch 105（租户模式）

## 📋 项目信息

| 字段 | 值 |
|------|-----|
| **项目名称** | 租户模式：用户→组织/团队→项目（C104-1） |
| **关联 PRD** | [batch-105-tenant-organization-prd-summary.md](../batch-105-tenant-organization-prd-summary.md) |
| **执行器** | codex（用户明确确认） |
| **Worktree** | F:\CamelTv-worktrees\codex-batch-105-tenant-organization |
| **分支** | feature/batch-105-tenant-organization |
| **端口** | 前端 5215 / 后端 8045 |

## 🎯 交付切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | 批次工件 + 看板 | ✅ | ✅ | ✅ | ✅ | ⏳ | PRD/PM/Design 已落盘 |
| 2 | 组织模型 + 迁移回填 + 配置 | ⬜ | ⬜ | ⬜ | ⬜ | ⏳ | |
| 3 | 组织接口 + 注册自动个人组织 | ⬜ | ⬜ | ⬜ | ⬜ | ⏳ | |
| 4 | 项目归属组织 + 组织成员访问 | ⬜ | ⬜ | ⬜ | ⬜ | ⏳ | |
| 5 | 前端组织管理页 + 项目组织联动 | ⬜ | ⬜ | ⬜ | ⬜ | ⏳ | |
| 6 | QA 硬门禁 + 回归 + 报告 + Leader + 总确认 | ⬜ | ⬜ | ⬜ | 🔄 ⬅️ | ⏳ | **当前位置**：准备编码 |

## 📍 当前位置

```
Batch 105 — 租户模式
├── ✅ PRD / PM / Design 工件落盘（mode: full，C104-1 驱动）
├── ✅ worktree 自 Batch 104 合并后的最新 main 创建（c9d7d5a）
├── ✅ 子模块 lanhu-mcp 初始化（C89-1）
└── 🔄 安装依赖 → Slice 2 编码（TDD）
```

## 📝 批次记录

| 产出 | 审批 | 耗时 |
|------|------|------|
| PRD/PM/Design/看板 | — | — |

## 🧰 自检清单（每切片提交前）

- [ ] ruff F821 / app 导入 / Alembic 单头
- [ ] 受影响模块 pytest + vitest（记录退出码）
- [ ] 双 404 约定（C86-1）
- [ ] 无调试遗留 / 无硬编码密钥
- [ ] 首个补丁落点验证在 worktree（C104-5）
- [ ] React 副作用四铁律
