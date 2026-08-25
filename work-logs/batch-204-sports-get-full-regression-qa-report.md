# Batch 204 — QA 报告：体育接口服务只读 GET 全量回归

> **QA (🟩)** | Date: 2026-08-25 | Verdict: **PASS（回归目标达成，1 项平台缺陷已修）** | Executor: DeepSeek_Harness | 轻量批次

## 1. 执行环境与方法

- 平台：本批 worktree 最新 main 后端（端口 8072）+ 证据库（1272 接口资产 / 8 服务 / 项目 1）
- 目标：Test5 网关（`http://camel-api-gateway05.svc.elelive.cn`），VPN 已连，`NO_PROXY=*`
- 执行路径：平台引擎真实执行（`/api/v1/apitest/api-execute`、`/api/v1/test-cases/{id}/execute`），并发 6，客户端超时 25s

## 2. 端点回归矩阵（523 条只读 GET）

| 分类 | 数量 | 说明 |
|------|------|------|
| PASS | 75 | 2xx + 业务码 200（account 7 / camel 44 / payment 3 / studio 21） |
| PASS_UNVERIFIED | 5 | 2xx 但响应体非 JSON（如 konfi /business/export 流） |
| BUSINESS_ERR | 193 | 网关 2xx + 业务码≠200（status=400 或 code=-1「Something goes wrong」）：**多为缺真实参数/前置 cookie**（如 live-platform /app/getById 无 id、studio association 系列） |
| NEED_PARAMS | 232 | HTTP 4xx——**全部来自 camel-service-final(115) 与 camel-test-confirm(117)，网关无此服务路由（404 Spring JSON）** |
| NETWORK | 18 | 25s+ 超时（camel 聚合类：list_competition/list_faceoff/init_name2id/init_season_stats/hot_match 等；account captcha/generate 等） |
| SERVER_ERR | 0 | 无 5xx |

逐服务 http 分布：account-service 200×39 / camel-service 200×105 / camel-service-final 404×115 / camel-test-confirm 404×117 / konfi-service 200×3 / live-platform 200×11 / payment-service 200×9 / studio-service 200×106。

证据：`b204_endpoints2.json`（523 行分类矩阵，会话留存 %TEMP%；摘要与样本已在本报告）。

## 3. 用例回归（GET 接口用例）

- 库内 GET 用例 621 条：**605 条 `is_deleted=1`**（历史迁移软删除数据，平台执行层按 `is_deleted=False` 过滤，属正常语义）；可执行 **10 条**。
- 修复前（旧代码）：10 条全部 404 —— 存量用例 `api_endpoint` 无服务前缀且 `api_endpoint_id` 为空。
- **修复后**（本批 commit `a049c95b`：`_case_execution_url` 经 `api_spec_ref` 的 `api_endpoint:{id}` 回退解析服务前缀）：

| 用例 | 结果 | 结论 |
|------|------|------|
| #2416 `getById?id=1`（live-platform） | **HTTP 200 / status=200 / data.id=1 / all_pass=True** | ✅ 修复闭环：存量用例真实执行通过 |
| #2415 `getById` 无参数 | HTTP 200 / status=400 业务拒绝（all_pass=True，用例断言设计为「2xx 或业务拒绝」） | ✅ 引擎诚实、参数缺失被业务层拦下 |
| #2417/2418/2419 负向（id 缺失/类型/鉴权） | HTTP 200 / status=400，**all_pass=False** | ❗ 断言口径失配：生成时用 HTTP 4xx 断言，网关语义=HTTP 200+status=400 → **C204-3** |
| #2420–2424 `article/match`×5 | 404（URL=…/camel-test-confirm/ee/article/match） | ❗ 用例绑定资产属 camel-test-confirm，该服务网关无路由 → 同 **C204-1** |

## 4. 平台缺陷与修复

| # | 缺陷 | 修复 | 验证 |
|---|------|------|------|
| B204-FIX-1 | 存量用例（api_endpoint_id 为空）执行 URL 缺服务前缀 → 全 404 | `api_execution_service._case_execution_url` 增加 `api_spec_ref` 前缀 `api_endpoint:{id}` 回退解析（绝对 URL/已有 api_endpoint_id 优先） | 新增 `test_b204_spec_ref_fallback.py`（3 例）+ 既有执行 parity/gaps 测试 11 passed；实跑 #2416 200 通过 |

## 5. 发现与登记

- **C204-1**（P1 资产/环境）：camel-service-final、camel-test-confirm 两副本服务在 Test5 网关无路由（232 端点 + 5 用例 404）。非平台缺陷，属资产与环境事实；解除=确认服务下线或网关路由恢复后归档/启用资产。
- **C204-2**（P2 慢接口）：18 条聚合类 GET 超过 25s（引擎 30s 超时边缘）；解除=服务侧优化或平台执行超时配置化后长超时重试。
- **C204-3**（P2 断言口径）：负向用例断言 HTTP 4xx 与网关信封（HTTP 200+status=400）失配；解除=生成器负向断言对齐业务码口径（`$.status` in 4xx + HTTP 2xx），并回归既有生成测试。
- 数据治理提示：605 条软删除 GET 用例（source=migration）占库内 GET 用例 97%，建议后续批评估清理/归档视图。

## 6. 自检

- `pytest tests/test_b204_spec_ref_fallback.py tests/test_agroup_followup_gaps.py tests/test_api_execution_entrypoint_parity.py` → **11 passed**
- `ruff check app/services/api_execution_service.py --select F821` → 通过
- 全量后端 pytest（合并 main 后）与 CI 门禁见合并前记录（本报告随 PR 更新最终值）

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 4h / ~4.5h | 0/1/3/0（平台 1 项已修；C 条件 3 项外部） | 1（分类器非 JSON 体重分类） | 外部依赖（服务路由/慢接口）+ 技术债（存量用例绑定） | 全量回归前先按 `is_deleted=0` 过滤再统计可执行用例；分类器对非 JSON 响应体单独归类 |
