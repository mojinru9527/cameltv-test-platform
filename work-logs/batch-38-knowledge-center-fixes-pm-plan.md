# Batch 38 — PM Plan
> **PM (🟨)** | Date: 2026-07-23

## 规格摘要
**原始需求**: 知识中心 8 项问题修复（PRD §US-1 ~ US-8）
**目标时间**: 本次 batch 完成，预估 3-4 小时

## 开发任务（按 Slice 拆分）

### Slice 1: 功能门禁开启（US-5/7/8）
**描述**: 将 `rag_enabled`、`knowledge_graph_enabled`、`lanhu_evidence_enabled` 默认值从 False 改为 True
**验收标准**:
- `rag_enabled=True` → reembed 接口不再返回 503
- `knowledge_graph_enabled=True` → graph/extract 和 graph/evolve 接口不再返回 503
- `lanhu_evidence_enabled=True` → lanhu-evidence/jobs 接口不再返回 503
**涉及文件**:
- [test-platform-v2/backend/app/core/config.py](test-platform-v2/backend/app/core/config.py) — 改 3 个 bool 默认值
**参考**: PRD §5 技术考量 > 功能门禁

---

### Slice 2: 前端交互修复（US-2/3/4）
**描述**: 检索结果点击弹窗 + 弹窗尺寸适配长内容 + 验证按钮状态即时更新
**验收标准**:
- 检索结果卡片可点击 → 弹出 Dialog 展示 chunk 详情
- ProjectTab/PlatformTab/SourceListTab 弹窗使用 `max-w-7xl` 适应大内容
- SourceListTab 验证按钮在 API 返回后立即更新本地行状态（不依赖 reload）
**涉及文件**:
- [test-platform-v2/frontend/src/pages/knowledge/components/SearchTab.tsx](test-platform-v2/frontend/src/pages/knowledge/components/SearchTab.tsx) — 添加点击处理 + Dialog
- [test-platform-v2/frontend/src/pages/knowledge/components/ProjectTab.tsx](test-platform-v2/frontend/src/pages/knowledge/components/ProjectTab.tsx) — 弹窗尺寸
- [test-platform-v2/frontend/src/pages/knowledge/components/PlatformTab.tsx](test-platform-v2/frontend/src/pages/knowledge/components/PlatformTab.tsx) — 弹窗尺寸
- [test-platform-v2/frontend/src/pages/knowledge/components/SourceListTab.tsx](test-platform-v2/frontend/src/pages/knowledge/components/SourceListTab.tsx) — 验证按钮即时状态更新
**参考**: PRD §US-2/3/4

---

### Slice 3: 数据归属迁移 + 过滤修正（US-1）
**描述**: 编写数据库迁移脚本，将现有平台研发类知识源的 `knowledge_domain` 更新为 'platform'；修正 ProjectTab 过滤逻辑
**验收标准**:
- 迁移脚本可重复执行（幂等）
- ProjectTab 使用 `knowledge_domain: 'project'` 过滤
- 迁移后"平台研发"标签显示原项目知识中的平台研发数据
**涉及文件**:
- [test-platform-v2/backend/app/core/config.py](test-platform-v2/backend/app/core/config.py) — 或在启动时运行 data migration
- [test-platform-v2/frontend/src/pages/knowledge/components/ProjectTab.tsx](test-platform-v2/frontend/src/pages/knowledge/components/ProjectTab.tsx) — 改 API 过滤参数
**参考**: PRD §US-1 + §5 数据迁移

---

### Slice 4: 批量审核 UI 确认与增强（US-6）
**描述**: ArtifactReviewTab 已有批量审核功能（checkbox + 批量采纳/驳回按钮），本次确认逻辑完备性：确保全选 checkbox 正确联动、添加"全选本页"和"取消全选"快捷操作、确保分页切换时不丢失已选项
**验收标准**:
- 全选 checkbox 正确：勾选=选中当前页所有 pending/approved，取消=清空
- 分页切换后已选项保持
- 批量操作后列表自动刷新
**涉及文件**:
- [test-platform-v2/frontend/src/pages/knowledge/components/ArtifactReviewTab.tsx](test-platform-v2/frontend/src/pages/knowledge/components/ArtifactReviewTab.tsx) — 确认并完善
**参考**: PRD §US-6

## 质量要求
- [x] 响应式（Desktop + Tablet）— 弹窗在移动端应有合理表现
- [x] OpenAPI 同步 — 无 API 变更无需重新生成
- [ ] 前端 typecheck + build 无错误
- [ ] 后端 ruff check 无 F821 错误
- [ ] 无 console 报错/告警
