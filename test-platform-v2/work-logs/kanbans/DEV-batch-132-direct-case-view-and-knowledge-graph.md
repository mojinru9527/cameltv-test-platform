# 🗂️ Dev 看板 — Batch 132（直属用例可查看/编辑 + 知识图谱计数/分域）

| 字段 | 值 |
|------|-----|
| 模式 | full |
| 执行器 | codex |
| 分支 | feature/batch-132-direct-case-view-and-knowledge-graph |
| Worktree | F:/CamelTv-worktrees/codex-batch-132-direct-case-view-and-knowledge-graph |
| 前/后端端口 | 5220 / 8050 |
| 基线 | origin/main@58cf6f7 |
| PRD | `../batch-132-direct-case-view-and-knowledge-graph-prd-summary.md` |

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 0 | Product / 根因定位 | ✅ | ✅ | ✅ | ✅ | ⏳ | 三问题根因：直属无精确过滤/图谱用例仅子集+计数口径错/孤儿实体双域重复 |
| 1 | 后端 taxonomy_direct 直属精确过滤 | ✅ | ✅ | ✅ | ⏳ | ⏳ | list/export + direct_only + 4 测试（62/62） |
| 2 | 前端直属核算行可点击查看/编辑 | ✅ | ✅ | ✅ | ⏳ | ⏳ | isAccounting 可点击 + selDirect 过滤 + 12/12 测试 |
| 3 | 后端全量用例入图 + source 回填 + 计数口径 | ✅ | ✅ | ✅ | ⏳ | ⏳ | sync 服务/接口/脚本 + test_case_total + 4 测试 |
| 4 | 后端分域隔离（graph/view + entities/stats） | ✅ | ✅ | ✅ | ⏳ | ⏳ | _knowledge_domain_filter 三端点 + 测试 |
| 5 | 前端图谱计数展示 + 分域传参 | ✅ | ✅ | ✅ | ⏳ | ⏳ | GraphTab 已入库/全量 + EntityTab 分域 + 442/442 |
| 6 | QA / 浏览器 / Leader | ⏳ | ✅ | ✅ | ✅ | ⏳ | QA PASS：双端门禁 + 浏览器证据 + vision |
| 7 | 总确认 → Draft PR → checks → main | ✅ | ✅ | ✅ | ✅ | 🔄 | 待用户一次总确认 |

## 当前结论
- 直属用例是真实用例，需可点击进入列表查看/编辑（复用现有链路）。
- 图谱用例计数与用例库对齐（全量入图 + 已入库/全量口径）。
- 项目知识/平台研发分域隔离，孤儿实体不再双域重复。
