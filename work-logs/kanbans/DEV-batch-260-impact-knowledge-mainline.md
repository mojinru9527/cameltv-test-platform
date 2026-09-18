# 🗂️ Dev 部门项目看板 — Batch 260（B3 知识主线）

## 📋 项目信息

| 字段 | 值 |
|------|-----|
| **项目名称** | batch-260-impact-knowledge-mainline（B3 落地批次） |
| **关联 PM 计划** | [batch-260-impact-knowledge-mainline-pm-plan.md](../batch-260-impact-knowledge-mainline-pm-plan.md) |
| **关联 PRD** | [batch-260-impact-knowledge-mainline-prd-summary.md](../batch-260-impact-knowledge-mainline-prd-summary.md) |
| **批次档位** | 完整批次（数据模型 + 新接口 + 前端行为变更） |
| **总预估工时** | 20h |
| **看板创建** | 2026-09-19 |
| **最后更新** | 2026-09-19 |

## 🎯 交付切片进度

| # | Slice | 方案 | 编码 | 自测 | 审批 | 合入 | 备注 |
|---|-------|:----:|:----:|:----:|:----:|:----:|------|
| 1 | `ImpactEdge` 模型 + 迁移（B3-1） | ✅ | ✅ | ✅ | ⏳ | ⏳ | 13 例；迁移演练通过 |
| 2 | 关联构建 + 覆盖率证据（B3-2） | ✅ | ✅ | ✅ | ⏳ | ⏳ | 9 例；真实数据数字 → C260-1 |
| 3 | 「改了 X 要跑哪些」查询（B3-3） | ✅ | ✅ | ✅ | ⏳ | ⏳ | 13 例；含 2 条防 N+1 断言 |
| 4 | 复用建议命中率埋点（B3-4） | ✅ | 🔄 ⬅️ | ⏳ | ⏳ | ⏳ | **当前位置**，主体已存在只补埋点 |
| 5 | 知识中心 Tab 收敛 ≤3（B3-5） | ✅ | ⏳ | ⏳ | ⏳ | ⏳ | 前端 |

## 📍 当前位置

```
Batch 260 — Slice 4：复用建议命中率埋点
├── 已完成: Slice 1（ImpactEdge）、Slice 2（关联构建）、Slice 3（查询 API + 未覆盖缺口）
│          commit b8e3bb32 / 09fa9a7a / 64787ae4 / 249e0632 / d93d3ef0 / 2c60c78b
├── 🔄 进行中: 复用建议命中率埋点（B11/B12 主体已存在，只补埋点 + 聚合，不改既有返回契约）
├── 未决: C260-1（真实体育资产上的覆盖率数字需在目标环境跑回填脚本产出；本机库无该数据）
├── ⏳ 待审批: 本批次一次总确认（推送 + Draft PR + required checks 通过后合入）
└── ⏳ 下一步: Slice 5（知识中心 Tab 收敛 ≤3）→ QA/Leader
```

## 📜 批次记录

### Batch 258 — B1 落地（已合入）
- **产出**: PR #477 → squash `2ced1baf`（16 commits / 43 文件）；审计 S1/S2/S3 闭合
- **遗留**: C258-1（Test5 真机）、C258-2（→ B2-1 已关闭）

### Batch 259 — B2 落地（已合入）
- **产出**: PR #478 → squash `573f5c12`（15 commits / 33 文件）；审计 S4/S5 关闭、S6 部分关闭
- **遗留**: C259-1（搜索直达）、C259-2（内核级沙箱属部署层）

### Batch 260 — B3 知识主线（进行中）
- **产出**: 待补
- **审批**: 待一次总确认
- **耗时**: 进行中

## ⚠️ 阻塞与风险

| 阻塞项 | 严重度 | 描述 | 需要谁 | 记录时间 |
|--------|:------:|------|--------|----------|
| 能力重复风险 | P2 | B3-3/B3-4 的主体能力已以 B11/B12 形式存在；若按 backlog 字面从零实现会产生第二份影响面实现（S1/S5 模式） | 本批已按"复用优先"落进 PRD §3 非目标 | 2026-09-19 |
| 试点数据依赖 | P2 | B3-2 的「体育模块关联覆盖率 ≥90%」依赖库内已有的体育资产；若库为空则只能给脚本 + 空集证据 | 环境 | 2026-09-19 |

## 🔗 相关工件

| 工件 | 路径 | 状态 |
|------|------|:----:|
| PRD | [link](../batch-260-impact-knowledge-mainline-prd-summary.md) | ✅ |
| PM 计划 | [link](../batch-260-impact-knowledge-mainline-pm-plan.md) | ✅ |
| 设计规范 | [link](../batch-260-impact-knowledge-mainline-design-spec.md) | ✅ |
| QA 报告 | `../batch-260-impact-knowledge-mainline-qa-report.md` | ⏳ |
| Leader 判决 | `../batch-260-impact-knowledge-mainline-leader-verdict.md` | ⏳ |
