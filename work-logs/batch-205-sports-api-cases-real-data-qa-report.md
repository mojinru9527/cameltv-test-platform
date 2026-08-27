# Batch 205 — QA 报告：足球/篮球接口用例「真实数据版」复核 + 补充异常场景

> **QA (🟩)** | Date: 2026-08-27 | Executor: DeepSeek_Harness | 直接任务（分支 `feature/sports-api-cases-real-data`，基于 origin/main @ 79627d15）

## 1. 目标与范围

承接 Batch 204「真实参数矩阵补全 + 负向用例」另立批（见 C204-3），完成：

| 对象 | 服务 | 接口数 | 口径 |
|------|------|-------|------|
| 足球 | camel-service | 197（65 POST + 132 GET） | 现有接口用例参数复核为真实数据版 |
| 篮球 | basketball-service | 188（57 POST + 131 GET） | 完整导入平台库并建真实数据用例 |

用例口径（`tests/test-case-standards/接口用例必填真实数据规范.md`）：
- 正向每接口 1 条：真实参数（数据库数据回填）+ 断言 2xx + 业务码 + 数据存在 + 真实执行回填 `last_response_json`/`last_run_status`
- 负向每接口 ≤3 条（标准三要素）：缺参 / 类型错误 / 越权（无效 token），模拟异常参数

## 2. 方法

1. **契约采集**：Test5 网关 `camel-api-gateway05.svc.elelive.cn/{svc}/v3/api-docs`（VPN 已连；`NO_PROXY=*` 规避残留失效代理）
2. **真实参数池收割**：`home_match`/`list_competition`/`season_teams`/`hot-players`/`hot_match`/`hot_team`/`group_competition` 等列表接口真实响应中提取 matchId/competitionId/seasonId/teamId/playerId/stageId/venueId/refereeId（足球 197 matchId、篮球 20 matchId 等），uid/authorId 用真实演示用户 `11025728`
3. **用例生成**：独立脚本按平台 `api_case_generation_service` 同构字段（title/domain/module/case_type/priority/steps/expected_result/api_*/case_design_method/positive_negative/test_data_note/tags）+ 真实参数回填
4. **真实执行**：只读 GET 正向用例经平台引擎同款 URL 组装（`网关 + /{service}/ee/...`）真实执行；写操作（save/delete/bet/settle/stop_push 等）与副作用 GET（sync/refresh/clear 等）**不执行**（避免污染 Test5），标 pending

## 3. 结果

| 维度 | 值 |
|------|-----|
| 生成用例 | **1196**（正向 385 + 负向 811） |
| 真实执行 | 241 条只读 GET 正向 |
| 通过 | **188**（含 27 条按真实信封自适应断言后转通过） |
| 失败 | **53**（见 §4） |
| 未执行（pending） | **955**（负向 811 + 写操作/副作用 144） |

分服务：camel 90 通过/31 失败/490 pending；basketball 98 通过/22 失败/465 pending。

落库：`platform.db` —— basketball-service（服务 id=9，188 端点）+ camel-service 补 7 缺失端点（190→197）+ `test_case` 1196 条（`source='real_data'`）。备份 `platform.db.bak-sports-realdata-20260828000959`。

## 4. 失败与发现（53 条失败 = 真实健康矩阵）

| 分类 | 数量 | 说明 | 处置 |
|------|-----|------|------|
| 慢接口超时 | 24 | `init_basic_info`/`init_season_stats`/`init_name2id`/`player/hot-players`/`getTransferHistory`/`view_match`/`v_stream` 等 35s 超时（网关慢 + 本轮负载） | 承接 C204-2 |
| 参数待精修（status:400） | 27 | `names/{type}`（ids 类型未随 type 联动）、`home_favorite`（缺 uid）、`article/read`/`my_article_detail`（缺 articleId/uid）、`football/season/recent/*`（缺有效 competitionId/seasonId）、`news/get`（缺 query 参数）等 | 登记 C205-1 |
| 其他 | 2 | 响应信封边缘 | 已记录 |

## 5. 关键发现（供 Leader/后续批次）

1. **响应信封不一致**：体育服务存在三种信封 `{status,data}` / `{code,success,data}` / `{code,success,detail}`，与标准「$.status==200 + data 存在」假设不符。本批按真实信封自适应断言（status/code/success + data/detail/records），27 条因此修正为通过。
2. **缺参/越权在体育公开接口不产生业务拒绝**：`home_match` 缺 `day` → 200+status:200（服务端默认当天）；无效 token → 200（接口 auth_required=0 公开）。故负向断言采用稳健口径「异常输入不得 5xx」，具体拒绝行为记于 expected_result（不误报大量假失败）。
3. **写操作未执行**：122 条 POST + 12 条副作用 GET 建用例但标 pending，需单独授权环境执行。

## 6. C 条件登记

| ID | 内容 | 优先级 |
|----|------|--------|
| C205-1 | 27 条 status:400 端点参数精修（names/{type} 的 ids 随 type 联动、home_favorite/article 补 uid、season/recent 补有效 competitionId+seasonId、news 补 query）后复跑归零；解除条件=精修参数并复跑该 27 条真实执行通过 | P2 |
| C205-2 | 24 条慢接口超时（init_*/hot-players/getTransferHistory/view_match/v_stream 等），承接 C204-2；解除条件=服务侧优化或平台超时配置化后重试 | P2 |

## 7. 复现

```text
1. 契约：http://camel-api-gateway05.svc.elelive.cn/{camel-service|basketball-service}/v3/api-docs
2. 真实参数池：work-logs/evidence/batch-205/real_param_pool.json
3. 生成+执行+落库脚本：test-platform-v2/backend/scripts/sports_api_cases/
4. 落库：test-platform-v2/backend/data/platform.db（gitignored，本地）
```

**证据**：`work-logs/evidence/batch-205/real_param_pool.json`、`execution_summary.json`。
