# 🗂️ Dev 部门项目看板 — Batch 13 · M3 知识图谱建图

> **上一批次**：[batch-12 (M2 向量化与混合检索)](DEV-batch-12-rag-m2-vector-search.md) — ✅ 已交付、合入 develop（PR #26）

## 项目信息

| 字段 | 值 |
|------|-----|
| **里程碑** | M3：知识图谱建图 — 实体提取 + 关系建图 + 可视化 |
| **关联** | batch-11「后续里程碑」M3 定义 + [ADR-0009](../../docs/adr/0009-knowledge-center-agent-continuous-learning.md) |
| **状态** | ✅ 已交付（2026-07-09，4 slices 全部补齐，70 测试全绿） |
| **开关** | `knowledge_graph_enabled`（已建，默认 OFF） |

## ℹ️ 架构决策

| # | 决策 | 方案 |
|---|------|------|
| D1 | 实体提取策略 | 规则驱动（正则 + 字段解析），不依赖外部 LLM（速度/成本/确定性优先） |
| D2 | 实体粒度 | 5 类：`api` / `field` / `requirement` / `test_case` / `defect` |
| D3 | 关系类型 | `contains`（API→字段）、`executed_by`（用例→关联实体）；可扩展 `depends_on`/`affects`/`generated_from` |
| D4 | 可视化 | vis-network ForceAtlas2 力导向布局，浏览器端渲染，不依赖外部图数据库 |
| D5 | 去重策略 | `entity_key = entity_type:p{project_id}:{name}` 稳定唯一键 |

## 📦 已随 M2 分支合入的 M3 代码（基线）

> 以下代码已在 PR #26 中合入 develop，构成 M3 基线。本批次在此基础上补齐缺口。

### 后端

| 层 | 文件 | 行数 | 说明 |
|----|------|------|------|
| ORM 模型 | `models/knowledge.py` L73-107 | ~35 | `KnowledgeEntity` + `KnowledgeRelation`（含 `review_status`） |
| 迁移 | `20260708_0013_knowledge_base.py` | — | 建表 `knowledge_entity` / `knowledge_relation` |
| Schema | `schemas/knowledge.py` L159-244 | ~85 | entity/relation/graph view/extract 请求与响应 |
| 实体服务 | `services/knowledge/entity_service.py` | 396 | 4 类提取器（api_schema/requirement/test_case/defect）+ 关系构建 + 去重 |
| API | `api/v1/knowledge.py` L335-496 | ~160 | 7 端点：extract / entities list / entity detail / relations list / graph view / approve / reject |
| 开关 | `core/config.py` L108 | 1 | `knowledge_graph_enabled: bool = False` |

### 前端

| 层 | 文件 | 行数 | 说明 |
|----|------|------|------|
| 类型 | `types/index.ts` L814-865 | ~50 | `KnowledgeEntity` / `KnowledgeRelation` / `GraphNode` / `GraphEdge` / `GraphView` |
| API | `api/knowledge.ts` L62-68 | ~7 | `fetchGraphView()` / `triggerEntityExtract()` |
| 图谱 Tab | `pages/knowledge/components/GraphTab.tsx` | 342 | vis-network 交互图：节点着色/力导向/缩放/图例/详情/提取按钮 |
| 主页面 | `pages/knowledge/index.tsx` | 69 | 5 Tab（概览/检索/知识源/AI审核台/**图谱**） |
| 依赖 | `package.json` | — | `vis-network ^10.1.0` + `vis-data ^8.0.4` |

## 🎯 本批次交付切片

### Slice 1 — 补齐缺口：实体管理前端 + 关系浏览页

- [ ] **实体列表页**（新 `EntityTab.tsx` 或扩展现有 Tab）：
  - 表格展示 `knowledge_entity`：entity_type Badge / name / description / confidence / review_status / 来源
  - 筛选：entity_type 下拉、keyword 搜索
  - 点击行 → 侧栏详情（关联的 relations 列表）
- [ ] **关系列表组件**：展示 `knowledge_relation`，按 relation_type 分组，每条显示 from→to 实体名 + confidence + evidence
- [ ] **前端 API 补齐**：`api/knowledge.ts` 加 `fetchEntities()` / `fetchEntityDetail()` / `fetchRelations()` / `approveRelation()` / `rejectRelation()`
- [ ] **类型补齐**：确认 `KnowledgeEntity` / `KnowledgeRelation` 类型已在组件中使用（当前仅定义了但未消费）
- [ ] **C1 验收**：实体管理 Tab 可查可筛可点；关系列表可浏览

### Slice 2 — 关系类型扩展 + 提取触发自动化

- [ ] **扩展关系类型**：
  - `affects`：缺陷实体 → API/需求实体（缺陷影响范围）
  - `covers`：用例实体 → 需求实体（用例覆盖需求）
  - `generated_from`：用例实体 → API 实体（AI 从接口生成用例）
- [ ] **扩展 entity_service 提取器**：
  - 从 `defect_case` 提取 affected endpoint（正则匹配 path）
  - 从 `test_case` → `api_schema` 的 `business_ref_id` 关联生成 `covers` + `generated_from`
- [ ] **入库 hook 自动触发提取**（BackgroundTasks，非阻塞）：
  - `ingest_service.py` 的 `make_chunks` 后，若 `knowledge_graph_enabled`，自动调 `extract_and_build_graph_in_new_session`
  - 去重守护：仅对新 chunk 的 source_id 做增量提取（避免全量重跑）
- [ ] **C2 验收**：新增缺陷→自动建 `affects` 关系；新导入接口用例→自动建 `generated_from` 关系；图谱边数增长

### Slice 3 — 图谱治理 + 迭代维度

- [ ] **`knowledge_entity.metadata_json` 利用**：存入 `iteration` / `version` 字段，支持按迭代筛选实体
- [ ] **图谱视图增强**：
  - 支持按 `entity_type` 过滤节点（图例可点击 toggle）
  - 支持按 `iteration` 过滤（下拉选择）
  - 节点 size 按关联关系数动态缩放（度越大节点越大）
- [ ] **`KnowledgeHealth.overview` 补齐**：
  - `low_confidence_relations` 从硬编码 0 → 真实查询 `confidence < 0.5` 的关系数
  - 加 `unreviewed_relations`（`review_status='pending'` 计数）
- [ ] **C3 验收**：图例可交互过滤；概览看板健康指标真实；按迭代可筛

### Slice 4 — 测试 + 文档 + 开关收口

- [ ] `tests/test_knowledge.py` 追加 M3 用例：
  - `TestEntityExtraction`：api/field/requirement 三类提取覆盖
  - `TestRelationBuilding`：contains/executed_by 关系生成
  - `TestGraphApi`：extract 幂等、graph/view 返节点+边、approve/reject 状态变更
  - `TestGraphIngestHook`：入库自动建图（若 Slice 2 实现自动触发）
- [ ] 新增或更新 ADR（如需要）：若实体提取策略/关系类型有重大变化，追加 `0011-knowledge-graph-entity-extraction.md`
- [ ] `knowledge_graph_enabled` 开关文档：在配置注释中写明开启前提（已入库数据 + 已过治理审核）
- [ ] **C4 验收**：`pytest tests/test_knowledge.py` M3 扩展集通过；ADR 定稿（如需）

## 范围边界（M3 不做）

- ❌ LLM 驱动的实体提取（关系抽取仍用规则）→ LLM 增强留 M4 Agent 阶段
- ❌ 图数据库（Neo4j/JanusGraph）→ 保持 SQLite/PG 内建表，够用
- ❌ 跨项目实体关联 → 仅当前项目维度
- ❌ 时序图谱（实体变更历史）→ M5/M6 迭代知识包阶段

## 风险

| 风险 | 缓解 |
|------|------|
| 规则提取覆盖不足（特殊 API path 格式） | 正则渐进补强；M4 可用 LLM 补充低频模式 |
| 实体膨胀（每次入库创建大量重复实体） | `entity_key` 唯一去重；增量提取只处理新 source_id |
| vis-network 大数据量性能（>500 节点） | 默认 limit 200；按 entity_type 过滤减载 |
| 关系类型语义不清 | 每种 relation_type 在代码注释中明确定义 + ADR 留痕 |

## 参考

- [vis-network 文档](https://visjs.github.io/vis-network/docs/network/)
- [ForceAtlas2 论文](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0098679)

## 落地记录（batch-13 · feature/knowledge-m3-graph）

| Slice | 提交 | 验收 |
|---|---|---|---|
| S1 实体管理前端 | 本批次 | C1 ✅ EntityTab + 6 API 函数 + 类型补齐 |
| S2 关系类型扩展+自动触发 | 本批次 | C2 ✅ affects/covers/generated_from + 5 入库 hook 自动触发 |
| S3 图谱治理+迭代维度 | 本批次 | C3 ✅ 类型过滤 toggle + 节点度缩放 + 健康指标真实化 |
| S4 测试+文档+收口 | 本批次 | C4 ✅ 22 M3 测试 + duplicate commit 修复 + Pydantic v2 兼容 |

**证据**：`pytest tests/test_knowledge.py -q` → **70 passed**；`npx tsc --noEmit` → 0 error（M3 文件）。
