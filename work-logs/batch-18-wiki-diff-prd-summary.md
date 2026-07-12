# 批次 18 (batch-18-wiki-diff) —— PRD 摘要

> **产品经理**: Agent Team Product Department
> **日期**: 2026-07-10
> **状态**: **功能已实现，PRD 流程回填**（DEV 部门先行落地 VNext-1..3，本文档基于真实实现反向补齐产品文档，非重新设计）
> **需求源头**: [LLM-Wiki知识库差异对比能力落地方案.md](../test-platform-v2/docs/LLM-Wiki知识库差异对比能力落地方案.md)（v1.0）
> **实施计划**: `C:\Users\26029\.claude\plans\lexical-seeking-pillow.md`
> **本批次范围**: VNext-1（蓝湖 Provider + Raw Source）+ VNext-2（平台内 Wiki 编译）+ VNext-3（RAG vs Wiki 差异对比 + 转待审产物）
> **提交序列**: `04c2b2e`（基座）→ `3cffa53`（VNext-1）→ `c4e1fd8`（VNext-2）→ `13ded44`（VNext-3）→ `f301ba0`（前端集成收口）

---

## 1. 产品背景：为什么这批至关重要

平台在批次 12-17 已建成 RAG 检索、知识图谱、Agent 持续学习闭环（`app/services/knowledge/*`），但知识能力停留在**"从原始切片中检索答案"**这一层。这带来三个结构性缺口：

1. **知识只被"检索"，没有被"结构化"**：蓝湖需求经 lanhu_mcp 提取后直接切片入向量库，缺少可读、可链接、可维护、可审核的中间结构层。Agent 无法基于一份"编译后的知识"做对比、补全、审查。

2. **同一需求在不同知识来源间的差异无法被系统发现**：一个需求可能同时存在于 RAG 切片、Wiki 页面、已确认需求文档、接口资产中。当这些来源对"比赛推送需要哪些字段/走哪些异常路径/覆盖哪些客户端"的理解不一致时，当前平台**没有任何机制**把这些缺失、冲突、版本漂移暴露出来——只能靠测试人员人工比对，极易漏测。

3. **发现差异到补齐测试资产之间缺少闭环**：即便人工发现了"某字段规则缺失对应用例"，也没有一键把该缺口转成待审测试产物、走审核台、落正式资产的路径。

**如果不做这批**：知识中心会长期停留在"能搜到、但说不清哪里缺、哪里冲突"的状态，需求在两库间的缺失/冲突/覆盖缺口只能靠人肉发现，与平台"AI 原生、系统化保障测试覆盖"的定位背离。

本批次落地"**蓝湖需求 → 双知识库（RAG + 结构化 Wiki）→ 同一需求跨库差异对比 → 差异一键转待审产物**"主链路，把知识能力从"检索"推进到"结构化 + 可比对 + 可补齐"。

---

## 2. 成功指标

| # | 指标 | 基线（本批次前） | 目标 | 测量方式 |
|---|------|------------------|------|----------|
| 1 | 蓝湖需求可结构化沉淀 | 仅切片入 RAG，无结构层 | 同一蓝湖链接可同时落 Raw Source + 触发 Wiki 编译 | `POST /wiki/import/lanhu` 后 `GET /wiki/raw-sources` 有记录，且 `wiki_job_id` 非空 |
| 2 | Wiki 编译产出完整性 | 无 | 单需求生成来源页/模块页/需求页/规则页，每页有 source_refs、页间有 link | `GET /wiki/pages` + `GET /wiki/pages/{id}/links`；`test_wiki_ingest.py` 断言 |
| 3 | 差异召回（维度覆盖） | 0（无对比能力） | 差异至少覆盖 业务规则/字段/接口/异常路径/客户端/验收/测试覆盖 7 维度 | `test_wiki_diff.py` 分维度断言；`diff_classifier.classify` 输出 `by_dimension` |
| 4 | 差异项可追溯率 | 不适用 | 100% 差异项含 类型/级别(P0-P3)/维度/左右值/证据/建议 | `WikiDiffItem` 字段非空校验；前端详情抽屉展示 |
| 5 | 差异→待审产物转化 | 无路径 | 差异项一键生成 pending `AiArtifact`，回写 `resolved_artifact_id` | `POST /wiki/diff/items/{id}/create-artifact` → AI 审核台可见 |
| 6 | 审核台闭环 | 无 | 未审核 Wiki 页面/差异产物不进入正式资产 | 产物 `review_status="pending"`，走既有 `ArtifactReviewTab` |
| 7 | 灰度安全性 | 不适用 | 所有新能力默认 OFF，未开启返回 503 | 未设 `WIKI_ENABLED`/`WIKI_DIFF_ENABLED` 时接口 503 |
| 8 | 既有行为零回归 | —— | `extract_features`/`generate_test_cases` 行为不变 | 回归 `test_knowledge.py` 与蓝湖既有用例全绿 |

> **指标可测性风险（诚实标注）**：指标 3 的"**差异召回率**"与"**误报率**"目前**无法量化基线**——因为差异分类器 [`diff_classifier.py`](../test-platform-v2/backend/app/services/wiki/diff_classifier.py) 是**确定性规则比对（无 LLM）**，其召回质量完全取决于上游 [`contract_extractor.py`](../test-platform-v2/backend/app/services/wiki/contract_extractor.py) 抽取契约的准确度。本期仅能验证"给定两份契约，差异被正确分类"，尚无标注语料评估"真实需求的差异是否被完整召回"。详见 §7 决策 3 与本文档末尾缺口清单。

---

## 3. 范围定义

### 纳入范围（VNext-1..3 三条主链）

| VNext | 主链环节 | 优先级 | 模块 | 交付内容 |
|-------|----------|--------|------|----------|
| VNext-1 | 蓝湖 Provider 化 + Raw Source | P0 | backend | `lanhu_provider` 抽取+委托、`wiki_raw_source` 去重/supersede、蓝湖导入入口 |
| VNext-2 | 平台内 Wiki 两阶段编译 | P0 | backend + frontend | `wiki_ingest` Agent（Analysis→Generation）、Wiki 页面/链接/审核、Wiki 知识库 Tab |
| VNext-3 | RAG vs Wiki 差异对比 + 转产物 | P0 | backend + frontend | 契约抽取、差异分类（7 类 × P0-P3）、差异任务/项、转待审 `AiArtifact`、知识差异对比 Tab |

**贯穿三链的基座**：配置开关（`wiki_enabled`/`wiki_auto_ingest_enabled`/`wiki_diff_enabled`/`wiki_auto_create_artifact`/`lanhu_mcp_enabled`）、RBAC 权限（`wiki:view/manage/approve/diff`）、6 张 `wiki_*` 表 + 迁移、审计日志。

### 排除范围（本期明确不做）

| 排除项 | 原因 |
|--------|------|
| **VNext-4 复杂产物映射矩阵** | 本期仅做基础 `create-artifact`（维度→产物类型仅映射 业务规则→business_rule、版本→regression_scope，其余归 test_case），完整映射矩阵（权限矩阵用例、接口边界用例、需求评审问题单等）后续迭代 |
| **VNext-5 外部 LLM-Wiki 连接器** | `wiki_external_connection` 表、`external-connections/*` 端点、`wiki:external` 权限、`external_llm_wiki_enabled` 开关本期不建。避免把外部 LLM Wiki Desktop 变成平台强依赖 |
| **VNext-6 wiki_lint 迭代体检** | 孤立页/过期页/冲突规则的知识体检 Agent 后续做 |
| **OCR / 图片型原型文本提取** | 蓝湖图片原型仅走"补充说明"入口，OCR 不在本期 |
| **完整 Obsidian Vault 文件系统同步** | Wiki 存数据库，不落文件系统 |
| **前端组件单测框架** | 沿用仓库"零组件单测"现状，逻辑靠后端 pytest 覆盖 |
| **复制 `nashsu/llm_wiki` 源码** | GPLv3 许可证风险，仅借鉴架构思想（见 §6 决策 1） |

---

## 4. 用户故事与验收标准

### US-1 —— 蓝湖需求导入双写（VNext-1）

**用户故事**: 作为测试负责人，我在知识中心输入一个蓝湖设计稿链接，希望平台自动把需求内容提取为可追溯的原始知识（Raw Source），并可选地同时进入 RAG 知识库和触发 Wiki 编译，这样同一份需求就在两个知识库都有落点，为后续对比打基础。

**问题描述**: 蓝湖提取逻辑此前深埋在 `ai_service.py`，与 AI 用例生成流程强耦合，无法被知识中心/Wiki 独立复用；蓝湖内容也没有沉淀为不可变的、带来源指纹的原始事实层。

**验收标准（Given/When/Then）**:
- **Given** 已开启 `wiki_enabled` 且当前用户有 `wiki:manage` 权限，**When** 调用 `POST /wiki/import/lanhu` 传入蓝湖链接，**Then** 返回 `{raw_source_id, knowledge_source_id?, wiki_job_id?, extraction_status, extraction_summary}`，且 `GET /wiki/raw-sources` 能查到该记录（含 docId/versionId/pageId/模块/页面/content_hash）。
- **Given** 蓝湖原型为图片无文本 / 登录态失效 / 链接缺 docId，**When** 导入，**Then** `extraction_status` 分别回显 `image_only` / `auth_failed` / `invalid_url`，前端按状态给出对应引导文案（补充说明 / 检查账号 / 复制具体页面链接）。
- **Given** 同一 `immutable_version + content_hash` 的内容已导入，**When** 重复导入，**Then** 跳过不重复入库；内容变化时新建版本、旧版本标记 `superseded`。
- **Given** 未开启 `wiki_enabled`，**When** 调用导入，**Then** 返回 503。
- **回归 AC**: 蓝湖逻辑迁移到 `lanhu_provider` 后，`ai_service` 薄封装保持返回 dict 形状与异常语义不变，`extract_features`/`generate_test_cases` 行为零变化（回归测试兜底）。

### US-2 —— Wiki 两阶段编译（VNext-2）

**用户故事**: 作为知识管理者，我希望把一份 Raw Source 编译成结构化、带来源引用、可审核的 Wiki 页面（来源页/模块页/需求页/规则页），页面之间有链接形成知识网络，且 LLM 生成的内容在人审通过前不参与正式用例生成。

**问题描述**: 知识只有切片没有结构，无法承载"可读、可链接、可对比"的知识层；LLM 生成内容若直接当事实会有编造风险。

**验收标准（Given/When/Then）**:
- **Given** 一条 Raw Source，**When** `POST /wiki/ingest-jobs` 触发编译，**Then** `wiki_ingest` Agent 两阶段执行（Analysis 结构化分析 → Generation 生成页面/链接/Review），任务状态经 `pending→running→success`，`stage` 与 `analysis_json` 落库。
- **Given** 编译成功，**When** `GET /wiki/pages`，**Then** 生成来源页/模块页/需求页/规则页，每页含 YAML frontmatter 且**每条关键结论引用 raw source**（`source_refs_json` 非空）；`GET /wiki/pages/{id}/links` 页面间有链接。
- **Given** 一个已 `approved` 的 Wiki 页面，**When** 重新编译，**Then** 只做版本化更新（version+1），**不覆盖**已审核版本。
- **Given** Wiki 页面处于 `pending/draft`，**When** AI 生成正式用例，**Then** 未审核 Wiki **不参与**正式用例生成（未审不进正式资产）。
- **Given** 编译任务失败，**When** 用户操作，**Then** 支持 `retry`/`cancel`，`running` 态不可重试、已结束态不可取消。

### US-3 —— RAG vs Wiki 差异对比（VNext-3）

**用户故事**: 作为测试人员，我输入一个需求关键词（如"比赛推送"），选择左侧"平台 RAG 知识库"、右侧"LLM Wiki 知识库"，发起对比，平台输出两库对同一需求理解的缺失/冲突/版本变化/测试覆盖缺口，每条差异带严重级别、维度、左右值、证据和建议，让我快速定位漏测点。

**问题描述**: 同一需求在两库间的差异此前完全不可见，只能人工比对。

**验收标准（Given/When/Then）**:
- **Given** 已开启 `wiki_diff_enabled` 且用户有 `wiki:diff` 权限，**When** `POST /wiki/diff/tasks` 传 `{query, left_kb_type, right_kb_type}`，**Then** 后台任务抽取左右契约、分类差异、落 `WikiDiffTask`（`summary_json` 含 left/right 契约与统计）与 `WikiDiffItem`。
- **Given** 对比完成，**When** `GET /wiki/diff/tasks/{id}`，**Then** 返回差异项列表，每项含 `diff_type`（missing_in_left/missing_in_right/conflict/changed/ambiguous/coverage_gap/stale 七类之一）、`severity`（P0-P3）、`dimension`、`left_value`/`right_value`、`evidence`、`suggestion`；差异至少覆盖业务规则/字段/接口/异常路径/客户端/验收/测试覆盖维度。
- **Given** 差异列表，**When** 按严重级别/维度筛选，**Then** 前端列表实时过滤（`GET` 传 `severity`/`dimension`/`diff_type`/`review_status` 查询参数）。
- **Given** 接口路径缺失，**When** 分类，**Then** 判为 P0；业务规则/字段/异常路径缺失判 P1；验收标准不一致判 P2（严重级别按方案 §6.6 判定）。
- **Given** 未开启 `wiki_diff_enabled`，**When** 发起对比，**Then** 返回 503。

### US-4 —— 差异转待审产物（VNext-3）

**用户故事**: 作为测试人员，对于确认有价值的差异项（如"左侧缺少某字段"），我点一下就能把它转成一条待审的 AI 产物，进入既有 AI 审核台，审核通过后落地为正式测试用例——让"发现缺口"直接接上"补齐资产"。

**问题描述**: 发现差异到补齐测试资产之间此前无闭环路径。

**验收标准（Given/When/Then）**:
- **Given** 一个 `pending` 差异项，**When** `POST /wiki/diff/items/{id}/create-artifact`，**Then** 生成 `review_status="pending"` 的 `AiArtifact`（标题 `[差异补齐] xxx`，`content_json` 含差异上下文，`source_refs` 复用差异证据），并回写 `item.resolved_artifact_id` + 将该项标记 `accepted`。
- **Given** 差异维度为"业务规则"/"版本"，**When** 转产物且未显式指定类型，**Then** `artifact_type` 分别取 `business_rule`/`regression_scope`，其余维度默认 `test_case`。
- **Given** 差异项已生成过产物（`resolved_artifact_id` 非空），**When** 再次转产物，**Then** 返回 400 拒绝重复生成。
- **Given** 产物已生成，**When** 打开 AI 审核台，**Then** 该 pending 产物可见并可审核；审核通过前不进入正式资产。
- **Given** 差异项，**When** 用户操作，**Then** 支持 `accept`/`reject` 单独标记 `review_status`。

---

## 5. 依赖关系

```
基座（切片 0）
  ├─ config 开关 + 6 张 wiki_* 表 + 迁移 20260710_0017 + seed 权限 + 空路由
  └─ 是 VNext-1..3 全部前置

VNext-1（Raw Source）── 依赖 基座；复用 source_service 去重/supersede 语义；
                        解耦 ai_service 蓝湖逻辑（回归测试兜底行为不变）
VNext-2（Wiki 编译）── 依赖 VNext-1（消费 Raw Source）；复用 agent_orchestrator._call_llm_sync
VNext-3（差异对比）── 依赖 VNext-2（右侧 platform_wiki 取自 Wiki 页面）+ 现有 RAG
                      （左侧 platform_rag 取自 search_service）；产物复用 AiArtifact + 既有审核台
前端集成收口（切片 4）── 依赖 VNext-1..3 全部端点
```

**外部/既有复用**（不重造）：LLM 调用 `agent_orchestrator._call_llm_sync`；RAG 检索 `search_service.hybrid_search`；脱敏 `knowledge/sanitize`；后台任务自带 Session 范式 `ingest_service`；审核产物 `AiArtifact` + `ArtifactReviewTab.tsx`；信封/分页 `schemas/common.R/Page`；前端 tab/加载/空/错样式照抄 `SearchTab.tsx`。

**关键路径**：基座 → VNext-1 → VNext-2 → VNext-3 → 前端收口（严格串行，每片 commit+push 以对抗工作树重置风险）。

---

## 6. 产品决策记录

1. **不复制 GPLv3 源码，只借鉴架构**：`nashsu/llm_wiki` 为 GPLv3，直接复制进内部平台有开源合规/发布风险。决策为平台内**自建** LLM-Wiki 风格能力（Raw Source/Wiki Page/Link/Review/Diff 业务表与服务），外部 LLM Wiki 未来通过只读 HTTP API/MCP 连接（VNext-5），不嵌入其运行时。

2. **默认开关全 OFF，灰度放量**：`wiki_enabled`/`wiki_auto_ingest_enabled`/`wiki_diff_enabled`/`wiki_auto_create_artifact` 默认 `False`，未开启接口返回 503，与既有 `rag_enabled` 门禁一致。管理员在配置页逐步开启，降低对既有主链路的冲击面。

3. **差异分类器采用确定性规则（无 LLM），LLM 仅用于上游契约抽取**：`diff_classifier.classify` 用集合/键比对确定性地产出差异，保证差异结果**可复现、可解释、零幻觉**；LLM 只在 `contract_extractor` 把非结构化知识抽成"需求契约 JSON"环节介入。代价是差异质量强依赖契约抽取准确度（见 §7 风险）。

4. **未审核不进正式资产**：LLM 生成的 Wiki 页面/差异产物一律 `pending`，走既有 AI 审核台人审通过后才落正式资产；已 `approved` 的 Wiki 页面重编译只版本化不覆盖。平台不自动判定"两库谁对谁错"，只暴露差异 + 展示证据，由人决策。

5. **抽取+委托，保持蓝湖既有行为不变**：VNext-1 把蓝湖提取从 `ai_service` 迁到独立 `lanhu_provider`，`ai_service` 改为薄封装，返回 dict 形状与异常语义**完全一致**，`extract_features`/`generate_test_cases` 零行为变化，由回归测试兜底。

6. **本期仅基础 create-artifact，不做映射矩阵**：维度→产物类型仅硬映射两项（业务规则、版本），其余归 `test_case`，完整映射矩阵留 VNext-4，避免过度设计。

7. **Wiki 收在知识中心内，不新增顶级菜单**：以"Wiki 知识库"/"知识差异对比"两个懒挂载 Tab 收在 `pages/knowledge/index.tsx`，降低用户学习成本；不新增 `menu:*` 权限。

---

## 7. 风险与不确定性

| 风险 | 等级 | 影响 | 缓解 / 现状 |
|------|------|------|------------|
| 差异召回/误报率无法量化 | 中 | 无法证明"真实漏测点被完整发现"，指标 3 缺基线 | 本期先保证分类确定性可复现；后续需建标注语料评估契约抽取准确度 |
| 契约抽取依赖 LLM，质量波动 | 中 | 抽取不准 → 差异误报/漏报 | 差异项均带证据，人审兜底；`ambiguous` 类显式转人审 |
| 蓝湖图片型原型无文本 | 中 | 无法生成有效 Wiki | 提供补充说明入口；OCR 排除在本期 |
| 前端对比结果为轮询（8 次 ×1.2s） | 低 | 长任务可能超轮询窗口未回显 | 提供历史任务下拉可回看；后续可加任务状态推送 |
| Wiki 正文无 markdown 渲染库 | 低 | 富文本体验弱 | 现用 `whitespace-pre-wrap` 纯文本块，符合仓库现状 |
| 灰度计划仅"开关 OFF"，无分环境放量规则 | 低 | 缺少显式灰度节奏文档 | 建议后续补"先 test 环境开 wiki_enabled → 验证 → 再开 wiki_diff"的放量 SOP |

---

## 8. 交付物清单

| # | 交付物 | 类型 | 对应 VNext |
|---|--------|------|-----------|
| 1 | [`models/wiki.py`](../test-platform-v2/backend/app/models/wiki.py)（6 表）+ 迁移 `20260710_0017_wiki_tables.py` | 后端模型 | 基座 |
| 2 | config 开关段 + `seed.py` Wiki 权限（`wiki:view/manage/approve/diff`，tester 得 view/diff） | 后端配置/权限 | 基座 |
| 3 | [`services/external/lanhu_provider.py`](../test-platform-v2/backend/app/services/external/lanhu_provider.py) + `schemas/lanhu.py` | 后端服务 | VNext-1 |
| 4 | [`services/wiki/raw_source_service.py`](../test-platform-v2/backend/app/services/wiki/raw_source_service.py)（去重/supersede） | 后端服务 | VNext-1 |
| 5 | `services/wiki/ingest_service.py` + `page_service.py` + `link_service.py` + `wiki_ingest` prompt | 后端服务 | VNext-2 |
| 6 | [`services/wiki/contract_extractor.py`](../test-platform-v2/backend/app/services/wiki/contract_extractor.py) + [`diff_classifier.py`](../test-platform-v2/backend/app/services/wiki/diff_classifier.py) + [`compare_service.py`](../test-platform-v2/backend/app/services/wiki/compare_service.py) | 后端服务 | VNext-3 |
| 7 | [`api/v1/wiki.py`](../test-platform-v2/backend/app/api/v1/wiki.py)（全部端点）+ router 注册 | 后端 API | VNext-1..3 |
| 8 | `tests/test_lanhu_provider.py` / `test_wiki_raw_source.py` / `test_wiki_ingest.py` / `test_wiki_diff.py` | 后端测试 | VNext-1..3 |
| 9 | `frontend/src/api/wiki.ts` + `types/index.ts` Wiki 类型 | 前端 API/类型 | 基座/收口 |
| 10 | `WikiTab.tsx` / `WikiImportDialog.tsx` | 前端组件 | VNext-1/2 |
| 11 | [`WikiDiffTab.tsx`](../test-platform-v2/frontend/src/pages/knowledge/components/WikiDiffTab.tsx) + `WikiDiffDetailDrawer.tsx` | 前端组件 | VNext-3 |
| 12 | `pages/knowledge/index.tsx` 两 Tab + `requirement/index.tsx` 查看 Wiki/发起对比入口 | 前端集成 | 收口 |

## 9. 完成定义（DoD）

- [x] 蓝湖链接可稳定提取为 Raw Source（含 docId/versionId/pageId/模块/页面/hash），支持 7 种 `extraction_status`，重复导入去重、变更 supersede。
- [x] 同一蓝湖需求可两阶段编译出来源/模块/需求/规则页，每页有来源引用、页间有链接，approved 版本不被覆盖。
- [x] 可发起 `platform_rag` vs `platform_wiki` 差异对比，差异项含 类型（7 类）/级别（P0-P3）/维度/左右值/证据/建议。
- [x] 差异项可一键转 pending `AiArtifact`，人审通过后进入正式资产；未审不进正式资产。
- [x] 全部新能力有 RBAC 权限（`wiki:*`）、配置开关（默认 OFF，未开 503）、审计日志。
- [x] `extract_features`/`generate_test_cases` 行为零回归（回归 `test_knowledge.py` 与蓝湖既有用例）。
- [x] 前端知识中心两新 Tab 渲染、空/加载/错态正常、导入对话框按状态回显、差异筛选与批量操作可用；`npm run build` typecheck 通过。
- [ ] **（遗留）** 差异召回率/误报率量化评估——待建标注语料，后续迭代补齐。
- [ ] **（遗留）** 分环境灰度放量 SOP 文档——建议 PM 部门补齐。

---

> **文档性质说明**：本 PRD 为**流程合规回填**。DEV 部门已按实施计划 `lexical-seeking-pillow.md` 完成 VNext-1..3 落地（5 提交），本文档基于真实代码（`api/v1/wiki.py`、`services/wiki/*`、前端 `WikiTab/WikiDiffTab`）反向补齐产品视角的问题陈述、成功指标、用户故事与验收标准，供六部门流水线归档与后续 VNext-4..6 规划参照。
