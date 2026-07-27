# Batch 26-2 — 知识中心 UX 修复 Leader Verdict
> **Leader (🎯)** | Date: 2026-07-21 | Decision: APPROVED

## 评审摘要

| 维度 | 评分 | 备注 |
|------|------|------|
| 需求分析 | ⭐⭐⭐⭐⭐ | 7 个问题精准定位，PRD 有量化基线/目标 |
| 任务拆解 | ⭐⭐⭐⭐⭐ | 7 Slice 粒度合理（30-60min），依赖关系清晰 |
| 设计规范 | ⭐⭐⭐⭐ | 组件规格完整，RF4/RF7 识别到位 |
| 技术方案 | ⭐⭐⭐⭐ | 关键发现：search_service 有 status=active 过滤需移除；graph_view 需 JOIN 查询 |
| 测试覆盖 | ⭐⭐⭐⭐⭐ | 28 个检查点，覆盖交互/尺寸/API/性能 |
| 风险 | 🟢 低 | 改动集中在 2 个前端组件 + 3 处后端微调 |
| 覆盖 | 全链路 | 前端 8 文件 + 后端 5 文件 + 1 迁移 |

---

## 关键发现（技术审查）

### F1: 搜索服务有隐式 status 过滤
`search_service.py:85` / `vector_store.py:88` 硬编码 `KnowledgeChunk.status == "active"`，导致检索无法命中 deprecated/archived 切片。Slice 4 需要移除该过滤条件（或改为可配置参数，默认不过滤）。

### F2: 图谱端点不支持知识域过滤
`knowledge.py:597` 的 `graph_view` 端点仅按 `project_id` 过滤，KnowledgeEntity 表无 `knowledge_domain` 列。需要 JOIN KnowledgeSource 来实现域过滤：
```python
select(KnowledgeEntity).join(
    KnowledgeSource, KnowledgeEntity.source_id == KnowledgeSource.id
).where(
    KnowledgeEntity.project_id == pid,
    KnowledgeSource.knowledge_domain == domain,
)
```

### F3: Select 弹窗错位是 Radix 已知问题
根因：Radix SelectPortal 默认挂到 `document.body`，Dialog 也是 Portal，各自的 z-index=50 导致 SelectContent 被 Dialog 的 stacking context 影响。修复方案：
- `<SelectContent position="popper" sideOffset={4} className="z-[60]" />`
- 或在 `select.tsx` 中全局设置 `position="popper"`

---

## 最终优化清单

| # | 优先级 | Slice | 问题 | 涉及文件 | 估时 |
|---|--------|-------|------|---------|------|
| 1 | 🔴 P0 | S1 | ProjectTab 知识源添加 onClick → 详情弹窗 | ProjectTab.tsx | 30min |
| 2 | 🔴 P0 | S2 | PlatformTab 分区折叠 + onClick → 详情弹窗 | PlatformTab.tsx | 40min |
| 3 | 🟠 P1 | S3 | 概览 Tab 第一位 + 默认显示 | index.tsx L26 | 5min |
| 4 | 🟠 P1 | S3 | 搜索栏提升到页面顶部常驻 | index.tsx + SearchTab.tsx | 30min |
| 5 | 🟠 P1 | S4 | 检索去掉 status=active 过滤，搜索全状态切片 | search_service.py L85 | 10min |
| 6 | 🟠 P1 | S4 | 图谱区分项目知识/平台研发 | GraphTab.tsx + knowledge.py (api) | 35min |
| 7 | 🟡 P2 | S5 | 所有弹窗 Select 下拉错位修复 | select.tsx + 各弹窗组件 | 20min |
| 8 | 🟡 P2 | S5 | 所有弹窗内容放大（max-w-5xl, text-sm起步） | 5 个弹窗组件 | 25min |
| 9 | 🟡 P2 | S6 | AI 审核台批量采纳/驳回 | ArtifactReviewTab.tsx | 30min |
| 10 | ⚪ P3 | S7 | 知识溯源字段 module_name | Model + Schema + 迁移 + ingest + 前端 | 35min |

**总计**: 约 4.5 小时（含验证时间）

---

## 抽检通过

- ✅ [ProjectTab.tsx:76](test-platform-v2/frontend/src/pages/knowledge/components/ProjectTab.tsx#L76) — 确认 `<div>` 无 onClick，需要添加
- ✅ [PlatformTab.tsx:123](test-platform-v2/frontend/src/pages/knowledge/components/PlatformTab.tsx#L123) — 确认 `<div>` 无 onClick，需要添加
- ✅ [PlatformTab.tsx:113-150](test-platform-v2/frontend/src/pages/knowledge/components/PlatformTab.tsx#L113-L150) — 确认所有分区始终展开（无折叠逻辑）
- ✅ [index.tsx:26](test-platform-v2/frontend/src/pages/knowledge/index.tsx#L26) — 确认默认 tab='project'
- ✅ [search_service.py:85](test-platform-v2/backend/app/services/knowledge/search_service.py#L85) — 确认 `KnowledgeChunk.status == "active"` 硬编码过滤
- ✅ [knowledge.py:597-613](test-platform-v2/backend/app/api/v1/knowledge.py#L597-L613) — 确认 graph_view 无 knowledge_domain 参数
- ✅ [ArtifactReviewTab.tsx](test-platform-v2/frontend/src/pages/knowledge/components/ArtifactReviewTab.tsx) — 确认有批量导入但缺批量采纳/驳回
- ✅ KnowledgeSource 模型无 module_name 字段

---

## 判决
**APPROVED → 进入 Slice 1 编码阶段。**

### 执行顺序建议
```
Slice 1 + Slice 2 并行（独立组件，无文件冲突）
    ↓
Slice 3（Tab/搜索）
    ↓
Slice 4（检索+图谱后端微调）
    ↓
Slice 5（弹窗统一样式）
    ↓
Slice 6（批量审核）
    ↓
Slice 7（溯源字段，收尾）
```

## 下一批次 Leader 条件
- C1: Slice 5 完成后，所有弹窗经 Design 走查确认尺寸达标
- C2: Slice 4 完成后，图谱两域数据隔离确认（截图对比）
- C3: 全部 Slice 完成后，运行 28 个 QA 检查点，通过率 ≥ 90%
