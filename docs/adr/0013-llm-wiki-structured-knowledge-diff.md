# ADR-0013: 自建 LLM-Wiki 结构化知识层与 RAG/Wiki 差异对比（VNext-1..3）

- **状态**：已接受（accepted）—— batch-18 落地 VNext-1..3、batch-19 补齐 Leader 放行条件（RBAC/契约过滤/本 ADR）
- **日期**：2026-07-10
- **决策者**：Dev 部门（承接 M0-M6 RAG 能力，叠加 LLM-Wiki 思路）
- **关联**：[ADR-0009 知识中心与 Agent 持续学习子系统](0009-knowledge-center-agent-continuous-learning.md)、[ADR-0010 向量化与混合检索](0010-knowledge-vector-embedding-hybrid-retrieval.md)、[ADR-0007 DeepSeek LLM 用例生成](0007-deepseek-llm-test-case-generation.md)、[LLM-Wiki知识库差异对比能力落地方案](../../test-platform-v2/docs/LLM-Wiki知识库差异对比能力落地方案.md)

## 背景

M0-M6（ADR-0009/0010）已把需求/接口/用例/缺陷/执行沉淀为可向量检索的 RAG 知识库，但知识仅停留在「从原始切片检索答案」层面：缺少**结构化、可版本化、可比对**的需求视图，导致「同一需求在不同来源/版本间的缺失、冲突、测试覆盖缺口」无法被系统化发现。

需求方要求借鉴 [`nashsu/llm_wiki`](https://github.com/nashsu/llm_wiki) 的 LLM-Wiki 思路：蓝湖需求经 lanhu_mcp 提取后**同时**进入现有 RAG 知识层与新增的结构化 Wiki 层，再支持同一需求在两库之间做差异对比，输出缺失/冲突/版本变化/测试覆盖缺口，一键转为待审测试用例或知识修订。

**硬约束**：
1. `nashsu/llm_wiki` 为 **GPLv3**，直接复制源码会传染平台协议 → 合规红线。
2. 继承 M0 安全红线：生产语料脱敏、数据不外流、未审内容不进正式资产。
3. 蓝湖提取逻辑当前深埋 `ai_service.py`，被 `extract_features`/`generate_test_cases` 依赖，重构**不得改变既有行为**。

## 决策

### D1. GPLv3 合规 —— 仅借鉴架构，不复制源码
- 只借鉴其「原始来源 → 结构化页面 → 页面间链接 → 知识比对」的分层思路，**平台侧全部自研实现**。
- 外部 LLM-Wiki Desktop 连接器（VNext-5）若未来接入，走**只读外部连接器**边界，不引入 GPL 代码。

### D2. 三层知识模型 —— 不可变来源层 + 结构化 Wiki 层 + 差异层（6 表）
- `wiki_raw_source`：蓝湖等原始来源的**不可变快照**（`immutable_version + content_hash` 去重/supersede，复刻 `source_service` 语义）。
- `wiki_page` / `wiki_link`：LLM 编译出的结构化页面（requirement/rule/module/api/…）与页面间关系；页面带 `review_status` 与 `version`，**approved 版本不被覆盖，重编译只 version+1**。
- `wiki_ingest_job`：两阶段编译任务状态机（analysis/generation）。
- `wiki_diff_task` / `wiki_diff_item`：差异任务与逐条差异项（7 类 diff_type + P0-P3）。
- 与 RAG 表并存、松散标量 `project_id` 隔离，无跨库 FK。

### D3. 蓝湖提取 Provider 化 —— 抽取 + 委托（保行为）
- 将 `_extract_lanhu_content` 及私有 helper **字节级搬移**至 `app/services/external/lanhu_provider.py`，导出标准化 `extract(url) -> LanhuExtractResult`（7 状态）。
- `ai_service.py` 改为**委托同一函数对象**（`ai_service._extract_lanhu_content is lanhu_provider._extract_lanhu_content`），返回 dict 形状与异常语义完全一致 → `extract_features`/`generate_test_cases` 零回归（回归测试兜底）。

### D4. Wiki 编译 —— 两阶段（LLM 分析 → 确定性生成），LLM 不可用降级
- 阶段一 LLM 结构化分析 → 阶段二确定性生成页面/链接；LLM 不可用时退化为最小页面，**保链路可跑可测**。
- 治理：每个结论页必带 `source_refs` 来源引用；低置信/未审页 `review_status` 非 approved，**不进入正式用例生成与差异比对**（见 D5）。

### D5. 差异对比 —— 确定性分类器（无 LLM），差异转 pending 产物复用审核台
- 契约抽取：`platform_rag` 走 `search_service`/chunks，`platform_wiki` **仅纳入 approved 页**（排除 draft/pending/rejected/superseded，避免未审内容污染，见 batch-19 C2）。
- 分类器 `diff_classifier` 为**确定性规则比对**（无 LLM，可复现），逐维度产出 7 类差异 + P0-P3 + 证据 + 建议。
- 差异转产物：生成 `AiArtifact(review_status="pending")`，**复用现有 AI 审核台**闭环，回写 `resolved_artifact_id`。

### D6. 治理门禁 —— 默认全 OFF + RBAC 分权
- 配置开关 `wiki_enabled`/`wiki_diff_enabled`/`wiki_auto_ingest_enabled`/`wiki_auto_create_artifact` **默认 OFF**（未开返回 HTTP 503）。
- RBAC：`wiki:view`（读）/ `wiki:manage`（导入/编译）/ `wiki:approve`（**审核 Wiki 页面与差异处理**：采纳/忽略/转产物）/ `wiki:diff`（发起对比）。tester 默认得 `wiki:view` + `wiki:diff`（可发起对比，但**采纳/转产物需 `wiki:approve`**，见 batch-19 C1）。

## 备选与否决

| 备选 | 否决理由 |
|------|----------|
| 直接复制 `nashsu/llm_wiki` 源码进平台 | **GPLv3 协议传染**平台（现为私有），合规红线；且技术栈（Electron/Desktop）与平台 FastAPI 不匹配 |
| Wiki 内容复用 `knowledge_chunk` 表，不新建模型 | 结构化页面/版本/审核/链接语义与切片检索职责混淆；独立 `wiki_*` 表更清晰、便于治理与差异比对 |
| 差异分类用 LLM 判定 | 不可复现、成本高、易漂移；确定性规则比对可复现、可测、零外部依赖，LLM 仅用于上游契约归一化 |
| 蓝湖提取原地保留在 `ai_service.py` | 无法被 Wiki 层复用；Provider 化后双链路（RAG + Wiki）共享同一提取，且以「委托同一函数」保证零回归 |
| 差异采纳复用 `wiki:diff` 权限 | 发起对比（读操作）与采纳/转正式产物（写操作/治理动作）权限等级不同；合并前修正为 `wiki:approve`（batch-19 C1） |

## 影响

- **正向**：需求获得结构化、可版本化、可比对视图；RAG vs Wiki 差异系统化发现缺失/冲突/覆盖缺口并转待审用例；GPLv3 零污染；蓝湖提取零回归且被双链路复用。
- **成本**：新增 6 张表 + 迁移 `20260710_0017`；新增 `wiki_*` 服务层与两个知识中心 Tab；LLM 调用增加（编译分析 + 契约归一化）。
- **风险**：
  - 差异**召回率/误报率暂无标注语料无法量化**（遗留项，随 VNext 补基线）。
  - 迁移 `20260710_0017` 仅 dev `AUTO_CREATE_TABLES` 验证，**生产/staging `alembic upgrade head` 上线前须演练**（上线硬门）。
  - 蓝湖字节级搬移为最高技术风险点，已由 `test_lanhu_provider`(9) + `test_knowledge` 回归兜底。

## 验证（batch-18 落地 + batch-19 收口）

- **单测**：新增 34 条 wiki 用例（provider 9 / raw_source 5 / ingest 6 / diff 9 / api 5）；后端全量回归绿（唯一 `test_ai_extraction_fallback` 为改动前既存、与本批次无关）。
- **门禁**：`wiki_enabled`/`wiki_diff_enabled` 关闭返回 HTTP 503（非 200+code）；RBAC 采纳/转产物为 `wiki:approve`。
- **契约不变性**：`ai_service` 委托 `lanhu_provider` 同一函数对象，蓝湖行为零回归（抽检确认）。
- **降级**：LLM 不可用时两阶段编译与契约抽取均走确定性降级，主链路不崩。

## 本期不做（记录以免误解）

VNext-4 复杂产物映射矩阵、VNext-5 外部 LLM-Wiki 连接器（`wiki_external_connection` 表未建）、VNext-6 `wiki_lint` 迭代体检、OCR、完整 Obsidian Vault 同步。
