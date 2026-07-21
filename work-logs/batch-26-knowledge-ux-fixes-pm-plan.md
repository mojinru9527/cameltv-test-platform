# Batch 26-2 — 知识中心 UX 修复 PM Plan
> **PM (🟨)** | Date: 2026-07-21

## 规格摘要
**原始需求**: 用户走查知识中心全模块后发现 7 类 UX 缺陷，核心是「数据渲染了但不可交互」
**目标时间**: 1 个 batch（约 3 小时），分 7 个 Slice 推进

---

## 开发任务（按优先级排列）

### [P0] Slice 1: 项目知识 Tab — 添加知识源点击详情弹窗
**描述**: 在 ProjectTab 中，给每个知识源条目 `<div>` 添加 onClick 处理器，复用 SourceListTab 的弹窗组件（fetchSourceChunks + Dialog）展示详情
**验收标准**:
- [ ] 点击任意知识源条目 → 弹出详情弹窗
- [ ] 弹窗包含：原始内容 + AI 切片列表 + 元数据摘要（保鲜评分/时间/来源）
- [ ] 弹窗尺寸 ≥ max-w-4xl, max-h-[90vh]
- [ ] 批次分组卡片保持现有交互（始终展开）
**涉及文件**:
- [ProjectTab.tsx](test-platform-v2/frontend/src/pages/knowledge/components/ProjectTab.tsx) — 添加状态管理 + 弹窗 + onClick
**参考**: PRD §P1-1 / SourceListTab.tsx L75-83 弹窗模式

---

### [P0] Slice 2: 平台研发 Tab — 分区折叠 + 知识源点击详情
**描述**: PlatformTab 改造：(a) 分区标题添加展开/折叠切换，默认仅展开第一个分区；(b) 知识源条目添加 onClick → 弹窗
**验收标准**:
- [ ] 首次加载：仅 area（问题模式）分区展开，其余折叠
- [ ] 点击分区标题（CardHeader）→ 该分区展开/收起（带动画或直接切换）
- [ ] 点击知识源条目 → 弹出详情弹窗（同 Slice 1 的弹窗）
- [ ] 折叠状态用图标指示（ChevronDown/ChevronRight）
**涉及文件**:
- [PlatformTab.tsx](test-platform-v2/frontend/src/pages/knowledge/components/PlatformTab.tsx) — 添加展开/折叠状态 + 弹窗
**参考**: PRD §P1-2

---

### [P1] Slice 3: Tab 顺序 + 默认概览 + 检索提升
**描述**: (a) 概览 Tab 移到第一位，设为默认 Tab；(b) 检索栏从 Tab 中提取到页面顶部常驻
**验收标准**:
- [ ] `/knowledge` 无 `?tab=` 参数时 → 默认显示概览
- [ ] Tab 栏顺序：概览 | 项目知识 | 平台研发 | 检索 | 知识源 | AI审核台 | 图谱 | 实体 | 迭代 | Wiki | 差异对比 | Skills
- [ ] 搜索栏在 PageHeader 下方、Tab 栏上方常驻显示（输入框 + 搜索按钮，回车触发）
- [ ] 搜索栏在任意 Tab 下都可见可用
- [ ] 常驻搜索栏功能与 SearchTab 一致（hybrid/keyword/vector 切换）
**涉及文件**:
- [index.tsx](test-platform-v2/frontend/src/pages/knowledge/index.tsx) — Tab 顺序 + 默认值 + 搜索栏
- [SearchTab.tsx](test-platform-v2/frontend/src/pages/knowledge/components/SearchTab.tsx) — 提取搜索栏为独立组件或直接 inline
**参考**: PRD §P1-3, §P2-1

---

### [P1] Slice 4: 检索全状态 + 图谱知识域隔离
**描述**: (a) 确保检索 API 不过滤 status，搜索全部切片（含 deprecated/archived）；(b) GraphTab 添加项目知识/平台研发切换
**验收标准**:
- [ ] 检索结果包含各种状态的切片（不限于 active）
- [ ] 若后端 searchKnowledge 有 status=active 过滤 → 移除
- [ ] GraphTab 顶部添加 Toggle/Tabs：「项目知识 | 平台研发」
- [ ] 切换域后重新调用 fetchGraphView 并传入 knowledge_domain 参数
- [ ] 后端 GraphView API 支持 knowledge_domain 查询参数
**涉及文件**:
- [SearchTab.tsx](test-platform-v2/frontend/src/pages/knowledge/components/SearchTab.tsx) — 确认/修改检索参数
- [GraphTab.tsx](test-platform-v2/frontend/src/pages/knowledge/components/GraphTab.tsx) — 添加域切换
- [knowledge.ts](test-platform-v2/frontend/src/api/knowledge.ts) — fetchGraphView 加参数
- [knowledge.py](test-platform-v2/backend/app/api/v1/knowledge.py) — GraphView 端点可能需加 knowledge_domain 参数（待确认）
**参考**: PRD §P2-1, §P2-2

---

### [P2] Slice 5: 弹窗 Select 错位修复 + 内容放大
**描述**: (a) 修复 Dialog 内 Select 下拉错位；(b) 统一所有弹窗尺寸标准
**验收标准**:
- [ ] Dialog 内 Select 下拉不再偏移/截断（方案：SelectContent 添加 `position="popper"` 或调整 z-index）
- [ ] 所有知识中心弹窗最小宽度 max-w-4xl（约 56rem/896px）
- [ ] 弹窗内容文字最小 text-sm（14px），代码区最小 text-sm
- [ ] 弹窗高度 ≥ 85vh
**涉及文件**:
- [SourceListTab.tsx](test-platform-v2/frontend/src/pages/knowledge/components/SourceListTab.tsx) — 弹窗尺寸
- [ArtifactReviewTab.tsx](test-platform-v2/frontend/src/pages/knowledge/components/ArtifactReviewTab.tsx) — 弹窗尺寸 L317-341
- [ProjectTab.tsx](test-platform-v2/frontend/src/pages/knowledge/components/ProjectTab.tsx) — 新增弹窗的尺寸
- [PlatformTab.tsx](test-platform-v2/frontend/src/pages/knowledge/components/PlatformTab.tsx) — 新增弹窗的尺寸
- [select.tsx](test-platform-v2/frontend/src/components/ui/select.tsx) — SelectContent z-index/position（如果需要全局修复）
**参考**: PRD §P3-1, §P3-2

---

### [P2] Slice 6: AI 审核台批量操作
**描述**: 扩展 ArtifactReviewTab 的批量能力：支持批量采纳（pending→approved）、批量驳回（pending→rejected）
**验收标准**:
- [ ] 筛选「待审核」时 → 全选 checkbox + 「批量采纳」「批量驳回」按钮出现
- [ ] 批量采纳：逐条调用 approveArtifact API，成功/失败计数 → toast 汇总
- [ ] 批量驳回：弹出驳回原因输入框（统一原因）→ 逐条调用 rejectArtifact
- [ ] 批量导入功能保持现有逻辑
- [ ] 操作完成后自动刷新列表
**涉及文件**:
- [ArtifactReviewTab.tsx](test-platform-v2/frontend/src/pages/knowledge/components/ArtifactReviewTab.tsx) — 扩展批量操作逻辑
**参考**: PRD §P3-3

---

### [P3] Slice 7: 知识溯源字段增强
**描述**: 增加知识溯源能力：KnowledgeSource 模型加 module_name 字段，前端弹窗展示溯源链路
**验收标准**:
- [ ] KnowledgeSource 模型新增 `module_name: str | null`（Alembic 迁移）
- [ ] 知识源创建时（ingest_service）尝试从 source_ref 提取模块名
- [ ] 前端 KnowledgeSource 类型加 `module_name?: string`
- [ ] 弹窗元数据区展示：项目 → 模块 → 来源（source_ref）→ 类型（source_type）的溯源链路
- [ ] 已有数据的 module_name 可在后续逐步回填（非阻塞）
**涉及文件**:
- [knowledge.py (model)](test-platform-v2/backend/app/models/knowledge.py) — 添加 module_name 列
- [knowledge.py (schema)](test-platform-v2/backend/app/schemas/knowledge.py) — schema 加字段
- [ingest_service.py](test-platform-v2/backend/app/services/knowledge/ingest_service.py) — record_source 时提取 module_name
- [types/index.ts](test-platform-v2/frontend/src/types/index.ts) — KnowledgeSource 加 module_name
- [SourceListTab.tsx](test-platform-v2/frontend/src/pages/knowledge/components/SourceListTab.tsx) — 弹窗溯源展示
- Alembic 迁移脚本

---

## 任务依赖图

```
Slice 1 (ProjectTab 弹窗) ────┐
                               ├─> Slice 5 (弹窗统一放大) ──> Slice 7 (溯源)
Slice 2 (PlatformTab 弹窗) ───┘         │
                                         └─> Slice 6 (批量审核)
Slice 3 (Tab顺序+检索提升) ──> Slice 4 (检索全状态+图谱域隔离)
```

- Slice 1-2 可并行（独立组件）
- Slice 3-4 可并行于 Slice 1-2
- Slice 5 依赖 Slice 1-2（新增弹窗统一尺寸）
- Slice 7 依赖 Slice 1-2 + Slice 5（弹窗已就绪后再增加溯源）

## 质量要求
- [ ] TypeScript 编译 0 error (`npx tsc --noEmit`)
- [ ] 无 console 报错/告警
- [ ] 响应式：Desktop (1280+) 完整布局，弹窗在 Tablet (768-1024) 也能正常显示
- [ ] 后端 Alembic 迁移可逆（downgrade 可用）
- [ ] 已有测试不回归
