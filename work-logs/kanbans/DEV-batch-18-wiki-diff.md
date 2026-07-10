# 🗂️ Dev 部门项目看板 — Batch 18 · LLM-Wiki 知识库差异对比（VNext-1..3）

> **触发来源**：[LLM-Wiki知识库差异对比能力落地方案.md](../../test-platform-v2/docs/LLM-Wiki知识库差异对比能力落地方案.md)
> **上一批次**：[batch-17 (VNext-1 验收修复)](DEV-batch-17-vnext1-acceptance-fixes.md)
> **本批次目标**：打通"蓝湖需求 → 双知识库（RAG + Wiki）→ RAG vs Wiki 差异报告 → 待审产物"主链路

## 项目信息

| 字段 | 值 |
|------|-----|
| **里程碑** | VNext-1..3：Lanhu Provider 化 + 平台内 Wiki 编译 + RAG vs Wiki 差异对比 |
| **关联方案** | [LLM-Wiki知识库差异对比能力落地方案.md](../../test-platform-v2/docs/LLM-Wiki知识库差异对比能力落地方案.md) |
| **计划** | `.claude/plans/lexical-seeking-pillow.md`（切片 0-4） |
| **分支** | feature/knowledge-m2-vector |
| **状态** | ✅ 代码全部落地并推送（5 提交 `04c2b2e`→`f301ba0`），六部门流程回填中 |
| **开关** | `wiki_enabled` / `wiki_diff_enabled` / `wiki_auto_ingest_enabled` / `wiki_auto_create_artifact`（均默认 OFF）；`lanhu_mcp_enabled`（默认 ON） |
| **最后更新** | 2026-07-10 |

## ℹ️ 架构决策（已锁定）

| # | 决策 | 方案 |
|---|------|------|
| D1 | GPLv3 合规 | 仅借鉴 nashsu/llm_wiki 架构，**不复制源码**；外部连接器（VNext-5）本期不做 |
| D2 | 蓝湖重构 | **抽取 + 委托（保行为）**——蓝湖提取从 ai_service 抽到 lanhu_provider，ai_service 委托同一函数，`extract_features`/`generate_test_cases` 行为字节级不变 |
| D3 | 双知识库 | 蓝湖需求同时进入现有 RAG 知识层 + 新增结构化 Wiki 层；Raw Source 复刻 source_service 去重/supersede |
| D4 | Wiki 编译 | 两阶段：LLM 分析 → 确定性生成；LLM 不可用优雅降级保链路；approved 版本不覆盖只 version+1 |
| D5 | 差异分类 | **确定性分类器**（无 LLM）逐维度 → 7 类 diff_type + P0-P3；差异转 pending `AiArtifact` 复用现有 AI 审核台 |
| D6 | 治理门禁 | 所有能力默认开关 OFF（未开返回 HTTP 503）；LLM 产物必带来源引用；未审核不进正式资产 |

## 📍 当前位置

**Batch 18 → 全部切片 ✅ 已交付 → 🔄 六部门流程回填（Product/PM/Design/QA/Leader）**

上次完成：切片 0-4 全部编码 + 测试 + commit + push
本次继续：Agent Team 六部门流水线回填评审与放行

---

## 🎯 交付切片

### Slice 0 — 基座（提交 `04c2b2e`）

- [x] `app/core/config.py`：`wiki_enabled/wiki_auto_ingest_enabled/wiki_diff_enabled/wiki_auto_create_artifact=False` + `lanhu_mcp_enabled=True`
- [x] `app/models/wiki.py`：6 表（WikiRawSource / WikiPage / WikiLink / WikiIngestJob / WikiDiffTask / WikiDiffItem），`(Base, TimestampMixin)`，JSON 存 Text，project_id 索引
- [x] `app/models/__init__.py`：导入 6 模型 + 加入 `__all__`
- [x] 迁移 `alembic/versions/20260710_0017_wiki_tables.py`（承 `20260710_0016`）
- [x] `app/seed.py`：`_ACTIONS` 加 `wiki:view/manage/approve/diff`；`_TESTER_ACTIONS` 加 `wiki:view/diff`
- [x] `app/schemas/wiki.py` 骨架 + `app/api/v1/wiki.py` 路由 + `router.py` 注册
- [x] 前端 `api/wiki.ts` / `types/index.ts` 类型骨架
- **验收**：后端启动建表、`/api/v1/wiki/*` 挂载、seed 权限入库、前端 typecheck 过 ✅

### Slice 1 — VNext-1：Lanhu Provider + Raw Source（提交 `3cffa53`）

- [x] `app/schemas/lanhu.py`：`LanhuExtractResult`（7 状态：success/partial/image_only/auth_failed/permission_denied/invalid_url/failed）+ `LanhuPage`
- [x] `app/services/external/lanhu_provider.py`：把 `_extract_lanhu_content` 及私有 helper **字节级搬移**入 provider；新增标准化 `extract(url, auto_login) -> LanhuExtractResult` + `_classify_error_status` + `_parse_url_ids`（never raises）
- [x] `app/services/ai_service.py`：删除内联蓝湖实现（1563→967 行），改为委托 `lanhu_provider._extract_lanhu_content`，返回 dict 形状与异常语义完全一致
- [x] `app/services/wiki/raw_source_service.py`：`record_raw_source`（按 `(project_id, immutable_version, content_hash)` 去重 + supersede，只 flush）
- [x] `app/api/v1/wiki.py`：`POST /wiki/import/lanhu` + `GET /wiki/raw-sources[/{id}]`
- [x] `app/api/v1/requirement.py`：蓝湖上传后 BackgroundTasks 追加建 raw source
- [x] 前端 `WikiImportDialog.tsx` + `WikiTab.tsx`（Raw Source 列表 + 导入入口）
- **验收**：test_lanhu_provider(9) + test_wiki_raw_source(5) 全绿；蓝湖既有行为不变 ✅

### Slice 2 — VNext-2：平台内 Wiki 两阶段编译（提交 `c4e1fd8`）

- [x] `agent_prompts.py`：`AGENT_META["wiki_ingest"]` + 两阶段 prompt（Analysis → Generation）
- [x] `app/services/wiki/ingest_service.py`：`run_wiki_ingest_in_new_session` + `_run_analysis` + `_generate`（LLM 不可用降级）
- [x] `app/services/wiki/page_service.py`：`upsert_page`（approved 不覆盖只 version+1）+ slugify/list/get/review/get_page_links
- [x] `app/services/wiki/link_service.py`：`create_link`（去重）
- [x] API：ingest-jobs(create/get/retry/cancel) + pages(list/get/links/approve/reject) + search
- [x] 前端 `WikiTab.tsx` 全量（来源 / 页面树按 page_type 分组 / 预览 whitespace-pre-wrap + 来源引用 / 审核）
- **验收**：test_wiki_ingest(6) 全绿（生成页含 source_refs、页间有 link、approved 不被覆盖）✅

### Slice 3 — VNext-3：RAG vs Wiki 差异对比 + 转产物（提交 `13ded44`）

- [x] `app/services/wiki/contract_extractor.py`：`extract_contract`（platform_rag 走 search_service/chunks，platform_wiki 走 wiki 页面，LLM 辅助 + 降级）
- [x] `app/services/wiki/diff_classifier.py`：`classify` + `summarize`（确定性，7 类 diff_type + P0-P3 + 证据 + 建议）
- [x] `app/services/wiki/compare_service.py`：`run_diff_in_new_session` + `create_artifact_from_item`（→ pending AiArtifact，回写 resolved_artifact_id）
- [x] `agent_prompts.py`：`knowledge_diff` 类型
- [x] API：diff/tasks(create/list/detail-with-filters) + items(accept/reject/create-artifact)
- [x] 前端 `WikiDiffTab.tsx`（左右契约三栏 + 差异筛选）+ `WikiDiffDetailDrawer.tsx`（Sheet：证据+建议+采纳/驳回/生成产物）
- **验收**：test_wiki_diff(8) 全绿（契约抽取 / 各 diff_type 分类 / 转 AiArtifact）✅

### Slice 4 — 前端集成收口（提交 `f301ba0`）

- [x] `pages/knowledge/index.tsx`：挂载「Wiki 知识库」「知识差异对比」两 Tab（懒挂载 + `?tab=` 深链）
- [x] `pages/requirement/index.tsx`：蓝湖需求行加「发起对比」入口（导航 `/knowledge?tab=wikidiff&q=<title>`）
- [x] `WikiDiffTab` 从 `?q=` 预填查询
- [x] `test_wiki_api.py`(5)：配置读取 + 权限/开关门禁（HTTP 层）
- **验收**：`npm run build` typecheck + 打包通过；20 路由挂载正常 ✅

## 范围边界（本期不做）

- ❌ VNext-4 复杂产物映射矩阵（本期仅基础 create-artifact）
- ❌ VNext-5 外部 LLM-Wiki 连接器（`wiki_external_connection` 表与连接器端点未建）
- ❌ VNext-6 `wiki_lint` 迭代体检、OCR、完整 Obsidian Vault 同步
- ❌ 前端组件单测框架（沿用仓库零组件单测现状，逻辑靠后端 pytest 覆盖）

## 风险

| 风险 | 缓解 |
|------|------|
| 蓝湖代码字节级搬移可能引入静默行为偏差 | 已验证 `ai_service._extract_lanhu_content is lanhu_provider._extract_lanhu_content`（同一对象）；回归测试兜底 |
| `*_in_new_session` 自带 SessionLocal 无法走 HTTP 层测试 | 业务逻辑以组件级（db_session）覆盖；HTTP 层只覆盖接线/权限/门禁 |
| LLM（DeepSeek）不可用阻断 Wiki 编译/差异 | 两阶段编译与契约抽取均有确定性降级路径，保链路不崩 |
| 迁移 `20260710_0017` 仅 dev auto-create 验证，未在生产 PG 验证 | dev 靠 `AUTO_CREATE_TABLES`；生产上线前需单独跑迁移验证 |

## 📜 批次记录

| Batch | 产出 | 审批 | 耗时 |
|-------|------|------|------|
| 18-Slice0 基座 | 6表/迁移/开关/权限/路由骨架 | `04c2b2e` | — |
| 18-Slice1 VNext-1 | Lanhu Provider + Raw Source | `3cffa53` | — |
| 18-Slice2 VNext-2 | Wiki 两阶段编译 | `c4e1fd8` | — |
| 18-Slice3 VNext-3 | RAG vs Wiki 差异对比 + 转产物 | `13ded44` | — |
| 18-Slice4 集成收口 | 两 Tab 挂载 + 发起对比入口 + API 门禁测试 | `f301ba0` | — |
| **19 验收修复** | **C1 RBAC 越权 + C2 契约状态过滤 + C3 ADR-0013** | **Leader 3 项必办已清** | — |

**batch-19（合并 develop 前必办条件收口）**：
- ✅ C1 — 差异 `accept`/`reject`/`create-artifact` 权限 `wiki:diff`→`wiki:approve`；accept/reject 补 `_require_wiki_diff_enabled` 门禁 + `_audit` 审计。
- ✅ C2 — `contract_extractor._gather_wiki_text` 仅纳入 `approved` 页，排除 draft/pending/rejected/superseded；新增回归 `test_wiki_excludes_non_approved_pages`。
- ✅ C3 — 新增 [ADR-0013](../../docs/adr/0013-llm-wiki-structured-knowledge-diff.md)（自建 LLM-Wiki 层 + GPLv3 借鉴 + 确定性分类器）+ 索引。
- 验证：wiki 专项 **34 passed**；全量 **270 passed / 1 failed**（预存 `test_ai_extraction_fallback`，无关）。
- **剩余（上线前 / batch-20 跟进）**：Design 两项 P1（严重级 Badge P0/P1 同色、深色模式对比度）、迁移 `20260710_0017` staging 演练、review_items 持久化、差异召回率基线、灰度放量 SOP。

**证据**：新增 33 条 wiki 测试（provider 9 / raw_source 5 / ingest 6 / diff 8 / api 5）；后端回归 269 passed（唯一失败 `test_ai_extraction_fallback` 为改动前既存、与本批次无关）；前端 `npm run build` 通过。

## 参考

- [方案原文](../../test-platform-v2/docs/LLM-Wiki知识库差异对比能力落地方案.md)
- [batch-17 (VNext-1 验收修复)](DEV-batch-17-vnext1-acceptance-fixes.md)
- 六部门回填产物：`batch-18-wiki-diff-{prd-summary,pm-plan,design-spec,qa-report,leader-verdict}.md`
