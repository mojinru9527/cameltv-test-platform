# ADR-0010: 知识切片向量化与混合检索（M2）

- **状态**：草案（待 Product/Design/Leader 评审，按 [[agent-team-gate]]）
- **日期**：2026-07-09
- **决策者**：Dev 部门（承接 M1，落地 M2）
- **关联**：[ADR-0009 知识中心与 Agent 持续学习子系统](0009-knowledge-center-agent-continuous-learning.md)、[RAG落地执行文档 §M2](../../test-platform-v2/docs/RAG知识图谱与Agent持续学习能力落地执行文档.md)

## 背景

M0+M1（PR #15）已把需求/接口/用例/缺陷/执行等沉淀为 `knowledge_source` + `knowledge_chunk`，
`knowledge_chunk.embedding_id` 预留但为空。M2 目标：让知识**可语义检索**，为 M4 Agent 供料，
并在接口详情页提供「相关知识」。开关 `rag_enabled`（已存在，默认 OFF）门控。

**硬约束（继承 M0 安全红线）**：生产语料脱敏后方可入库；Secret/Cookie/凭据禁入向量库；
**数据不外流**。→ 直接影响「嵌入来源」选型。

## 决策

### D1. 嵌入来源 —— 本地 `fastembed`（BAAI/bge-small-zh-v1.5, onnx）
- CPU 可跑、中文强、**离线不外传**、无 torch 重依赖（onnxruntime）。512 维。
- 新增依赖：`fastembed`、`numpy`（模型首次使用时缓存到本地）。
- 配置：`embedding_model="BAAI/bge-small-zh-v1.5"`、`embedding_dim=512`。

### D2. 向量存储 —— 分层抽象，dev SQLite blob + NumPy，PG 升级切 pgvector
- 定义 `vector_store` 接口（`upsert(chunk_id, vec)` / `search(project_id, qvec, top_k, filters)`）。
- **dev/SQLite**：新表 `knowledge_vector(id, chunk_id 唯一, project_id, model, dim, vec BLOB float32, created_at)`；
  检索走 NumPy 暴力余弦（语料规模数百~数千，足够）。`chunk.embedding_id` 置为对应 vector 行标识。
- **PG 升级**：`pgvector` 列 + ivfflat/hnsw 索引，同接口零改上层。
- 迁移 `0014_knowledge_vector`（承 `0013`）。

### D3. 混合检索 `/knowledge/search`
- 关键词（SQLite LIKE/FTS；PG tsvector）+ 向量余弦，**RRF（Reciprocal Rank Fusion）**融合排序（对量纲鲁棒）。
- 入参：`query`、`chunk_type?`、`top_k`（默认 8）；项目维度隔离。
- 门禁：`knowledge:view` + `rag_enabled`；仅检索 `status="active"` 且已脱敏的 chunk。

### D4. 向量化管线
- `make_chunks` 后，`rag_enabled` 时经 BackgroundTasks（自带 Session，非阻塞）嵌入入库；失败静默+日志。
- 存量回填：`POST /knowledge/reembed`（`knowledge:manage`，分批）或脚本。supersede 的旧向量随 chunk 置 deprecated。

## 备选与否决

| 备选 | 否决理由 |
|------|----------|
| 外部 embedding API（OpenAI/DeepSeek） | **数据出境**违反不外流红线；成本 + 网络依赖 |
| torch + sentence-transformers | 依赖重（torch ~2GB）、冷启慢、镜像膨胀；fastembed(onnx) 更轻 |
| 外部向量库（Chroma/Qdrant/FAISS 服务） | 引入基础设施，违背「SQLite 优先·纯 Python 单栈」；in-DB blob + pgvector 已足 |
| 直接在 chunk 表加 vec 列 | 混淆职责、迁移噪声；独立 `knowledge_vector` 表更清晰、便于 PG 适配 |

## 影响

- **正向**：语义检索能力落地；接口详情「相关知识」；为 M4 Agent RAG 供料；数据全程在本地。
- **成本**：新增 `fastembed`/`numpy` 依赖（需更新 `requirements.txt` 并过 [[common-pitfalls]] 隐式依赖检查）；
  首次下载嵌入模型（部署镜像宜预置缓存）。
- **风险**：暴力余弦在语料显著增长后需切 pgvector/ANN（已由分层抽象兜底）；嵌入延迟需压测（目标单条 <50ms CPU）。
