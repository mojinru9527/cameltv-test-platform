# 🗂️ Dev 看板 — Batch 137（仅最新版本 + DOM 文本兜底 + OCR 诊断）

| 字段 | 值 |
|------|-----|
| 模式 | full |
| 执行器 | codex |
| 分支 | feature/batch-137-lanhu-latest-version-and-ocr |
| Worktree | F:/CamelTv-worktrees/codex-batch-137-lanhu-latest-version-and-ocr |
| 前/后端端口 | 5228 / 8058 |
| 基线 | origin/main |
| PRD | `../batch-137-lanhu-latest-version-and-ocr-prd-summary.md` |

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 0 | 根因定位 | ✅ | ✅ | ✅ | ✅ | ⏳ | 全量含多版本；OCR 未配置致不可导入 |
| 1 | 后端版本过滤 + 链路透传 | ✅ | ✅ | ✅ | ✅ | ⏳ | 4 单测 |
| 2 | DOM 文本兜底 + ocr_note | ✅ | ✅ | ✅ | ✅ | ⏳ | 有 HTML 文本可导入 |
| 3 | 前端开关 | ✅ | ✅ | ✅ | ✅ | ⏳ | 可选字段，444 通过 |
| 4 | QA / Leader | ⏳ | ✅ | ✅ | ✅ | ⏳ | 后端 1313 / 前端 444 |
| 5 | 总确认 → Draft PR → checks → main | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | 未获总确认不得 push |

## 当前结论
- 勾选"仅最新版本"只采集 16.0.0 文件夹页面；有 DOM 文本的任务无需 OCR 即可达标导入。
