# 🗂️ Dev 部门项目看板 — Batch 126（测试平台生产对抗性审查 + 修复）

| 字段 | 值 |
|------|-----|
| **项目名称** | 测试平台生产对抗性审查 + 图谱完整性/差异对比引导修复（轻量批次） |
| **关联 PRD** | [batch-126-production-adversarial-review-prd-summary.md](../batch-126-production-adversarial-review-prd-summary.md) |
| **执行器** | codex |
| **分支** | feature/production-adversarial-review |
| **范围** | test-platform-v2 |

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 0 | 生产 24 模块对抗性走查与证据 | ✅ | ✅ | ✅ | ✅ | ⏳ | P1×5 / P2×5 / P3×2，含误报复核 |
| 1 | 图谱完整性与大数据量提示 | ✅ | ✅ | ✅ | ✅ | ⏳ | `fetchGraphView(1000)`；语义 warning token |
| 2 | 差异对比禁用原因引导 | ✅ | ✅ | ✅ | ✅ | ⏳ | 空关键词提示 + tooltip |
| 3 | PRD-lite / QA / Leader / C 条件 | ✅ | ✅ | ✅ | ✅ | ⏳ | 轻量批次工件已齐备 |
| 4 | 本地全量门禁 | ✅ | ✅ | ✅ | ✅ | ⏳ | typecheck/build；Vitest 94 files / 362 tests |
| 5 | 一次总确认 → push → Draft PR → checks → 合入 | ✅ | ✅ | ✅ | 🔄 | ⏳ | **当前位置**：等待用户一次总确认 |

> 状态图例：⏳ 待开始 | 🔄 进行中 | ✅ 已完成 | ❌ 已取消 | 🔒 阻塞中

## 📍 当前位置

```text
Batch 126 — 生产对抗性审查（轻量）
├── ✅ 生产走查与问题分级
├── ✅ 图谱完整性 / 大数据量提示
├── ✅ 差异对比引导
├── ✅ 本地硬门禁与全量回归
└── 🔄 一次总确认 → push → Draft PR → required checks → final audit → squash merge
```
