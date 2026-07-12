# 批次 18 — LLM-Wiki 知识库差异对比能力 PM 实施计划

> **PM Department (📋)** | 日期：2026-07-10 | 状态：**功能已实现，任务拆解流程回填**
> 批次编号：batch-18-wiki-diff | 分支：`feature/knowledge-m2-vector`
> 说明：本计划为**流程合规回填**——DEV 部门已按纵切片先行落地（VNext-1..3，5 提交 5 切片），PM 依据真实交付代码反向补齐 30-60 分钟粒度任务分解、验收标准与执行记录。所有任务默认 `[x]`（代码已交付并入库）。

---

## 1. 规格摘要

### 1.1 原始需求引用

需求方方案：[LLM-Wiki知识库差异对比能力落地方案.md](/F:/CamelTv/test-platform-v2/docs/LLM-Wiki知识库差异对比能力落地方案.md)

平台已建成 RAG / 知识图谱 / Agent 持续学习能力（`app/services/knowledge/*`），但知识只停留在"从原始切片检索答案"。本需求在其上叠加 LLM-Wiki 思路：蓝湖需求经 `lanhu_mcp` 提取后，**同时**沉淀进现有 RAG 知识库与新增的结构化 Wiki 知识层，再支持"同一需求在两个知识库之间做差异对比"，输出缺失/冲突/版本变化/测试覆盖缺口，并可一键转为待审测试用例或知识修订。

本批次落地范围 **VNext-1 → VNext-3**（打通"蓝湖需求 → 双知识库 → RAG vs Wiki 差异报告 → 待审产物"主链路）。外部 LLM-Wiki Desktop 连接器（VNext-5）、Wiki Lint 迭代体检（VNext-6）本期不做。

规划主骨架：[lexical-seeking-pillow.md](/C:/Users/26029/.claude/plans/lexical-seeking-pillow.md)（DEV 切片 0-4 划分与复用清单）。

### 1.2 技术栈

| 层 | 技术 | 关键约定 |
|----|------|---------|
| 后端 | FastAPI + SQLAlchemy 2.0 + SQLite(WAL) | Router 编排 / Service 承载逻辑 / `R[T]`+`Page[T]` 信封 |
| 模型 | `Mapped[...]` + `mapped_column`，JSON 存 `Text` 列 `*_json` | 表名 `wiki_*` 单数 snake_case，松散标量 `project_id` 无 FK |
| 异步 | `BackgroundTasks.add_task` + `*_in_new_session` 自带 Session | 无 Celery；不强接 `agent_queue` |
| LLM | 复用 `agent_orchestrator._call_llm_sync`（DeepSeek 兼容，`response_format=json_object`） | LLM 不可用时确定性降级 |
| 前端 | React 18 + shadcn/ui（Radix + Tailwind）+ Vite 5 | 无 antd、无 react-markdown（正文 `whitespace-pre-wrap`）、无组件单测 |

### 1.3 目标

1. 蓝湖抽取逻辑 **Provider 化**并保持 `extract_features`/`generate_test_cases` 行为字节级不变；
2. 蓝湖需求沉淀为不可变 **Raw Source**（SHA-256 去重 + supersede）；
3. 平台内 **两阶段 LLM 编译** Raw Source → 结构化 Wiki 页面/链接（带来源引用、Review 门禁、approved 不覆盖）；
4. **RAG vs Wiki 差异对比**：确定性 7 类差异 + P0-P3 分级 + 证据 + 建议 → 一键转待审 `AiArtifact`；
5. 全链路受 **配置开关门禁（默认 OFF，503）** 与 **RBAC（`wiki:*`）** 保护；
6. 知识中心挂载两 Tab、需求列表"发起对比"入口。

---

## 2. 开发任务（按 5 纵切片组织）

> 依赖链：切片 0 → 1 → 2 → 3 → 4（详见 §4）。每切片独立可提交、可验收，逐片 commit+push（工作树重置风险，见 memory worktree-reset-hazard）。

### 切片 0 — 基座（提交 `04c2b2e`）

> 目标：配置开关 + 6 表模型 + 迁移 + 权限 + schema/路由骨架 + 前端类型骨架，端到端可挂载。

- [x] **Task 0.1 — 配置开关段**
  - 描述：`config.py` 新增 `# ── Wiki 知识库 ──` 段：`wiki_enabled=False`、`wiki_auto_ingest_enabled=False`、`wiki_diff_enabled=False`、`wiki_auto_create_artifact=False`、`lanhu_mcp_enabled=True`。
  - 验收：默认全 OFF；`.env` 可覆盖；`GET /wiki/config` 回显五开关。
  - 涉及文件：[backend/app/core/config.py](/F:/CamelTv/test-platform-v2/backend/app/core/config.py)
  - 技术参考：与 `rag_enabled` 门禁一致。

- [x] **Task 0.2 — 6 表 ORM 模型**
  - 描述：`models/wiki.py` 一次性建 6 表：`WikiRawSource / WikiPage / WikiLink / WikiIngestJob / WikiDiffTask / WikiDiffItem`，字段严格对齐方案 §6，JSON 存 `Text` 列 `*_json`，`(Base, TimestampMixin)`；在 `models/__init__.py` 导入并加入 `__all__`。
  - 验收：后端启动 `Base.metadata.create_all` 自动建 6 表；字段/枚举与方案 §6 一致。
  - 涉及文件：[backend/app/models/wiki.py](/F:/CamelTv/test-platform-v2/backend/app/models/wiki.py)、[backend/app/models/__init__.py](/F:/CamelTv/test-platform-v2/backend/app/models/__init__.py)
  - 技术参考：`app/core/db.py:Base` + `app/models/base.py:TimestampMixin`。

- [x] **Task 0.3 — 生产迁移**
  - 描述：`alembic/versions/20260710_0017_wiki_tables.py` 建全部 6 表（dev 靠 `AUTO_CREATE_TABLES` 自动建，迁移供生产/共享环境）。
  - 验收：`alembic upgrade head` 建表成功；`downgrade` 可回滚。
  - 涉及文件：[backend/alembic/versions/20260710_0017_wiki_tables.py](/F:/CamelTv/test-platform-v2/backend/alembic/versions/20260710_0017_wiki_tables.py)

- [x] **Task 0.4 — RBAC 权限种子**
  - 描述：`seed.py` `_ACTIONS` 加 Wiki 段 `wiki:view / wiki:manage / wiki:approve / wiki:diff`；`_TESTER_ACTIONS` 增 `wiki:view / wiki:diff`；不新增 `menu:*`（收在知识中心内）。
  - 验收：seed 后 4 权限入库；tester 具备 view/diff。
  - 涉及文件：[backend/app/seed.py](/F:/CamelTv/test-platform-v2/backend/app/seed.py)

- [x] **Task 0.5 — schema 骨架 + 空路由 + router 注册**
  - 描述：`schemas/wiki.py` 骨架（`WikiConfigOut` 等）；`api/v1/wiki.py` `APIRouter(prefix="/wiki")` + `GET /config`；`router.py` `include_router(wiki.router)`。
  - 验收：`/api/v1/wiki/*` 出现在 OpenAPI；`GET /wiki/config` 通。
  - 涉及文件：[backend/app/schemas/wiki.py](/F:/CamelTv/test-platform-v2/backend/app/schemas/wiki.py)、[backend/app/api/v1/wiki.py](/F:/CamelTv/test-platform-v2/backend/app/api/v1/wiki.py)、[backend/app/api/v1/router.py](/F:/CamelTv/test-platform-v2/backend/app/api/v1/router.py)

- [x] **Task 0.6 — 前端类型骨架**
  - 描述：`api/wiki.ts` + `types/index.ts` 补 Wiki 类型骨架。
  - 验收：`npm run build` typecheck 通过。
  - 涉及文件：[frontend/src/api/wiki.ts](/F:/CamelTv/test-platform-v2/frontend/src/api/wiki.ts)、[frontend/src/types/index.ts](/F:/CamelTv/test-platform-v2/frontend/src/types/index.ts)

---

### 切片 1 — VNext-1：Lanhu Provider + Raw Source（提交 `3cffa53`）

> 目标：蓝湖抽取 Provider 化（保持既有行为）+ Raw Source 去重/supersede + 导入入口。

- [x] **Task 1.1 — LanhuExtractResult schema**
  - 描述：`schemas/lanhu.py` 定义 `LanhuExtractResult`（`source_type/source_ref/doc_id/version_id/page_id/document_name/module_name/page_name/client_scope/changelog/pages[]/content_hash/extraction_status/extraction_summary`），`extraction_status` 枚举含 `success/partial/image_only/auth_failed/permission_denied/invalid_url/failed`（方案 §6.1）。
  - 验收：枚举覆盖全部抽取状态。
  - 涉及文件：[backend/app/schemas/lanhu.py](/F:/CamelTv/test-platform-v2/backend/app/schemas/lanhu.py)

- [x] **Task 1.2 — Lanhu Provider（抽取 + 委托）**
  - 描述：`services/external/lanhu_provider.py` 把 `_extract_lanhu_content` 及私有 helper 迁入，导出 `extract(url, auto_login=True) -> LanhuExtractResult`，把 `ValueError`/`LanhuAuthError` 映射为 `extraction_status`。
  - 验收：`ai_service` 薄封装后 `extract_features`/`generate_test_cases` 返回 dict 形状与异常语义完全一致（回归兜底）。
  - 涉及文件：[backend/app/services/external/lanhu_provider.py](/F:/CamelTv/test-platform-v2/backend/app/services/external/lanhu_provider.py)、[backend/app/services/ai_service.py](/F:/CamelTv/test-platform-v2/backend/app/services/ai_service.py)
  - 技术参考：现内联实现在 `ai_service._extract_lanhu_content`；`sys.path` 注入 `lanhu-mcp` in-process 调用 `LanhuExtractor`。

- [x] **Task 1.3 — Raw Source Service（去重 + supersede）**
  - 描述：`services/wiki/raw_source_service.py` `record_raw_source(db, ...)` 按 `(project_id, immutable_version, content_hash)` 去重、内容变更 supersede 旧版本，只 `flush()`；列表/详情查询。
  - 验收：去重跳过 / supersede 状态流转正确。
  - 涉及文件：[backend/app/services/wiki/raw_source_service.py](/F:/CamelTv/test-platform-v2/backend/app/services/wiki/raw_source_service.py)
  - 技术参考：照抄 `source_service.record_source` 的 SHA-256 去重语义。

- [x] **Task 1.4 — 导入服务 + API**
  - 描述：`services/wiki/import_service.py:import_lanhu(...)`；`POST /wiki/import/lanhu`（门禁 `wiki_enabled` + `wiki:manage`）→ 调 provider → 记 raw source → 按 target 用 BackgroundTasks 触发知识入库 / 记 `WikiIngestJob`；`GET /wiki/raw-sources`、`GET /wiki/raw-sources/{id}`。
  - 验收：返回 `{raw_source_id, knowledge_source_id?, wiki_job_id?, extraction_status, extraction_summary}`；未开开关 503。
  - 涉及文件：[backend/app/services/wiki/import_service.py](/F:/CamelTv/test-platform-v2/backend/app/services/wiki/import_service.py)、[backend/app/api/v1/wiki.py](/F:/CamelTv/test-platform-v2/backend/app/api/v1/wiki.py)

- [x] **Task 1.5 — 需求上传联动**
  - 描述：`requirement.py` 蓝湖上传建 `requirement_document` 后，`wiki_enabled` 时 BackgroundTasks 追加建 raw source。
  - 验收：需求上传后台自动生成 raw source，不阻塞主流程。
  - 涉及文件：[backend/app/api/v1/requirement.py](/F:/CamelTv/test-platform-v2/backend/app/api/v1/requirement.py)

- [x] **Task 1.6 — 前端导入对话框 + Raw Source 列表**
  - 描述：`WikiImportDialog.tsx`（链接 + 补充说明 + 目标开关，按 §6.1 状态表回显）；`WikiTab.tsx` 先落 Raw Source 列表 + 导入入口。
  - 验收：状态回显正确、空/加载/错态正常。
  - 涉及文件：[frontend/src/pages/knowledge/components/WikiImportDialog.tsx](/F:/CamelTv/test-platform-v2/frontend/src/pages/knowledge/components/WikiImportDialog.tsx)、[frontend/src/pages/knowledge/components/WikiTab.tsx](/F:/CamelTv/test-platform-v2/frontend/src/pages/knowledge/components/WikiTab.tsx)

- [x] **Task 1.7 — 测试**
  - 描述：`test_lanhu_provider.py`（9 条，mock：success/auth_failed/invalid_url/image_only 状态映射）+ `test_wiki_raw_source.py`（5 条，去重跳过/supersede/状态流转）。
  - 验收：14 条通过，蓝湖回归行为不变。
  - 涉及文件：[backend/tests/test_lanhu_provider.py](/F:/CamelTv/test-platform-v2/backend/tests/test_lanhu_provider.py)、[backend/tests/test_wiki_raw_source.py](/F:/CamelTv/test-platform-v2/backend/tests/test_wiki_raw_source.py)

---

### 切片 2 — VNext-2：平台内 Wiki 两阶段编译（提交 `c4e1fd8`）

> 目标：两阶段 LLM（分析→生成）编译 Raw Source → 结构化 Wiki 页面/链接，带 Review 门禁。

- [x] **Task 2.1 — wiki_ingest 两阶段 prompt**
  - 描述：`agent_prompts.py` `AGENT_META["wiki_ingest"]` + 两阶段 prompt（Analysis 结构化 → Generation 生成页面/链接/Review），规则：页面必带 YAML frontmatter、结论必引 raw source、低置信进 Review、不覆盖 approved 版本。
  - 验收：prompt 强制 JSON 输出 + 来源引用。
  - 涉及文件：[backend/app/services/knowledge/agent_prompts.py](/F:/CamelTv/test-platform-v2/backend/app/services/knowledge/agent_prompts.py)

- [x] **Task 2.2 — Ingest Service（两阶段 + 降级）**
  - 描述：`services/wiki/ingest_service.py:run_wiki_ingest_in_new_session(project_id, job_id)` 自带 Session、两阶段调用共享 LLM helper、写 `WikiIngestJob.stage/analysis_json/status`；LLM 不可用时确定性降级。
  - 验收：job 状态机 pending→running→success/failed；stage 流转 analysis→generation。
  - 涉及文件：[backend/app/services/wiki/ingest_service.py](/F:/CamelTv/test-platform-v2/backend/app/services/wiki/ingest_service.py)
  - 技术参考：后台任务自带 Session 范式 `knowledge/ingest_service`。

- [x] **Task 2.3 — Page Service（版本化 + 审核）**
  - 描述：`services/wiki/page_service.py` 建/版本化/审核/列表/详情/关键词 search；**approved 版本不覆盖只 version+1**。
  - 验收：approved 页面重编译生成新版本而非覆盖。
  - 涉及文件：[backend/app/services/wiki/page_service.py](/F:/CamelTv/test-platform-v2/backend/app/services/wiki/page_service.py)

- [x] **Task 2.4 — Link Service**
  - 描述：`services/wiki/link_service.py` 建 `wiki_link`（mentions/depends_on/covers/affects/conflicts_with/source_of），可选同步 `knowledge_relation`。
  - 验收：页面间生成带 evidence/confidence 的链接。
  - 涉及文件：[backend/app/services/wiki/link_service.py](/F:/CamelTv/test-platform-v2/backend/app/services/wiki/link_service.py)

- [x] **Task 2.5 — Wiki 编译/页面 API**
  - 描述：`POST /wiki/ingest-jobs`、`GET /wiki/ingest-jobs/{id}`、`.../retry`、`.../cancel`；`GET /wiki/pages`、`GET /wiki/pages/{id}`、`.../approve`、`.../reject`、`GET /wiki/pages/{id}/links`、`GET /wiki/search`。
  - 验收：门禁 + RBAC 生效；approve/reject 写审计。
  - 涉及文件：[backend/app/api/v1/wiki.py](/F:/CamelTv/test-platform-v2/backend/app/api/v1/wiki.py)

- [x] **Task 2.6 — 前端 WikiTab 全量**
  - 描述：`WikiTab.tsx` 扩为 左 Wiki 树（按 page_type 分组）/ 中 页面预览（`whitespace-pre-wrap` + 来源引用 + 关联页面）/ 右 操作（重编译/采纳/驳回/查看来源）。
  - 验收：树/预览/操作三栏可用，空/加载/错态正常。
  - 涉及文件：[frontend/src/pages/knowledge/components/WikiTab.tsx](/F:/CamelTv/test-platform-v2/frontend/src/pages/knowledge/components/WikiTab.tsx)

- [x] **Task 2.7 — 测试**
  - 描述：`test_wiki_ingest.py`（6 条，mock LLM：生成来源/模块/需求/规则页、每页有 source_refs、页面间有 link、approved 不被覆盖）。
  - 验收：6 条通过。
  - 涉及文件：[backend/tests/test_wiki_ingest.py](/F:/CamelTv/test-platform-v2/backend/tests/test_wiki_ingest.py)

---

### 切片 3 — VNext-3：RAG vs Wiki 差异对比 + 转产物（提交 `13ded44`）

> 目标：两侧知识库抽契约 → 确定性分类差异 → 落库 → 一键转待审 AiArtifact。

- [x] **Task 3.1 — Contract Extractor**
  - 描述：`services/wiki/contract_extractor.py` 把一侧知识库抽成统一"需求契约 JSON"（§6.6）——`platform_rag` 走 `search_service`/chunks，`platform_wiki` 走 wiki 页面，LLM 辅助。
  - 验收：两侧输出同构契约 JSON。
  - 涉及文件：[backend/app/services/wiki/contract_extractor.py](/F:/CamelTv/test-platform-v2/backend/app/services/wiki/contract_extractor.py)
  - 技术参考：复用 `search_service.hybrid_search`。

- [x] **Task 3.2 — Diff Classifier（确定性 7 类 + P0-P3）**
  - 描述：`services/wiki/diff_classifier.py` 两契约按维度（需求范围/客户端/业务规则/字段/接口/异常/权限/数据依赖/验收/测试覆盖/版本/证据）分类差异（7 种 diff_type：`missing_in_left/missing_in_right/conflict/changed/ambiguous/coverage_gap/stale` + P0..P3 + 证据 + 建议）。
  - 验收：确定性分类，每差异含 type/severity/dimension/证据/建议。
  - 涉及文件：[backend/app/services/wiki/diff_classifier.py](/F:/CamelTv/test-platform-v2/backend/app/services/wiki/diff_classifier.py)

- [x] **Task 3.3 — Compare Service（编排 + 转产物）**
  - 描述：`services/wiki/compare_service.py:run_diff_in_new_session(task_id)` 编排抽取左右契约 → 分类 → 落 `WikiDiffTask/WikiDiffItem`；`create_artifact_from_item(...)` 差异转 pending `AiArtifact` 并回写 `resolved_artifact_id`。
  - 验收：差异项转 AiArtifact（`review_status="pending"`）；重复转产物拦截。
  - 涉及文件：[backend/app/services/wiki/compare_service.py](/F:/CamelTv/test-platform-v2/backend/app/services/wiki/compare_service.py)
  - 技术参考：直接建 `AiArtifact`，复用现有 AI 审核台 `ArtifactReviewTab.tsx`。

- [x] **Task 3.4 — knowledge_diff prompt**
  - 描述：`agent_prompts.py` 加 `knowledge_diff` 类型 prompt。
  - 验收：辅助契约抽取/差异归纳。
  - 涉及文件：[backend/app/services/knowledge/agent_prompts.py](/F:/CamelTv/test-platform-v2/backend/app/services/knowledge/agent_prompts.py)

- [x] **Task 3.5 — 差异对比 API**
  - 描述：`POST /wiki/diff/tasks`（建任务 + BackgroundTasks 跑）、`GET /wiki/diff/tasks`、`GET /wiki/diff/tasks/{id}`（含 items，支持 dimension/diff_type/severity/review_status 筛选）、`POST /wiki/diff/items/{id}/accept|reject`、`POST /wiki/diff/items/{id}/create-artifact`。
  - 验收：门禁 `wiki_diff_enabled`；筛选生效；create-artifact 写审计。
  - 涉及文件：[backend/app/api/v1/wiki.py](/F:/CamelTv/test-platform-v2/backend/app/api/v1/wiki.py)

- [x] **Task 3.6 — 前端差异对比 UI**
  - 描述：`WikiDiffTab.tsx`（对比范围选择 + 发起；左 左契约 / 中 差异列表带筛选[类型/级别/维度/是否已处理] / 右 右契约；批量确认/忽略/生成产物）、`WikiDiffDetailDrawer.tsx`（单差异证据+建议+采纳/驳回/生成产物，shadcn `Sheet`）。
  - 验收：筛选与批量生成可用，drawer 展示证据/建议。
  - 涉及文件：[frontend/src/pages/knowledge/components/WikiDiffTab.tsx](/F:/CamelTv/test-platform-v2/frontend/src/pages/knowledge/components/WikiDiffTab.tsx)、[frontend/src/pages/knowledge/components/WikiDiffDetailDrawer.tsx](/F:/CamelTv/test-platform-v2/frontend/src/pages/knowledge/components/WikiDiffDetailDrawer.tsx)

- [x] **Task 3.7 — 测试**
  - 描述：`test_wiki_diff.py`（8 条，契约抽取 / 各 diff_type 分类 / 差异转 AiArtifact）。
  - 验收：8 条通过。
  - 涉及文件：[backend/tests/test_wiki_diff.py](/F:/CamelTv/test-platform-v2/backend/tests/test_wiki_diff.py)

---

### 切片 4 — 前端集成收口（提交 `f301ba0`）

> 目标：知识中心挂两 Tab + 需求列表入口 + API 门禁测试。

- [x] **Task 4.1 — 知识中心挂载两 Tab**
  - 描述：`pages/knowledge/index.tsx` 加 `Wiki 知识库` / `知识差异对比` 两个懒挂载 Tab（`{tab==='x' && <XTab/>}`），支持 `?tab=` 深链；图标从 `@/lib/icons`（缺 `BookOpen`/`ArrowLeftRight` 先加入 icons）。
  - 验收：两 Tab 懒挂载渲染、深链跳转正确。
  - 涉及文件：[frontend/src/pages/knowledge/index.tsx](/F:/CamelTv/test-platform-v2/frontend/src/pages/knowledge/index.tsx)

- [x] **Task 4.2 — 需求列表发起对比入口**
  - 描述：`pages/requirement/index.tsx` 需求行加"查看 Wiki / 发起对比"入口。
  - 验收：从需求行可深链跳至差异对比 Tab。
  - 涉及文件：[frontend/src/pages/requirement/index.tsx](/F:/CamelTv/test-platform-v2/frontend/src/pages/requirement/index.tsx)

- [x] **Task 4.3 — API 门禁测试**
  - 描述：`test_wiki_api.py`（5 条，覆盖开关 503 门禁 + RBAC 权限点校验）。
  - 验收：未开开关返回 503；无权限被拒。
  - 涉及文件：[backend/tests/test_wiki_api.py](/F:/CamelTv/test-platform-v2/backend/tests/test_wiki_api.py)

---

## 3. 质量要求清单

- [x] **OpenAPI 同步**：20 路由全部带 `response_model=R[...]` + 中文 `summary`，`/api/v1/wiki/*` 出现在 OpenAPI。
- [x] **开关门禁**：五开关默认 OFF；写操作 `_require_wiki_enabled` / `_require_wiki_diff_enabled` 未开返回 `APIException(503)`。
- [x] **RBAC**：每 handler `require_permission("wiki:view|manage|approve|diff")`；seed 权限入库，tester 具 view/diff。
- [x] **单测覆盖**：33 条新增（provider 9 / raw_source 5 / ingest 6 / diff 8 / api 5），逻辑靠后端 pytest（仓库零组件单测约定沿用）。
- [x] **保持蓝湖既有行为**：Provider 化后 `extract_features`/`generate_test_cases` 返回 dict 形状与异常语义不变（回归兜底）。
- [x] **来源可追溯 + 审核门禁**：Wiki 页面必带 source_refs / YAML frontmatter；LLM 产物未审核（`pending`/`draft`）不进正式资产；approved 不覆盖只 version+1。
- [x] **审计**：导入/审核/差异创建/转产物均 `_audit(...)` 写审计日志。
- [x] **无 console 错误 / typecheck**：`npm run build` 通过；两 Tab 空/加载/错态正常（照抄 `SearchTab.tsx`）。
- [x] **响应式**：沿用知识中心既有 shadcn 布局，无新增响应式债务。
- [ ] **无障碍（a11y）**：沿用 shadcn/Radix 无障碍基座，本批次未单独跑 axe-core 扫描（见 §5 未闭环项）。

---

## 4. 依赖关系

### 4.1 切片间依赖（严格串行）

```
切片0 基座 ──▶ 切片1 Provider+RawSource ──▶ 切片2 Wiki编译 ──▶ 切片3 差异对比 ──▶ 切片4 前端收口
  (表/开关/权限)   (extract→raw_source)      (raw_source→pages)   (pages/rag→diff)   (Tab/入口/门禁测试)
```

- 切片 1 依赖切片 0 的 `WikiRawSource`/`WikiIngestJob` 表与 `wiki:manage` 权限；
- 切片 2 消费切片 1 产生的 `WikiIngestJob`（`import_lanhu` 中 `build_wiki` 目标记 job，切片 2 `run_wiki_ingest` 消费）；
- 切片 3 的 `contract_extractor` 的 `platform_wiki` 侧依赖切片 2 的 `WikiPage`；
- 切片 4 收口依赖切片 1-3 全部前端组件与 API。

### 4.2 对既有模块的复用依赖（不重造）

| 依赖模块 | 复用点 | 用于切片 |
|---------|--------|---------|
| `agent_orchestrator._call_llm_sync` | DeepSeek LLM 调用范式（JSON + markdown 兜底） | 2、3 |
| `search_service.hybrid_search` | RAG 侧契约抽取检索 | 3 |
| `knowledge/source_service.record_source` | SHA-256 去重 + supersede 语义 | 1 |
| `knowledge/ingest_service` | 后台任务自带 Session 范式 | 2、3 |
| `AiArtifact` + `ArtifactReviewTab.tsx` | 差异转待审产物复用现有审核台 | 3 |
| `agent_prompts.py` | 挂 `wiki_ingest` / `knowledge_diff` prompt | 2、3 |
| `schemas/common.R/Page` | 统一信封/分页 | 全部 |
| `SearchTab.tsx`/`IterationTab.tsx` | 前端 tab/加载/空/错样式 | 1、2、3 |

---

## 5. 技术备注（风险与缓解）

| 风险 | 级别 | 缓解措施 | 状态 |
|------|------|---------|------|
| **GPLv3 污染**：`nashsu/llm_wiki` 为 GPLv3 | 高 | 只借鉴架构思路，不复制任何源码；页面/差异生成为自研确定性 + 自有 prompt | 已缓解 |
| **蓝湖抽取字节级搬移风险**：`_extract_lanhu_content` 从 `ai_service` 迁至 provider，一旦行为漂移则用例生成回归 | 高 | Provider 化后 `ai_service` 薄封装，保持返回 dict 形状/异常语义完全一致；`test_lanhu_provider.py` 9 条 + `test_knowledge.py` 回归兜底 | 已缓解 |
| **LLM 不可用**：DeepSeek 超时/额度耗尽导致编译/差异中断 | 中 | `ingest_service`/`diff_classifier` LLM 不可用时走确定性降级，job 落 failed 可 retry | 已缓解 |
| **`*_in_new_session` 可测性**：后台任务自带 `SessionLocal()`，难以在测试注入 mock DB | 中 | 服务函数拆分为可注入 db 的纯逻辑 + 薄 session 包装，pytest 直接测纯逻辑（33 条即此模式） | 已缓解 |
| **开关误开生产**：五开关默认 OFF，若生产误开可能触发未验证链路 | 低 | 门禁 503 + RBAC 双重保护；建议生产灰度前先 staging 验证 | 需运维注意 |
| **迁移未在生产验证**：`20260710_0017` 仅 dev `AUTO_CREATE_TABLES` 验证 | 中 | 迁移文件已提供 `upgrade/downgrade`，生产 `alembic upgrade head` 前需在 staging 演练 | **未闭环** |

---

## 6. 冲刺完成情况

### 6.1 交付统计

| 切片 | 提交 | 内容 | 状态 |
|------|------|------|------|
| 切片 0 基座 | `04c2b2e` | config 5 开关 + 6 表 + 迁移 20260710_0017 + seed 权限 + schema/路由骨架 + 前端类型 | ✅ 已交付 |
| 切片 1 VNext-1 | `3cffa53` | Lanhu Provider 化 + Raw Source 去重/supersede + 导入 API + 前端导入对话框 | ✅ 已交付 |
| 切片 2 VNext-2 | `c4e1fd8` | wiki_ingest 两阶段 prompt + ingest/page/link service + 编译/页面 API + WikiTab 全量 | ✅ 已交付 |
| 切片 3 VNext-3 | `13ded44` | contract_extractor + diff_classifier（7 类+P0-P3）+ compare_service + 差异 API + 差异 UI | ✅ 已交付 |
| 切片 4 集成收口 | `f301ba0` | 知识中心两 Tab（懒挂载+?tab= 深链）+ 需求列表发起对比 + API 门禁测试 | ✅ 已交付 |

**交付率：5/5 切片，20 路由，6 表，8 后端 service，5 前端组件，33 单测（9/5/6/8/5）。**

### 6.2 一次通过率评估

- 后端 33 单测全绿（`test_lanhu_provider` 9 / `test_wiki_raw_source` 5 / `test_wiki_ingest` 6 / `test_wiki_diff` 8 / `test_wiki_api` 5）；
- 前端 `npm run build` typecheck 通过；
- 关键约束达成：蓝湖行为不变、开关默认 OFF、来源引用 + 审核门禁、approved 不覆盖；
- **评估：一次通过（回填视角）**——纵切片划分清晰、每片自带验收，未见跨切片返工痕迹。

### 6.3 本期不做（记录以免误解）

- VNext-4 复杂产物映射矩阵（本期仅基础 create-artifact）；
- VNext-5 外部 LLM-Wiki 连接器（`wiki_external_connection` 表与端点，`wiki:external` 权限、`external_llm_wiki_enabled` 开关均留待）；
- VNext-6 `wiki_lint` 迭代体检、OCR、完整 Obsidian Vault 同步；
- 前端组件单测框架（沿用仓库零组件单测现状，逻辑靠后端 pytest 覆盖）。

---

## 附：交付流程

```
Product → PM(回填) → Design → Dev(5 切片已交付) → QA → Leader
   ✅        ✅         —         ✅                 🔜     🔜
```

> 分支：`feature/knowledge-m2-vector`（Wiki 5 提交在此分支）→ 目标合并 `develop`。
