# 🗂️ Dev 部门项目看板 — Batch 104（外放轻量模式）

## 📋 项目信息

| 字段 | 值 |
|------|-----|
| **项目名称** | 外放轻量模式：开放注册（邀请码）/ 自助建项目 / 邀请同事；超管全平台权限保持 |
| **关联 PRD** | [batch-104-external-light-mode-prd-summary.md](../batch-104-external-light-mode-prd-summary.md) |
| **执行器** | codex（用户明确确认） |
| **Worktree** | F:\CamelTv-worktrees\codex-batch-104-external-light-mode |
| **分支** | feature/batch-104-external-light-mode |
| **端口** | 前端 5214 / 后端 8044 |

## 🎯 交付切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | 批次工件 + 看板 | ✅ | ✅ | ✅ | ✅ | ⏳ | PRD/PM/Design 已落盘 |
| 2 | 后端注册基础（配置/模型/迁移/接口/测试） | ✅ | ✅ | ✅ | ✅ | ⏳ | 21 新测试 + 迁移 20260806_batch104_invite_code |
| 3 | 后端自助项目（自动成员/配额/所有者权限/测试） | ✅ | ✅ | ✅ | ✅ | ⏳ | create_project 自动成员 + require_project_owner_or |
| 4 | 后端邀请码管理接口 + seed 权限点/测试 | ✅ | ✅ | ✅ | ✅ | ⏳ | system:invite:manage + project:self_create + menu:myproject |
| 5 | 前端注册页 + 登录入口 + 路由 | ✅ | ✅ | ✅ | ✅ | ⏳ | RegisterPage 4 测试 |
| 6 | 前端我的项目页 + 邀请码管理 Tab | ✅ | ✅ | ✅ | ✅ | ⏳ | MyProjectsPage 3 + InviteCodesTab 2 测试；347 全量绿 |
| 7 | QA 硬门禁 + 回归 + 报告 + Leader + 总确认 | ✅ | ✅ | ✅ | 🔄 ⬅️ | ⏳ | **当前位置**：写 QA/Leader 工件，等一次总确认 |

## 📍 当前位置

```
Batch 104 — 外放轻量模式
├── ✅ PRD / PM / Design 工件落盘（mode: full）
├── ✅ 子模块 lanhu-mcp 初始化（C89-1）
├── ✅ KB 检索（PATTERNS.md 本地证据：cookie 污染/契约漂移/envelope 404 纳入自检）
├── ✅ 后端：注册/邀请码/自助项目 21 测试 + 全量 1097 通过（3 跳过）
├── ✅ 前端：注册页/我的项目/邀请码管理，vitest 347/347 + typecheck + build 通过
├── ✅ 端到端冒烟：邀请码→注册→建项目→负责人可见（HTTP 实测）
├── ✅ 门禁：ruff F821 0 / app 导入 OK / Alembic 单头 / scan HARD 0 / cconditions 0 硬错
└── 🔄 写 QA 报告 + Leader 判决 → 一次总确认（push + Draft PR + 合入）
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
- [ ] React 副作用四铁律（cleanup / useCallback / 无 N+1 / Tabs 条件挂载）
