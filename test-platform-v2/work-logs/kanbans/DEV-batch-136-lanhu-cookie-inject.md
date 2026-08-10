# 🗂️ Dev 看板 — Batch 136（蓝湖 Cookie 注入 + 链接校验）

| 字段 | 值 |
|------|-----|
| 模式 | light |
| 执行器 | codex |
| 分支 | fix/batch-136-lanhu-cookie-inject |
| Worktree | F:/CamelTv-worktrees/codex-batch-136-lanhu-cookie-inject |
| 前/后端端口 | 5226 / 8056 |
| 基线 | origin/main |
| PRD | `../batch-136-lanhu-cookie-inject-prd-summary.md` |

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 0 | 根因定位 | ✅ | ✅ | ✅ | ✅ | ⏳ | LanhuExtractor 无 cookie 参数，注入失效（实测 False） |
| 1 | 后端 Cookie 注入 | ✅ | ✅ | ✅ | ✅ | ⏳ | module.COOKIE/DDS_COOKIE 注入 + 3 测试 |
| 2 | 前端链接校验 | ✅ | ✅ | ✅ | ✅ | ⏳ | pid/docId 校验 + 单测 |
| 3 | QA / Leader | ⏳ | ✅ | ✅ | ✅ | ⏳ | 后端 1313 / 前端 444 |
| 4 | 总确认 → Draft PR → checks → main | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | 未获总确认不得 push |

## 当前结论
- 保存的 Cookie 现在会真正注入 lanhu 请求；残缺链接在提交前即被拦截。
