# 🗂️ Dev 看板 — Batch 141（Railway 卷权限报错加固）

| 字段 | 值 |
|------|-----|
| 模式 | light |
| 执行器 | codex |
| 分支 | fix/batch-141-railway-volume-permissions |
| Worktree | F:/CamelTv-worktrees/codex-batch-141-railway-volume-permissions |
| 前/后端端口 | 5232 / 8062 |
| 基线 | origin/main |
| PRD | `../batch-141-railway-volume-permissions-prd-summary.md` |

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 0 | 根因定位 | ✅ | ✅ | ✅ | ✅ | ⏳ | Railway 卷 root 挂载 vs 容器非 root（cameltv UID 10001） |
| 1 | main.py 加固 | ✅ | ✅ | ✅ | ✅ | ⏳ | PermissionError 可操作提示 + chmod 755 尽力而为 |
| 2 | runbook 权限说明 | ✅ | ✅ | ✅ | ✅ | ⏳ | docs/ops/railway-storage.md |
| 3 | QA / Leader | ⏳ | ✅ | ✅ | ✅ | ⏳ | ruff F821 / lanhu 19 用例 / 全量回归 |
| 4 | 总确认 → Draft PR → checks → main | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | 未获总确认不得 push |

## 当前结论
- 用户按 Batch 140 runbook 加卷后遇到 Permission denied；本批让报错自解释并减少人工排障步骤。
- 根治操作：Railway 后端服务 Variables 设 RAILWAY_RUN_UID=0（或 chown /app/storage），代码不改变该部署项。