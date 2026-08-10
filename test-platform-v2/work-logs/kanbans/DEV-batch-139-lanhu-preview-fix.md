# 🗂️ Dev 看板 — Batch 139（蓝湖原型截图预览修复）

| 字段 | 值 |
|------|-----|
| 模式 | light |
| 执行器 | codex |
| 分支 | fix/batch-139-lanhu-preview-fix |
| Worktree | F:/CamelTv-worktrees/codex-batch-139-lanhu-preview-fix |
| 前/后端端口 | 5230 / 8060 |
| 基线 | origin/main |
| PRD | `../batch-139-lanhu-preview-fix-prd-summary.md` |

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 0 | 根因定位 | ✅ | ✅ | ✅ | ✅ | ⏳ | 资产文件随 Railway 重建丢失 → 404 |
| 1 | 下载静默 + 清晰提示 | ✅ | ✅ | ✅ | ✅ | ⏳ | suppressErrorToast + 文案 |
| 2 | 弹窗布局固定 + 版本展示 | ✅ | ✅ | ✅ | ✅ | ⏳ | 444 通过 |
| 3 | QA / Leader | ⏳ | ✅ | ✅ | ✅ | ⏳ | 444 全量 |
| 4 | 总确认 → Draft PR → checks → main | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | 未获总确认不得 push |

## 当前结论
- 截图失效不再全局弹错，预览稳定显示并提示重新采集；仅最新版本采集时预览只含最新版本截图。
