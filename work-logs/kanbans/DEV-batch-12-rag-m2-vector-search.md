# 🗂️ Dev 部门项目看板 — Batch 12 · M2 向量化与混合检索

> **上一批次**：[batch-11 (M0+M1)](DEV-batch-11-rag-knowledge.md) — ✅ 已交付、合入 develop（PR #15）

## 项目信息

| 字段 | 值 |
|------|-----|
| **里程碑** | M2：切片向量化 + 混合检索 |
| **关联 PRD** | [RAG知识图谱与Agent持续学习能力落地执行文档 §M2](../../test-platform-v2/docs/RAG知识图谱与Agent持续学习能力落地执行文档.md) |
| **ADR** | [ADR-0010](../../docs/adr/0010-knowledge-vector-embedding-hybrid-retrieval.md)（已接受） |
| **状态** | ✅ 已落地（Slice 1–5 提交完成，PR 待 Product→Design→QA→Leader 评审） |
| **开关** | `rag_enabled`（已建，默认 OFF） |

## ℹ️ 架构决策（已锁定）

| # | 决策 | 方案 |
|---|------|------|
| D1 | 嵌入来源 | `fastembed` BAAI/bge-small-zh-v1.5（onnx, CPU, 512d, 离线不外传） |
| D2 | 向量存储 | 分层抽象：dev SQLite blob + NumPy 暴力余弦；升 PG 切 pgvector |
| D3 | 检索方式 | RRF 融合：关键词(LIKE/FTS) + 向量余弦 → /knowledge/search |
| D4 | 管线触发 | BackgroundTasks post-commit（不阻塞）；存量→`/reembed` 回填 |

## 交付切片

### Slice 1 — 向量化基石：嵌入服务 + knowledge_vector 表 + 在线嵌入

- [ ] `requirements.txt` 加 `fastembed`、`numpy`
- [ ] 迁移 `0014_knowledge_vector`（承 `0013`）：`knowledge_vector(id, chunk_id unique-fk, project_id, model, dim, vec BLOB float32, created_at)`
- [ ] 模型 `KnowledgeVector` 对齐上述字段
- [ ] `backend/app/services/knowledge/embedding_service.py`：
  - `class EmbeddingService`（lazy-load onnx 模型）
  - `embed(texts: list[str]) → np.ndarray[float32, (n, 512)]`
  - 单文本 → `embed_one(text: str)`
  - 配置：模型路径 ~/.cache/fastembed，首次下载；错误回退不抛异常
- [ ] `chunk_service.py`：`make_chunks` 后，`rag_enabled` 时经 `BackgroundTasks` 调 `embedding_service` → 写 `knowledge_vector` + 回填 `chunk.embedding_id`
- [ ] **C1 验收**：新建带内容 chunk → `knowledge_vector` 有行、`chunk.embedding_id` 非空；`rag_enabled=False` 时跳过无副作用

### Slice 2 — 向量存储接口 + SQLite 实现 + 检索直接通路

- [ ] `vector_store.py`：抽象类 `VectorStore(upsert / delete / search / deactivate_project)`（dataclass `SearchResult(id, chunk_id, score)`）
- [ ] `sqlite_vector_store.py`：`upsert` 写 `knowledge_vector`（REPLACE via chunk_id）；`search` NumPy 余弦 → top_k 前加 `status="active"` 过滤（JOIN chunk）
- [ ] `search_service.py`（新）：
  - `_keyword_search(db, project_id, query, top_k)`：SQLite LIKE/FTS5 搜 `knowledge_chunk.content`（FTS5 表若未建则回退 LIKE）
  - `_vector_search(db, project_id, query_vec, top_k, chunk_type?)`：委托 vector_store.search
  - `_rrf_fuse(keyword_ranks, vector_ranks, k=8, rrf_k=60)`：RRF 公式
- [ ] **C2 验收**：`search_service` 可调、返回 RRF 排序结果；纯关键词/纯向量/混合三模可选

### Slice 3 — 检索端点 + 存量回填 + 治理

- [ ] `POST /api/v1/knowledge/search`（`knowledge:view` + `rag_enabled`）：
  ```json
  { "query": "密码字段参数校验", "chunk_type?": "test_case", "top_k?": 8 }
  ```
  入 `SearchQuery` schema → `search_service.hybrid_search` → `SearchResultOut[]`
- [ ] `POST /api/v1/knowledge/reembed`（`knowledge:manage` + `rag_enabled`）：分批回填已有 chunk（batch size 32），返回 `{total, embedded, skipped}`。
  - 跳过 `status != active` / 已有有效 embedding 的 chunk（幂等）。
- [ ] 治理：仅 `status="active"` chunk 入搜；生产数据门禁不变（`knowledge_ingest_production_data`）。
- [ ] Schema：`SearchQuery`（pydantic）、`SearchResultOut`（id + chunk_type + title + snippet + score + source_name）。
- [ ] **C3 验收**：搜索返结果；存量回填幂等；`rag_enabled=False` 搜报 503（SERVICE_UNAVAILABLE / "RAG 未启用"）。

### Slice 4 — 前端：接口详情「相关知识」面板 + 搜索预览

- [x] `frontend/src/api/knowledge.ts` 加 `searchKnowledge(params: SearchQuery): Promise<SearchResultOut[]>`
- [x] `frontend/src/types/index.ts` 追加 `SearchQuery / SearchResultOut` 接口
- [x] 知识中心搜索 Tab（新或复用概览页）：输入框→搜→结果卡片（标题/type/snippet/score）
- [x] 接口资产详情页（`/apitest` API 详情弹窗或面板）追加「相关知识」区块：用 endpoint path + 方法 + summary 拼 query → 调 search → 侧栏卡片展示
- [x] **C4 验收**：搜索 Tab 可搜；API 详情拉得到关联知识（若无匹配则显示「暂无相关」占位）

### Slice 5 — 测试 + ADR-0010 定稿 + 压测

- [ ] `tests/test_knowledge.py` 追加（承接已有 22 cases）：
  - `TestEmbeddingService`：embed_one/embed_many 形状/维度/占位符唯一性
  - `TestVectorStore`：upsert→search 往返、delete 清理、deactivate_project 隔离
  - `TestSearchService`：RRF 融合权重、纯keyword/纯vector/混合三模
  - `TestSearchApi`：`rag_enabled` 门禁 503、无权限 403、正常搜索返结果、存量回填幂等
- [ ] ADR-0010 转为 `accepted`（评审通过后）
- [ ] 压测（手工）：1000 chunk 全量嵌入耗时、单次搜索延迟 p50/p95（目标 <100ms）
- [ ] **C5 验收**：`pytest tests/test_knowledge.py` 扩展集通过；ADR 定稿；压测达标或记录基线

## 范围边界（M2 不做）

- ❌ 知识图谱建图 `knowledge_entity/relation` → M3
- ❌ Agent 编排（需求理解/影响分析/用例生成）→ M4
- ❌ `/knowledge/search` 跨项目检索 → 仅当前项目
- ❌ 向量实时增量（删除 chunk 时级联清理向量）→ M2 已含 `deactivate_project`；细粒度 cascade delete 属 QA 后优化

## 风险

| 风险 | 缓解 |
|------|------|
| 首次 `fastembed` 下载模型 ~130MB | dev 手动下载或 CI 预缓存；部署镜像预置 |
| NumPy 暴力余弦随 chunk 增长变慢 | D2 分层抽象；千级以下可接受；达到瓶颈时切 pgvector HNSW |
| 嵌入中文噪声（特殊符号/代码片段） | `sanitize()` 已去敏感信息；bge 模型对短文本编码质量有保障；检索前对 query 也过 sanitize |
| 安全：敏感内容通过嵌入间接泄露 | chunk 已脱敏（M1）；向量入库前 D4 管线复用 `sanitize()`；检索结果逐条过治理门 |

## 参考

- [fastembed 文档](https://github.com/qdrant/fastembed)——Python onnx embedding
- [BAAI/bge-small-zh-v1.5](https://huggingface.co/BAAI/bge-small-zh-v1.5)——中文小模型，输出 512 维（onnx/CPU 可跑，离线）
- [RRF — Reciprocal Rank Fusion](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)——Cormack et al. SIGIR 2009

## 落地记录（batch-12 · feature/knowledge-m2-vector）

| Slice | 提交 | 验收 |
|---|---|---|
| S1 向量化基石 | `44af6ec` | C1 ✅ 写路径/余弦/1:1 upsert/项目隔离；`rag_enabled=False` 无副作用 |
| S2 混合检索 | `079ab70` | C2 ✅ keyword(CJK 二元组)/vector/hybrid 三模，RRF 融合降序 |
| S3 端点+治理 | `f228dbb` | C3 ✅ `/search` rag关503·无权403·200；`/reembed` rag关/模型未就绪503、幂等 |
| S4 前端检索 Tab | `0023e7b` | C4 ✅ 知识中心「检索」Tab（模式选择+结果卡片+向量回填）；`tsc --noEmit` 0 err |
| S5 测试+ADR+压测 | 本提交 | C5 ✅ `test_knowledge.py` 35 绿；ADR-0010→accepted；压测基线见下 |

**压测基线**（512 维 NumPy 暴力余弦，search-only，in-memory）：
- 1,000 向量：p50 **5.3ms** / p95 **11.2ms**
- 5,000 向量：p50 **41.7ms** / p95 **87.1ms**
- 结论：千级远低于 100ms 目标；**~5,000/项目** 为 <100ms 舒适上限，超出即按 D2 切 pgvector。

**依赖**：`requirements.txt` 增 `fastembed>=0.3` + `numpy>=1.26`（首次使用下载 bge-small-zh-v1.5 onnx 模型；离线环境需预置缓存）。**未装 fastembed 时全链路优雅降级**：嵌入返回 None、检索退化纯关键词、`import app.main` 与 M1 入库零影响（已单测）。

**延后项**（避免与并行 apitest 本体重构冲突，随其本体 PR 一并补入）：
- ~~`/apitest` 接口详情页「相关知识」区块（前端）~~ → ✅ 已交付（commit `1638a58`，feature/knowledge-m2-vector）
- ~~apitest.py / test_case.py 的 4 个入库 hook（知识 5 事件源余项，属 batch-11 A3 延后）~~ → ✅ 已交付（PR #25 合入，commit `9338585`）

**证据**：`pytest tests/test_knowledge.py -q` → **35 passed**；`npx tsc --noEmit` → 0 error。
