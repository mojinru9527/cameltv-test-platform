# 🗂️ Dev 看板 — Batch 130（用例模块聚合与异常覆盖加固）

| 字段 | 值 |
|------|-----|
| 模式 | full |
| 执行器 | codex |
| 分支 | feature/batch-130-case-module-quality |
| Worktree | F:/CamelTv-worktrees/codex-batch-130-case-module-quality |
| 前/后端端口 | 5219 / 8049 |
| 基线 | origin/main@ebf4700 |
| PRD | `../batch-130-case-module-quality-prd-summary.md` |
| 实施计划 | `../../../docs/superpowers/plans/2026-08-09-case-module-aggregation-quality.md` |

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 0 | Product / PM / Design / 实施计划 | ✅ | ✅ | ✅ | ✅ | ⏳ | full batch；C125-3/C122-4 纳入 |
| 1 | taxonomy 规范化纯函数 | ✅ | ✅ | ✅ | ✅ | ⏳ | 去终端壳层、合并路径别名 |
| 2 | taxonomy/list 规范筛选契约 | ✅ | ✅ | ✅ | ✅ | ⏳ | surface/domain/module/nature/case_id |
| 3 | 用例服务异常筛选与标签 | ✅ | ✅ | ✅ | ✅ | ⏳ | PC/移动端/安卓不再做树节点 |
| 4 | 稳定 ID 与幂等全量导入 | ✅ | ✅ | ✅ | ✅ | ⏳ | 修复跨模块 TC-xxx 冲突和假查重 |
| 5 | 38 模块 adversarial overlay + audit | ✅ | ✅ | ✅ | ✅ | ⏳ | 故障恢复 + 重复/并发 |
| 6 | 全量 QA / 浏览器 / Leader | ✅ | ✅ | ✅ | ✅ | ⏳ | 三视口 + 数据审计全绿 |
| 7 | 总确认 → Draft PR → checks → main | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ | 未获总确认不得 push |

## 当前结论

- 根因不是简单缺少负向数量：全量基础资产非 happy-path 已达 49.8%，但尚未正确导入生产。
- 导入器存在跨模块 ID 冲突和假查重两个 P1 阻断，必须先修再执行 C125-3。
- 终端维度保留为 tags/正文；taxonomy 只按真实业务模块聚合。
- 全量资产补充 recovery 与 duplicate/concurrency overlay 后再通过审计门禁。
- 7,879 条资产最终审计 PASS：38/38 正负向、38/38 双对抗维度、来源端别错配 0。
- 本地 QA 与 Leader 已通过；尚未获得总确认，未 push、未创建 PR、未合入或发布。
