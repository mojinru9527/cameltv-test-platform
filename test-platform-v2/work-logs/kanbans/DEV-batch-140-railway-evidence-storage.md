# 🗂️ Dev 看板 — Batch 140（Railway 持久卷接入蓝湖证据存储）

| 字段 | 值 |
|------|-----|
| 模式 | light |
| 执行器 | codex |
| 分支 | fix/batch-140-railway-evidence-storage |
| Worktree | F:/CamelTv-worktrees/codex-batch-140-railway-evidence-storage |
| 前/后端端口 | 5231 / 8061 |
| 基线 | origin/main |
| PRD | `../batch-140-railway-evidence-storage-prd-summary.md` |

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 0 | 根因定位 | ✅ | ✅ | ✅ | ✅ | ⏳ | Railway 无持久卷 → 截图部署后丢失 |
| 1 | Railway 卷 runbook | ✅ | ✅ | ✅ | ✅ | ⏳ | Dashboard/CLI/验证 |
| 2 | 启动落点日志 + env 示例 | ✅ | ✅ | ✅ | ✅ | ⏳ | main.py + production.env.example |
| 3 | QA / Leader | ⏳ | ✅ | ✅ | ✅ | ⏳ | 导入/F821 |
| 4 | 总确认 → Draft PR → checks → main | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | 未获总确认不得 push |

## 当前结论
- 用户按 runbook 在 Railway 加卷挂载 /app/storage 后，新采集截图跨部署保留，不再 404。
