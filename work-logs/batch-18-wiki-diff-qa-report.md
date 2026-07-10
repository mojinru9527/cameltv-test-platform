# Batch-18 QA 报告 —— LLM-Wiki 知识库差异对比能力（VNext-1..3）

> 验证部门：测试部门 QA Department（独立质量守门）
> 需求方案：`test-platform-v2/docs/LLM-Wiki知识库差异对比能力落地方案.md`
> 验证日期：2026-07-10
> 验证范围：VNext-1（蓝湖 Provider 化 + Raw Source）/ VNext-2（平台内 Wiki 编译）/ VNext-3（RAG vs Wiki 差异对比）
> 环境：Windows 11 · Python 3.12.10 · pytest 9.0.3 · 解释器 `F:\CamelTv\test-platform\.venv`（v2 后端无独立 venv，复用 v1 venv 运行，依赖齐全）
> 结论：**NEEDS WORK**（信心 78%）

---

## 一、测试摘要（真实 pytest 输出）

### 1.1 Wiki 专项测试（方案 §12.1 指定 5 个文件）

命令：
```
python -m pytest tests/test_lanhu_provider.py tests/test_wiki_raw_source.py \
  tests/test_wiki_ingest.py tests/test_wiki_diff.py tests/test_wiki_api.py -v
```

结果：**33 passed, 1 warning in 4.62s**（0 失败）

| 测试文件 | 用例数 | 通过 | 失败 | 覆盖切片 |
|---|---:|---:|---:|---|
| test_lanhu_provider.py | 9 | 9 | 0 | VNext-1 蓝湖状态映射/解析/委托同一函数 |
| test_wiki_raw_source.py | 5 | 5 | 0 | VNext-1 去重/supersede/项目隔离/过滤 |
| test_wiki_ingest.py | 6 | 6 | 0 | VNext-2 分析(mock LLM)+退化+确定性生成+版本化 |
| test_wiki_diff.py | 8 | 8 | 0 | VNext-3 分类器/契约抽取退化/差异转产物 |
| test_wiki_api.py | 5 | 5 | 0 | API 接线 + RBAC + 配置开关门禁 |
| **合计** | **33** | **33** | **0** | — |

> 唯一 warning 为 Starlette TestClient 的 `httpx` 弃用提示，与本批次无关。

### 1.2 全量回归

命令：`python -m pytest -q`

结果：**269 passed, 1 failed, 4 warnings in 75.23s**

- 失败用例：`tests/test_ai_extraction_fallback.py::test_extract_features_falls_back_when_deepseek_times_out`
- 判定：**预存在失败、与本批次无关**。失败点在 `ai_service.py:856 extract_features`（DeepSeek 超时后未按预期退化而抛 `ValueError: classifier stalled`），属旧有 AI 抽取降级逻辑，未被本批次 wiki 改动触及（该测试上次改动为 commit 752c025 test-infra 修复，非 wiki 批次）。**不计入本批次缺陷。**
- 除该项外全绿，未发现 wiki 改动对既有模块的连带破坏。

---

## 二、缺陷列表（真实发现）

| # | 严重级 | 描述 | 证据 | 状态 |
|---|---|---|---|---|
| 1 | **P2** | RBAC 越权面偏大：差异项 accept / reject / create-artifact 三端点均挂 `wiki:diff`，而方案 §10.1 规定"差异处理"应为 `wiki:approve`。默认拥有 `wiki:diff` 的 Tester（seed.py:160）可直接采纳差异并生成待审产物，绕过审核角色。 | `app/api/v1/wiki.py:394,409,426`；`app/seed.py:148-160` | 待修 |
| 2 | **P2** | 契约抽取把已驳回/草稿 Wiki 页面纳入对比：`_gather_wiki_text` 仅排除 `superseded`，`rejected`/`draft`/`pending` 页面仍参与差异抽取。已被人工驳回的页面不应再作为对比事实源。 | `app/services/wiki/contract_extractor.py:41-53` | 待修 |
| 3 | **P2** | 分析阶段的 `review_items` / `contradictions` 未持久化，`_generate` 仅 `len()` 计数返回，且无 `WikiReviewItem` 表。违反方案 §6.5 生成规则#3"对不确定内容写入 Review Item"与 §13.3"低置信内容进入 Review"。LLM 标记的不确定/矛盾点被静默丢弃，人工无法审查。 | `app/services/wiki/ingest_service.py:167`；`app/models/wiki.py`（仅 6 张表，无 ReviewItem） | 待修 |
| 4 | **P2** | 差异对比接口能力被大幅简化：`WikiDiffCreateRequest` 左右两侧共用单一 `query`，无法按 §7.4 指定 `source_ids`/`wiki_page_ids`/`scope` 或左右独立查询；`compare_type` 实际未参与流水线（仅 `left_kb_type`/`right_kb_type` 生效），`wiki_vs_wiki`/`external_llm_wiki` 传入不报错但语义落空。 | `app/schemas/wiki.py:138-143`；`app/services/wiki/compare_service.py:41-48` | 待修/待澄清 |
| 5 | **P3** | 后台编排入口无直接测试：`run_wiki_ingest_in_new_session` / `run_diff_in_new_session` 的状态机（running/success/failed/cancelled 守卫）、异常回滚路径均未被测试触达；测试只覆盖组件级 `_run_analysis`/`_generate`/`classify`/`extract_contract`/`create_artifact_from_item`。 | `tests/test_wiki_ingest.py`、`tests/test_wiki_diff.py` 均未调用 `*_in_new_session` | 待补测 |
| 6 | **P3** | 一致性缺口：差异项 accept/reject 端点无审计日志、无 `wiki_diff_enabled` 门禁（同链路 create-artifact 两者都有）。 | `app/api/v1/wiki.py:390-417` vs `:420-442` | 待修 |
| 7 | **P3** | `import_lanhu` 未消费 `lanhu_mcp_enabled` 开关（§10.2 定义了该开关，导入路径未做校验）。 | `app/services/wiki/import_service.py:59-67`；`app/core/config.py:128` | 待修 |
| 8 | **P3** | 前端组件已落地（WikiTab / WikiDiffTab / WikiImportDialog / WikiDiffDetailDrawer + api/wiki.ts），但方案 §12.2 要求的 `WikiTab.test.tsx` / `WikiDiffTab.test.tsx` 前端测试缺失，前端未纳入本次回归。 | `frontend/src/pages/knowledge/components/__tests__/`（无 wiki 用例） | 待补测 |
| 9 | 观察 | 业务级 not-found 统一返回 HTTP 200 + body `code=404`（平台既有 R envelope 约定），与硬门禁 503 的风格不一致；非 wiki 特有缺陷，仅记录以便前端按 body.code 处理。 | `app/api/v1/wiki.py:139,159,178,261` 等 | 记录 |

---

## 三、规格合规对照（方案 §14 完成定义 9 条 + M1..M3 验收标准）

| # | 方案要求 | 实现 | 判定 |
|---|---|---|---|
| 1 | 蓝湖链接可稳定提取为 raw source | `lanhu_provider.extract()` 永不抛异常、7 状态齐全（success/partial/image_only/auth_failed/permission_denied/invalid_url/failed）+ `record_raw_source` | ✅ |
| 2 | 同一蓝湖需求生成 Wiki 页面 | `_generate` 确定性产出 source/module/requirement/rule/index 页 | ✅ |
| 3 | Wiki 页面与 raw_source/knowledge_source 有明确绑定 | 每页 `source_refs_json` 含 `{raw_source_id, knowledge_source_id}`，测试断言每页非空 | ✅ |
| 4 | 至少一种真实差异对比 platform_rag vs platform_wiki | `contract_extractor` + `diff_classifier` 全维度比对 | ✅ |
| 5 | 差异项含类型/级别/维度/左右值/证据/建议 | `WikiDiffItem` 全字段落库，`classify` 输出 P0..P3 + 7 类 diff_type + 证据 | ✅ |
| 6 | 至少一种差异生成待审用例产物 | `create_artifact_from_item` → `AiArtifact(review_status=pending)` 复用既有审核台 | ✅ |
| 7 | 人审通过后导入正式测试资产 | 产物落 pending AiArtifact，复用既有 AI 审核台链路；**diff→审核后落正式资产的端到端未在本批次验证** | ⚠️ 部分 |
| 8 | 新增能力有权限控制/配置开关/审计日志 | 权限✅（wiki:view/manage/approve/diff 已挂）、开关✅（5 项默认 OFF/lanhu 默认 ON）、审计**部分**（import/ingest/approve/reject-page/diff-create/create-artifact 有；accept/reject-item 缺，见缺陷#6） | ⚠️ 部分 |
| 9 | 前端 build/typecheck + 后端核心测试通过 | 后端 wiki 33/33✅、全量 269 passed（1 预存在无关失败）；**前端 build/typecheck 未在本次验证，前端 wiki 测试缺失** | ⚠️ 部分 |
| M2 验收4 | 未审核 Wiki 不参与正式用例生成 | 页面默认 pending；当前 requirement 生成链路尚未读取 wiki（VNext-4+），故"不参与"暂被动满足；但差异侧 `_gather_wiki_text` 纳入 rejected 页（缺陷#2）需在接入正式生成前收敛 | ⚠️ 需关注 |
| §13.3 | 每个结论带来源引用 | ✅ 每页强制 `## 来源` + source_refs；契约抽取 prompt 明确"只依据片段不编造" | ✅ |
| §13.3 | 低置信内容进入 Review | ❌ review_items/contradictions 未持久化（缺陷#3） | ❌ |

### 契约不变性（重点核对）
- `ai_service.py:21` `from ...lanhu_provider import _extract_lanhu_content`，第 804/903 行直接委托调用；`test_delegation_identity` 断言 `ai_service._extract_lanhu_content is lanhu_provider._extract_lanhu_content`（同一函数对象）。抽取逻辑整体平移、异常语义保持一致（`_do_extract` → `ValueError` → 状态归类）。**判定：契约不变性成立 ✅**，`extract_features`/`generate_test_cases` 行为未被本批次破坏（回归中相关用例均绿，唯一失败为预存在超时降级）。

### 降级健壮性（重点核对）
- `_run_analysis`：LLM 返回非 dict 或无 requirements → 退化最小确定性分析（`_fallback=True`），`test_fallback_when_llm_unavailable` 覆盖。✅
- `extract_contract`：LLM 不可用 → 最小契约（summary 保留原始片段），`test_rag_gathers_chunks_fallback` 覆盖。✅
- 后台 `run_*_in_new_session`：均有 try/except + rollback + 置 failed，逻辑正确但**无直接测试**（缺陷#5）。⚠️
- **判定：LLM 不可用时 ingest/contract 优雅降级不崩，成立 ✅**

### 安全核对
- 门禁：`wiki_enabled`/`wiki_diff_enabled` 关闭时经 `APIException(http_status=503)` 真返回 **HTTP 503**（`test_import_gated_when_wiki_off`/`test_diff_gated_when_diff_off` 断言 `status_code == 503`）。✅
- 脱敏：`record_raw_source` 对 title/source_ref/content_md 走 `sanitize()`（防御纵深）。✅
- 未审产物不进正式资产：wiki 页与 AiArtifact 均默认 pending。✅
- 越权：差异处理权限点偏松（缺陷#1）。⚠️

---

## 四、覆盖率与盲区分析

**已覆盖（真实断言，非走过场）：**
- 33 条用例断言实质结果（状态映射、去重/supersede、页面类型集合、source_refs 非空、字段冲突数量、P0 严重级、产物 pending + 计数），非空跑。
- 组件级路径（方案要求的盲区补测）：`_run_analysis`/`_generate`/`classify`/`extract_contract`/`create_artifact_from_item` 均有直接测试，弥补了 `*_in_new_session` 自带 SessionLocal 无法走 HTTP 层的问题。

**盲区：**
1. 后台编排包装层 `run_wiki_ingest_in_new_session` / `run_diff_in_new_session` 的状态机与异常回滚未被测试（缺陷#5）。
2. `import_service.import_lanhu` 编排（提取→raw source→RAG 入库→ingest job→幂等分支）无独立测试，仅被 API 门禁测试间接触及"关闭态"。
3. Raw source `partial` 状态的落地路径未测（provider 定义了 partial，但 extract() 当前仅产出 success/image_only/failed 系，partial 分支实际不可达 —— 建议澄清）。
4. 前端 WikiTab/WikiDiffTab 无单测、无 build/typecheck 验证（缺陷#8）。
5. 端到端验收链路（§12.3：蓝湖→raw→编译→对比→接受→生成接口用例→审核入正式资产）未跑通验证。

---

## 五、发布建议

- **状态：NEEDS WORK**
- **信心：78%**
- **必修复（合入 develop 前，2 项）：**
  1. 缺陷#1 —— 差异处理权限点由 `wiki:diff` 收紧为 `wiki:approve`（accept/reject/create-artifact），对齐 §10.1，避免 Tester 越权生成待审产物。
  2. 缺陷#2 —— 契约抽取排除 `rejected`/`draft` Wiki 页，防止已驳回内容污染差异对比与后续产物。
- **建议修复（可随 VNext-4 迭代，5 项）：**
  3. 缺陷#3 —— 落地 review_items/contradictions 持久化（新增 WikiReviewItem 或复用 AiArtifact），闭合 §13.3 低置信进 Review 安全控制。
  4. 缺陷#4 —— 补齐差异接口的 left/right 独立 ref/scope，或在文档中明确 VNext-3 仅支持单 query + rag_vs_wiki。
  5. 缺陷#5 —— 为 `*_in_new_session` 补编排级测试（状态机 + 异常回滚）。
  6. 缺陷#6/#7 —— accept/reject 补审计与门禁；import 校验 `lanhu_mcp_enabled`。
  7. 缺陷#8 —— 补前端 WikiTab/WikiDiffTab 测试并纳入 CI。

- **下次复测节点：** 缺陷#1、#2 修复并补对应回归用例后复测；建议同批带上后端 `*_in_new_session` 编排测试与一次前端 build/typecheck，届时可评估翻转为 READY。

---

*本报告所有测试数字均来自 2026-07-10 真实 pytest 执行，未做任何估算或编造。*
