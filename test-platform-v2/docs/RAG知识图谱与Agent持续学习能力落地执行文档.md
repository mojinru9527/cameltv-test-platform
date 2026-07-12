# RAG 知识图谱与 Agent 持续学习能力 — 落地执行文档

> **版本**：v1.0 | **日期**：2026-07-09 | **状态**：M0+M1+M2+M3 已落地，M4 规划中
>
> **关联 ADR**：
> - [ADR-0009](../../docs/adr/0009-knowledge-center-agent-continuous-learning.md) — 知识中心子系统架构决策
> - [ADR-0010](../../docs/adr/0010-knowledge-vector-embedding-hybrid-retrieval.md) — 向量化与混合检索技术决策
>
> **关联看板**：
> - [DEV-batch-11 (M0+M1)](../../work-logs/kanbans/DEV-batch-11-rag-knowledge.md)
> - [DEV-batch-12 (M2)](../../work-logs/kanbans/DEV-batch-12-rag-m2-vector-search.md)

---

## 一、愿景与目标

把测试平台从「一次性 AI 生成」升级为「持续学习闭环」：

```
需求 → 影响分析 → 用例/数据生成 → 人审 → 执行 → 知识回流 → （循环）
```

**核心原则**：治理优先、分阶段落地、默认关闭。

---

## 二、分阶段路线图

| 阶段 | 名称 | 内容 | 状态 |
|:----:|------|------|:----:|
| **M0** | 治理基座 | 6 表 + 6 权限 + 5 开关 + AI 产物审核 + Agent 日志 | ✅ 已落地 |
| **M1** | 知识源入库 | 5 事件源去重脱敏入库 + supersede 级联 + 安全加固 | ✅ 已落地 |
| **M2** | 向量化与混合检索 | fastembed 本地嵌入 + SQLite blob 向量 + RRF 混合检索 | ✅ 已落地 |
| **M3** | 知识图谱 | 规则实体提取 + 关系建图 + vis-network 可视化 | ✅ 已落地 |
| **M4** | Agent 编排 | 审核台写操作 + Agent 触发端点 + 持续学习回路 | 📋 规划中 |
| **M5** | 需求驱动自动化 | 需求变更 → 影响分析 → 自动推荐用例更新 | 🔮 远期 |
| **M6** | 迭代知识包 | 跨项目知识迁移 + 领域模型蒸馏 | 🔮 远期 |

---

## 三、M0 — 治理基座

### 3.1 数据模型（6 表）

```sql
-- 知识源：需求/接口/用例/缺陷/执行结果 的唯一事实入口
knowledge_source (id, project_id, source_type, source_id, title, source_ref,
                  version, content_hash, iteration_id, raw_content,
                  metadata_json, status, created_at, updated_at)

-- 知识切片：最小检索单元，从 source 切分而来
knowledge_chunk (id, project_id, source_id, chunk_type, title, content,
                 content_hash, token_count, embedding_id, tags, status,
                 created_at)

-- 知识实体：领域实体节点（M3 图谱用，M0 建空表）
knowledge_entity (id, project_id, entity_type, entity_key, name, description,
                  source_id, business_ref_type, business_ref_id, confidence,
                  review_status, metadata_json, created_at, updated_at)

-- 知识关系：实体间关系边（M3 图谱用，M0 建空表）
knowledge_relation (id, project_id, from_entity_id, relation_type, to_entity_id,
                    confidence, evidence_chunk_ids, review_status, metadata_json,
                    created_at)

-- AI 产物：LLM 生成的所有内容（人审后才能进正式库）
ai_artifact (id, project_id, artifact_type, title, content_json, source_refs,
             agent_run_id, confidence, review_status, reviewer_id, review_comment,
             imported_ref_type, imported_ref_id, created_at)

-- Agent 执行日志：可追踪的 Agent 运行记录
agent_run (id, project_id, agent_type, trigger_type, input_summary,
           output_summary, chunk_ids, artifact_ids, status, error_message,
           started_at, finished_at, created_at)
```

### 3.2 权限体系

| 权限码 | 说明 | 类型 |
|--------|------|:----:|
| `knowledge:view` | 查看知识中心 | button |
| `knowledge:manage` | 管理知识源（重解析/废弃） | button |
| `knowledge:approve` | 审核知识与 AI 产物 | button |
| `agent:list` | 查看 Agent 执行记录 | button |
| `agent:run` | 手动触发 Agent | button |
| `agent:admin` | 管理 Agent 配置 | button |
| `ai_artifact:import` | 导入 AI 产物到正式资产 | button |

Tester 角色默认拥有 `knowledge:view` 和 `agent:list`。

### 3.3 治理开关（5 个，全部默认 OFF）

| 开关 | 默认值 | 说明 |
|------|:------:|------|
| `knowledge_ingest_enabled` | `False` | 是否自动入库知识源 |
| `rag_enabled` | `False` | 是否启用 RAG 向量检索 |
| `knowledge_graph_enabled` | `False` | 是否启用实体提取与图谱 |
| `ai_artifact_allow_batch_import` | `False` | 是否允许批量导入 AI 产物 |
| `knowledge_ingest_production_data` | `False` | 是否允许生产环境执行结果入库 |

### 3.4 AI 产物治理

- `ai_artifact.review_status = "approved"` 才能导入正式用例库
- `review_status != "approved"` 时导入 → 403
- 批量导入受 `ai_artifact_allow_batch_import` 门控（>1 条时检查）

---

## 四、M1 — 知识源/切片入库

### 4.1 入库架构

```
领域事件（需求/接口导入/用例/缺陷/执行失败）
    │
    ▼ 主事务 commit 之后
BackgroundTasks.add_task(ingest_xxx_in_new_session)
    │
    ▼ 独立 SessionLocal()（失败不回滚主操作）
sanitize() → 去重 → record_source() → make_chunks()
```

### 4.2 5 个入库 Hook

| Hook | 触发点 | 入库内容 |
|------|--------|----------|
| 需求文档 | `POST /requirements` | 需求全文 |
| 接口导入 | `POST /apitest/assets/import` | API endpoint + schema |
| 接口用例 | `POST /apitest/cases/generate` → import | 生成的 API 测试用例 |
| 缺陷 | `POST /defects` | 缺陷标题/描述/步骤 |
| 执行失败 | API 批量任务完成后 | 失败用例的请求/响应/断言 |

### 4.3 去重策略

- **source 级**：`(project_id, source_type, source_id)` + 内容 hash 相同 → 跳过
- **chunk 级**：`(source_id, content_hash)` 唯一 → 同内容只存一条
- **supersede**：同 source_id 内容变更 → 旧 source 标记 `superseded`，级联废弃旧 chunks

### 4.4 脱敏管线

入库前 `sanitize()` 统一脱敏：
- 鉴权头：`Authorization: Bearer xxx` / `Cookie: SID=xxx` / `token=xxx`
- JWT token：裸 base64 三段式（含无 Bearer 前缀）
- 密钥/secret：单双引号 JSON 值 / 冒号无引号值
- 手机号：支持 `13812345678` / `138-1234-5678` / `138 1234 5678` / `138.1234.5678`
- 邮箱：`xxx@domain` → 遮蔽
- 身份证：18 位数字
- ReDoS 防护：正则含量词上界，50KB blob < 100ms

---

## 五、M2 — 向量化与混合检索

### 5.1 架构决策（详见 ADR-0010）

| # | 决策 | 方案 |
|---|------|------|
| D1 | 嵌入模型 | `fastembed` BAAI/bge-small-zh-v1.5（ONNX, CPU, 512d, 离线） |
| D2 | 向量存储 | 分层：dev SQLite blob + NumPy 余弦；升 PG → pgvector |
| D3 | 检索方式 | RRF 融合：关键词 LIKE + 向量余弦 → `/knowledge/search` |
| D4 | 触发方式 | BackgroundTasks post-commit 不阻塞；存量 `/reembed` 回填 |

### 5.2 核心组件

```
embedding_service.py          — 嵌入模型加载与推理（可用性检测/优雅降级）
vector_store.py               — 向量存储抽象（upsert/search/delete/deactivate_project）
search_service.py             — 混合检索引擎（关键词 + 向量 + RRF 融合）
```

### 5.3 API 端点

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| `POST` | `/api/v1/knowledge/search` | `knowledge:view` + `rag_enabled` | 混合检索（三模可选） |
| `POST` | `/api/v1/knowledge/reembed` | `knowledge:manage` + `rag_enabled` | 存量回填（幂等，分批） |

**搜索请求**：`{ query, chunk_type?, top_k?, mode?: "hybrid"|"keyword"|"vector" }`
**搜索结果**：`[{ chunk_id, chunk_type, title, snippet, score, source_id, source_name }]`

### 5.4 前端组件

- **知识中心 > 检索 Tab**：搜索输入框 → 结果卡片（标题/类型/snippet/score/知识源）
- **接口详情 > 相关知识面板**：用 endpoint path + method + summary 自动查询关联知识切片

---

## 六、M3 — 知识图谱

### 6.1 实体提取

规则引擎提取（非 LLM）：
- `api`: API 端点
- `field`: API 字段/参数
- `requirement`: 需求文档
- `test_case`: 测试用例
- `defect`: 缺陷

### 6.2 关系建图

| 关系类型 | 方向 | 说明 |
|----------|------|------|
| `contains` | API → field | API 包含参数/字段 |
| `executed_by` | test_case → API | 用例执行某 API |
| `depends_on` | requirement → test_case | 需求关联用例 |

### 6.3 API 端点

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| `GET` | `/api/v1/knowledge/graph/view` | `knowledge:view` | 返回图谱数据（nodes + edges） |
| `POST` | `/api/v1/knowledge/graph/extract` | `knowledge:manage` | 触发实体提取 |

### 6.4 前端可视化

- **技术选型**：vis-network + vis-data 力导向图
- **物理引擎**：ForceAtlas2Based（gravitationalConstant=-30, springLength=120）
- **节点着色**：按 entity_type（API=蓝色, 字段=绿色, 需求=紫色, 用例=橙色, 缺陷=红色）
- **边样式**：`contains`→实线, `executed_by`→虚线
- **交互**：点击节点查看详情, 缩放/适应画布, 触发提取按钮
- **入口**：知识中心第 5 个 Tab「图谱」

---

## 七、数据流全景

```
┌─────────────────────────────────────────────────────┐
│                    领域事件                           │
│  需求 / 接口导入 / 用例 / 缺陷 / 执行结果              │
└────────────┬────────────────────────────────────────┘
             │ post-commit
             ▼
┌─────────────────────────────────────────────────────┐
│              ingest_service                          │
│  sanitize() → dedup → record_source() → make_chunks()│
└────────────┬────────────────────────────────────────┘
             │
     ┌───────┴───────┐
     ▼               ▼
┌─────────┐   ┌──────────────┐
│ sources │   │   chunks     │
│ (原文)   │   │ (最小检索单元) │
└─────────┘   └──────┬───────┘
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
   ┌──────────────┐    ┌────────────────┐
   │ embedding    │    │ entity_service │
   │ (fastembed)  │    │ (规则提取)      │
   └──────┬───────┘    └───────┬────────┘
          ▼                     ▼
   ┌──────────────┐    ┌────────────────┐
   │ vectors      │    │ entities +     │
   │ (SQLite blob)│    │ relations      │
   └──────┬───────┘    └───────┬────────┘
          │                     │
          └──────────┬──────────┘
                     ▼
            ┌────────────────┐
            │ search_service │
            │ RRF 混合检索    │
            └───────┬────────┘
                     │
                     ▼
            ┌────────────────┐
            │ API + 前端      │
            │ /search        │
            │ /graph/view    │
            │ 检索 Tab       │
            │ 图谱 Tab       │
            └────────────────┘
```

---

## 八、测试与验证

### 8.1 后端测试

| 文件 | 用例数 | 覆盖范围 |
|------|:------:|----------|
| `tests/test_knowledge.py` | 22 | 模型持久化 / 脱敏 / 去重 / 治理守卫 / API 访问控制 / M2 嵌入/向量/检索 / 回填死循环守卫 |
| `tests/test_apitest_assets.py` | ~20 | Swagger 导入 + 用例生成（知识入库 hook 回归） |
| `tests/test_p1_security_regression.py` | ~40 | P1 安全加固回归（含 RBAC 验证） |

### 8.2 前端验证

| 检查项 | 状态 |
|--------|:----:|
| tsc 类型检查 | ✅ 0 error |
| ESLint | ✅ 通过 |
| vitest 单元测试 | ✅ 4 文件 30+ 用例 |

### 8.3 治理验证矩阵

| 测试项 | 预期 | 状态 |
|--------|------|:----:|
| `rag_enabled=False` 搜索 | 503 | ✅ |
| 缺少 `knowledge:view` 搜索 | 403 | ✅ |
| 未审核产物导入 | 403 | ✅ |
| 已审核产物导入 | 创建正式用例 | ✅ |
| 批量导入未开启 | 403（>1 条） | ✅ |
| 脱敏覆盖（含边界） | 密钥/jwt/手机/邮箱/身份证 全遮蔽 | ✅ |
| ReDoS 回归 | 50KB blob < 100ms | ✅ |
| supersede 级联 | 旧源+chunks → superseded | ✅ |
| 回填死循环守卫 | 零进展批次提前终止 | ✅ |

---

## 九、部署与运维

### 9.1 开启步骤

```bash
# 1. 开启知识入库（观察迭代 1-2 天无异常后继续）
SET knowledge_ingest_enabled=true

# 2. 批量回填存量 chunk 向量
curl -X POST /api/v1/knowledge/reembed

# 3. 开启 RAG 检索
SET rag_enabled=true

# 4. 提取实体与关系
curl -X POST /api/v1/knowledge/graph/extract

# 5. 开启知识图谱
SET knowledge_graph_enabled=true
```

### 9.2 容量预估

| 项目 | 估算 |
|------|------|
| 每 chunk 嵌入 | 512 float32 = 2KB |
| 1,000 chunks | ~2MB 向量存储 |
| 10,000 chunks | ~20MB 向量存储 |
| 搜索 p50 延迟（1,000 chunks） | <50ms（NumPy 暴力余弦） |
| 搜索 p95 延迟（10,000 chunks） | <200ms（建议切 pgvector） |

### 9.3 升级到 PostgreSQL/pgvector

当 chunk 数量 > 10,000 或搜索延迟 > 200ms 时：
1. 设置 `DATABASE_URL=postgresql://...`
2. 运行 `alembic upgrade head`（迁移自动包含 pgvector 扩展）
3. 向量存储自动切到 pgvector 实现（IVFFlat/HNSW 索引）

---

## 十、已知限制与后续

| 限制 | 影响 | 计划 |
|------|------|------|
| 实体提取为规则引擎（非 LLM） | 覆盖率有限 | M4 引入 LLM 辅助提取 |
| SQLite blob 暴力余弦 | chunk > 10K 时搜索变慢 | 切 pgvector |
| Agent 触发端点未实现 | 无法编排自动链路 | M4 实现 |
| 前端测试覆盖率低（仅 4 文件） | 重构风险 | G4 持续推进 |
| CI 仅测 SQLite | PG 兼容性未自动验证 | G5 补齐 |

---

## 附录 A：文件清单

### Backend

```
app/models/knowledge.py                          — 6 个 ORM 模型
app/schemas/knowledge.py                         — Pydantic schema
app/api/v1/knowledge.py                          — 知识中心 API (13 端点)
app/api/v1/agent.py                              — Agent 执行记录 API (2 端点)
app/services/knowledge/
  ├── source_service.py                           — 知识源 CRUD + supersede
  ├── chunk_service.py                            — 切片切分 + 去重
  ├── ingest_service.py                           — 5 事件入库 hook
  ├── sanitize.py                                 — 脱敏管线
  ├── artifact_service.py                         — AI 产物审核 + 导入
  ├── embedding_service.py                        — fastembed 嵌入服务
  ├── vector_store.py                             — SQLite 向量存储
  ├── search_service.py                           — RRF 混合检索
  ├── vectorize.py                                — 回填管线
  ├── entity_service.py                           — 规则实体提取
  └── agent_run_service.py                        — Agent 日志查询
alembic/versions/0013_knowledge_tables.py         — M0 6 表迁移
alembic/versions/0014_knowledge_vector.py         — M2 向量表迁移
tests/test_knowledge.py                           — 22 用例
```

### Frontend

```
src/types/index.ts                                — KnowledgeSource/Chunk/AiArtifact/GraphView 等类型
src/api/knowledge.ts                              — 知识 API 函数
src/pages/knowledge/index.tsx                     — 知识中心入口（5 Tab）
src/pages/knowledge/components/
  ├── OverviewTab.tsx                             — 概览面板
  ├── SourceListTab.tsx                           — 知识源列表
  ├── ArtifactReviewTab.tsx                       — AI 审核台
  ├── SearchTab.tsx                               — 混合检索面板
  └── GraphTab.tsx                                — vis-network 图谱可视化
src/stores/__tests__/auth.test.ts                 — Auth store 测试
src/api/__tests__/knowledge.test.ts               — Knowledge API 测试
```

---

## 附录 B：变更日志

| 日期 | 变更 | 版本 |
|------|------|:----:|
| 2026-07-09 | M0+M1+M2+M3 全链路落地，文档创建 | v1.0 |
