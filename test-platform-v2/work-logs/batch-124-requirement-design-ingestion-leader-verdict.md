# Batch 124 — Leader Verdict（需求/设计稿入库 + 图谱 P0 崩溃修复）

> **Leader (🎯)** | Date: 2026-08-08 | Decision: 有条件通过（C124-1/2 部署后闭环）

## 评审摘要

| 维度 | 评分 | 备注 |
|------|------|------|
| 实现质量 | 4.5/5 | 图谱 P0 修复 + 需求入库垂直切片全落地；门禁全绿（typecheck/build/ruff/pytest 79/79） |
| 风险 | 低 | 后端仅新增端点（无 schema 变更）；前端知识源详情加画廊 |
| 覆盖 | 4/5 | 图谱崩溃根因修复；需求/设计稿入库链路就绪（147 页/3526 图片）；生产导入待部署 |

## 关键决策（已批准）

1. **图谱 P0**：`graph_view` 去重兜底，历史重复实体不再崩页；重复实体清理脚本登记（C123-2 走查发现）。
2. **需求/设计稿入库**：新端点按 content_hash 幂等入库（source_type=requirement，文本+图片），图片存平台 storage 并由安全路由服务；前端知识源详情展示设计稿画廊。输入源=本地 axure_extract_test（147 页 / 3526 图）。
3. **入库脚本分批**：5 页/批 base64 上传，支持 --limit/--filter 断点续导。

## 抽检通过

- ✅ `graph_view` 去重 + `test_graph_dedup.py` 1/1（重复实体不崩、节点唯一、边有效）
- ✅ `design-assets/import` + `test_design_asset_import.py` 1/1（幂等、图片服务、路径逃逸防护）
- ✅ `import-requirement-design.py` dry-run 147 页/3526 图
- ✅ 门禁：typecheck/build/ruff F821/pytest 79/79

## 判决

**有条件通过**。合入部署后：C124-1 生产导入需求/设计稿并验证知识中心可查（文本+图片）；C124-2 生产图谱页复测截图。

## 下一批次 Leader 条件

- **C124-1**: 生产部署后执行 import-requirement-design.py 导入 147 页/3526 图片，验证知识中心可查看文本+设计稿
- **C124-2**: 生产图谱页复测（P0 修复后不再崩溃，截图证据）
- **C124-3**: 运营后台需求（axure_extract_61930a83，70+ 页）同链路入库（P3）

## 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| 图谱生产崩溃根因=重复实体 id（历史提取重复） | graph_view 去重兜底 + 清理脚本 | knowledge.py（已实现） |
| 需求/设计稿"用不上平台"= 无完整文本+图片入库链路 | 新增 design-assets 入库端点+脚本+画廊 | knowledge.py / import-requirement-design.py（已实现） |
| 新端点模块级 Path 依赖遗漏 | 测试暴露 → 顶部导入补齐 | knowledge.py |

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 1d / 实际 0.5d | 0/0/2/1 | 1 | 模块级导入遗漏 | 新端点先核对顶部导入；测试覆盖图片服务与逃逸 |

---

## 补充判决（2026-08-08 v2：用例基座接入 + 模块树全量修复）

### 评审摘要（补充）

| 维度 | 评分 | 备注 |
|------|------|------|
| 实现质量 | 4.5/5 | 功能用例基座接入 7 份文档权威要求；两 skill 深度用例补充层；后端生成链路真正加载权威文件；模块树 192→218 全量 |
| 风险 | 低 | 纯文档/skill 变更 + ai_service 只读加载逻辑 + 模块树证据文件；无 schema 变更 |
| 覆盖 | 4.5/5 | 功能/接口两基座统一「基础用例→深度用例」；运营后台 74 页全量入库准备（原 65 节点丢 23 子页已修） |

### 抽检通过（补充）

- ✅ `test_ai_skill_context.py` 3/3（functional/api 均加载权威输出要求；skill 目录优先）
- ✅ `test_requirement_module_tree_import.py` 1/1；`test_ai_extraction_fallback` + `test_ai_generate_chunked` 7/7
- ✅ ruff F821（ai_service.py / build_lanhu_hierarchy.py）
- ✅ 模块树完整性：218 节点（35 模块/183 页/4781 设计稿）、无重复 path、lanhu_page_id 全部可解析、depth≥3 父节点 0 缺失

### 判决

维持**有条件通过**。新增 C124-3 就绪度提升：运营后台需求（axure_extract_61930a83）**74 页全量 hierarchy（88 节点）已生成**，部署后按 C124-3 导入即可。

### 流程回写（补充）

| 发现 | 处理 | 落点 |
|------|------|------|
| 用户端导出 document.js 实为运营后台 sitemap 快照 | 用户端走 enrich 模式保留功能地图归级；脚本双模式 | build_lanhu_hierarchy.py |
| 运营后台 hierarchy 只走 2 层丢 23 子页 | 全量解析（Folder/Wireframe url 字段）→ 88 节点 | build_lanhu_hierarchy.py / requirement-module-tree.json |
| 用户端 3 页在 tree 中缺失（意见反馈/主播菜单/更新日志） | 恢复 → 130 节点 | requirement-module-tree.json |
| 接口 skill 曾未接入用户重新整理的输出用例要求 | 接口测试输出用例要求.md 已入加载链（v1 修复）+ 本次补功能侧对等 | ai_service.py |
