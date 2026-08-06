# 🗂️ Dev 部门项目看板 — Batch 109（邀请链接正式域名 + 生产种子演示用户开关 + 生产启用回填）

## 📋 项目信息

| 字段 | 值 |
|------|-----|
| **项目名称** | 邀请链接正式域名 / SEED_DEMO_USERS / 生产启用回填（C104-2/105-2/106-1） |
| **关联 PRD** | [batch-109-invite-link-url-prd-summary.md](../batch-109-invite-link-url-prd-summary.md) |
| **执行器** | codex（用户明确确认） |
| **Worktree** | F:\CamelTv-worktrees\codex-batch-109-invite-link-url |
| **分支** | feature/batch-109-invite-link-url |
| **端口** | 前端 5231 / 后端 8052 |

## 🎯 交付切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | 批次工件（PRD/PM/Design）+ 看板 | ✅ | ✅ | ✅ | ✅ | ⏳ | mode: full |
| 2 | FRONTEND_URL + 邀请链接 URL 修复 + 测试 | ✅ | ✅ | ✅ | ✅ | ⏳ | 新 URL 用例 |
| 3 | SEED_DEMO_USERS 种子开关 + 测试 | ✅ | ✅ | ✅ | ✅ | ⏳ | 新用例 |
| 4 | env 模板 + 生产启用清单回填 | ✅ | ✅ | ✅ | ✅ | ⏳ | checklist §1/§2/§6 |
| 5 | QA 硬门禁 + 回归 + 证据 + C-CONDITIONS + Leader | ✅ | ✅ | ✅ | ✅ | ⏳ | **当前位置**：等一次总确认（push + Draft PR + 合入） |

## 📍 当前位置

```
Batch 109 — 邀请链接正式域名 + 生产种子演示用户开关
├── ✅ worktree 自最新 main（93a4012）创建，子模块 lanhu-mcp 初始化（C89-1）
├── ✅ FRONTEND_URL：create_project_invite 配置优先 + 回退；URL 单测
├── ✅ SEED_DEMO_USERS：run_seed 条件化 + 校验联动；单测
├── ✅ env 模板 ×3 + 生产启用清单回填
├── ✅ 门禁：ruff F821 / import / Alembic 单头 / pytest
└── 🔄 QA PASS + Leader APPROVED → 一次总确认（push + Draft PR + 合入）
```

## 🧰 自检清单

- [ ] ruff F821 / app 导入 / Alembic 单头
- [ ] 受影响模块 pytest + 全量 pytest（记录退出码）
- [ ] 首个补丁落点验证在 worktree（C104-5）
- [ ] 凭据/Token 不落日志、不落库
