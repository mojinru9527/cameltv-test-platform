# 🗂️ Dev 看板 — Batch 135（蓝湖登录入口补到创建表单）

| 字段 | 值 |
|------|-----|
| 模式 | light |
| 执行器 | codex |
| 分支 | fix/batch-135-lanhu-login-entry-create |
| Worktree | F:/CamelTv-worktrees/codex-batch-135-lanhu-login-entry-create |
| 前/后端端口 | 5224 / 8054 |
| 基线 | origin/main |
| PRD | `../batch-135-lanhu-login-entry-create-prd-summary.md` |

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 0 | 根因定位 | ✅ | ✅ | ✅ | ✅ | ⏳ | 登录入口只在失败详情页 |
| 1 | 创建表单 + 需求面板补入口 | ✅ | ✅ | ✅ | ✅ | ⏳ | 复用 LanhuReloginDialog |
| 2 | QA / Leader | ⏳ | ✅ | ✅ | ✅ | ⏳ | 443 全量 + 新增断言 |
| 3 | 总确认 → Draft PR → checks → main | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | 未获总确认不得 push |

## 当前结论
- 创建证据表单与需求证据面板现可直接打开"蓝湖登录/更新Cookie"对话框。
