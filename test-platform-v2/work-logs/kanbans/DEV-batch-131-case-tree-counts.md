# 🗂️ Dev 看板 — Batch 131（用例模块树计数守恒）

| 字段 | 值 |
|------|-----|
| 模式 | light |
| 执行器 | codex |
| 分支 | feature/batch-131-case-tree-counts |
| Worktree | F:/CamelTv-worktrees/codex-batch-131-case-tree-counts |
| 前/后端端口 | 5181 / 8011 |
| 基线 | origin/main@674286d |
| PRD-lite | `../batch-131-case-tree-counts-prd-summary.md` |

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 0 | Product / 根因定位 | ✅ | ✅ | ✅ | ✅ | ⏳ | FAQ帮助 27 = 直属 18 + 子级 9 |
| 1 | TDD：直属计数纯函数与页面树测试 | ✅ | ✅ | ✅ | ⏳ | ⏳ | 红→绿：countDirectCases + DomainTree 只读项 + 页面树 |
| 2 | DomainTree 非交互统计项 | ✅ | ✅ | ✅ | ⏳ | ⏳ | selectable=false 只读行，浏览器证据无筛选请求 |
| 3 | QA / 浏览器 / Leader | ⏳ | ✅ | ✅ | 🔄 | ⏳ | typecheck/build/440 测试全绿 + 浏览器验收 pass |
| 4 | 总确认 → Draft PR → checks → main | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | 未获总确认不得 push |

## 当前结论

- 根因是 taxonomy 父节点同时包含本级直属与后代计数，而前端仅渲染后代。
- 本批不改变后端、数据库或用例分类，只补齐可见统计核算。
- 直属用例是只读说明项，不是可筛选的业务分类。

