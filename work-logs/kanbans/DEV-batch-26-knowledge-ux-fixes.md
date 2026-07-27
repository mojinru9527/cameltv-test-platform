# DEV 看板 — Batch 26-2 知识中心 UX 修复

> **Dev (💻)** | 创建: 2026-07-21 | 状态: 🔄 编码中

## 架构决策

| 维度 | 决策 |
|------|------|
| **弹窗复用** | ProjectTab/PlatformTab 直接内联 SourceListTab 的弹窗逻辑（fetchSourceChunks + Dialog），不抽取为独立组件（避免过度抽象） |
| **分区折叠** | PlatformTab 用 `useState<Set<string>>` 管理展开分区，初始值 `new Set(['area'])` |
| **检索提升** | 从 SearchTab 提取核心搜索 UI 到 index.tsx，SearchTab 保留原有完整功能（作为 Tab 落地页） |
| **图谱域隔离** | 后端 graph_view 端点需新增 JOIN 查询：KnowledgeEntity JOIN KnowledgeSource ON source_id WHERE knowledge_domain=X。前端传 `?knowledge_domain=project\|platform` |
| **搜索全状态** | `search_service.py` L85 移除 `KnowledgeChunk.status == "active"` 过滤 |
| **Select 错位** | SelectContent 加 `position="popper"` + `sideOffset={4}` 对齐；弹窗内 Select portal 指向 Dialog |
| **module_name** | KnowledgeSource 加 nullable 字段，Alembic 迁移 |

## 实现文件

### 前端
| 文件 | 改动点 |
|------|--------|
| [index.tsx](test-platform-v2/frontend/src/pages/knowledge/index.tsx) | Tab 顺序 + 默认概览 + 搜索栏常驻 |
| [ProjectTab.tsx](test-platform-v2/frontend/src/pages/knowledge/components/ProjectTab.tsx) | 弹窗逻辑 + onClick |
| [PlatformTab.tsx](test-platform-v2/frontend/src/pages/knowledge/components/PlatformTab.tsx) | 折叠分区 + 弹窗逻辑 |
| [GraphTab.tsx](test-platform-v2/frontend/src/pages/knowledge/components/GraphTab.tsx) | 知识域切换 Toggle |
| [ArtifactReviewTab.tsx](test-platform-v2/frontend/src/pages/knowledge/components/ArtifactReviewTab.tsx) | 批量采纳/驳回 |
| [SourceListTab.tsx](test-platform-v2/frontend/src/pages/knowledge/components/SourceListTab.tsx) | 弹窗尺寸 + 溯源行 |
| [types/index.ts](test-platform-v2/frontend/src/types/index.ts) | KnowledgeSource 加 module_name |
| [knowledge.ts](test-platform-v2/frontend/src/api/knowledge.ts) | fetchGraphView 加 knowledge_domain 参数 |

### 后端
| 文件 | 改动点 |
|------|--------|
| [knowledge.py (models)](test-platform-v2/backend/app/models/knowledge.py) | KnowledgeSource 加 module_name |
| [knowledge.py (schemas)](test-platform-v2/backend/app/schemas/knowledge.py) | schema 加 module_name |
| [knowledge.py (api)](test-platform-v2/backend/app/api/v1/knowledge.py) | graph_view 端点加 domain 过滤 JOIN |
| [search_service.py](test-platform-v2/backend/app/services/knowledge/search_service.py) | 移除 status=active 过滤 |
| [ingest_service.py](test-platform-v2/backend/app/services/knowledge/ingest_service.py) | record_source 时提取 module_name |
| 迁移脚本 | Alembic: add module_name to knowledge_source |

---

## Slice 推进记录

### 📝 Slice 1: ProjectTab 弹窗
- **方案**: 内联 Dialog + fetchSourceChunks，复用 SourceListTab L218-335 弹窗结构
- **状态**: ⬜ 待编码

### 📝 Slice 2: PlatformTab 折叠+弹窗
- **方案**: `useState<Set<string>>(new Set(['area']))` 管理展开分区；onClick → Dialog
- **状态**: ⬜ 待编码

### 📝 Slice 3: Tab 顺序+默认概览+搜索提升
- **方案**: tab 默认 'overview'；PageHeader 下方加搜索栏 JSX；SearchTab 保持不动
- **状态**: ⬜ 待编码

### 📝 Slice 4: 检索全状态+图谱域隔离
- **方案**: 后端 search_service 去 status 过滤；graph_view 加 JOIN + domain 参数
- **状态**: ⬜ 待编码

### 📝 Slice 5: 弹窗放大+Select 修复
- **方案**: 统一弹窗 max-w-5xl；SelectContent position="popper"
- **状态**: ⬜ 待编码

### 📝 Slice 6: AI 审核台批量操作
- **方案**: 全选→批量并发调用 approveArtifact/rejectArtifact；toast 汇总
- **状态**: ⬜ 待编码

### 📝 Slice 7: 知识溯源字段
- **方案**: 模型加 module_name；弹窗加溯源面包屑：项目 → 模块 → 来源
- **状态**: ⬜ 待编码

---

## 性能基准
- 弹窗打开 < 500ms（fetchSourceChunks 1 次 API 调用）
- 图谱域切换 < 2s（刷新 vis-network）
- 批量操作 N 条 < N×200ms（逐条 API 并发）
- TypeScript: 0 error
