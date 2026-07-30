---
title: "Batch 57 J01–J22 原子证据对账"
owner: "qa-team"
created: "2026-07-30"
last_reviewed: "2026-07-30"
status: "active-needs-work"
expires: "2027-01-30"
tags: ["batch-57", "production-acceptance", "atomic-evidence", "traceability"]
related:
  - "../../docs/work-logs/batch-56-production-acceptance-execution-matrix.md"
  - "batch-57-environment-targets-and-batch56-acceptance.md"
  - "../../tests/requirements/traceability-matrix/matrix-v14.csv"
---

# Batch 57 J01–J22 原子证据对账

## 1. 结论

`G56-014` 仍保持 `OPEN`，但“到底缺什么”已经收敛为可执行清单。

- J01–J13 本地证据组：288 collected，288 passed，0 skipped，0 failed，
  退出码 0，Pytest 76.15 秒。
- J14–J22 本地证据组：221 collected，221 passed，0 skipped，0 failed，
  退出码 0，Pytest 67.88 秒。
- 需求追溯矩阵共 133 个 CSV 行，其中 108 个真实需求行全部为
  `covered`；另 25 行是版本分隔注释，不是需求。
- J20 在 PC `1440×900` 优先级口径下保持 `PASS`。
- 当前测试证明了大量局部正负面和业务不变量，但不能把服务级测试、mock
  或静态契约当成完整的真实 UI/API/DB 生产链路。

本报告中的：

- `H`：HTTP 状态码已有明确断言；
- `S`：响应结构或 schema 已有明确断言；
- `B`：业务状态、数据库副作用、审计或隔离已有明确断言；
- `✅`：当前本地证据满足该维度；
- `△`：只有部分模块或部分路径满足；
- `—`：仍缺原子执行证据。

## 2. 原子证据矩阵

| J | 本地正/负面证据索引 | H | S | B | 当前判定与精确缺口 |
| --- | --- | :---: | :---: | :---: | --- |
| J01 | `test_auth.py`、`test_critical_path.py`、`test_p1_security_regression.py` | ✅ | △ | △ | `PARTIAL`：成功、错密、不存在、禁用、过期、Cookie/注销已有；仍缺真实浏览器空字段、错密、过期、注销及登录审计/会话同源 |
| J02 | `test_report_aggregator.py`、Batch 53 真实后端 E2E | — | — | △ | `LOCAL GAP`：缺全关联 Dashboard、空项目、低权限/跨项目的 HTTP/schema/count 同源矩阵 |
| J03 | `test_critical_path.py`、`test_p1_security_regression.py`、`test_agent_permissions.py` | △ | △ | △ | `LOCAL GAP`：缺项目/用户/角色/Token 完整 CRUD、Project A/B 三身份和撤权后列表/详情/子资源/写操作 |
| J04 | `test_environment_isolation.py`、`test_api_execution_snapshots.py` | △ | △ | ✅ | `LOCAL + EXTERNAL GAP`：环境跨项目与生产写保护已证实；dataset/integration CRUD、密钥不回显、坏文件/地址和坏引用仍缺；六服务测试环境另走 OpenVPN 流程 |
| J05 | `test_batch48_requirement_acceptance.py`、`test_batch48_requirement_modules.py` | ✅ | ✅ | ✅ | `LOCAL PASS / REAL-UI DEFERRED`：上传、坏输入、幂等、审查、隔离、审计已覆盖；真实 R1 的浏览器导入链待外部资料流程完成 |
| J06 | `test_lanhu_provider.py`、`test_lanhu_evidence_import.py`、`test_lanhu_evidence_worker.py`、`test_lanhu_ocr_merge.py` | △ | △ | ✅ | `EXTERNAL BLOCKED`：本地失败可观察、重试和证据模型已覆盖；真实蓝湖页面树、截图、OCR 和原始证据包不能由 mock 替代 |
| J07 | `test_knowledge_search_rag.py`、`test_wiki_api.py`、`test_wiki_lint.py`、`test_agent_permissions.py`、`test_knowledge_ai_closure.py` | △ | △ | ✅ | `EXTERNAL BLOCKED`：无 Key 时不再伪造 AI 成功；真实 DeepSeek/OCR 摄取→检索→Wiki→Agent 仍需本地密钥 |
| J08 | `test_testcase.py`、Batch 48 需求/用例导入测试、mindmap 单测 | △ | △ | △ | `LOCAL GAP`：缺 R1→用例/脑图真实 UI、坏 Excel/XMind、重复/无来源和跨页 search/sort/count 三类断言 |
| J09 | `test_testplan.py`、`test_c55_4_lifecycle_contracts.py` | ✅ | △ | ✅ | `PARTIAL`：状态枚举、失败分诊、审计和调度执行已覆盖；仍缺真实浏览器关联→执行→刷新，以及双击/并发、取消/重试 |
| J10 | `test_report_aggregator.py`、`test_c55_4_lifecycle_contracts.py` | △ | — | △ | `LOCAL GAP`：缺报告/模板 create/detail/export/delete，空计划、失败执行、坏模板及执行/缺陷同源统计 |
| J11 | `test_c55_4_lifecycle_contracts.py`、`test_task_lifecycle_notifications.py` | △ | △ | ✅ | `EXTERNAL BLOCKED`：调度真实执行、重复运行拒绝、终态和通知日志已覆盖；trigger HTTP/UI、真实 SMTP 收件和失败重试待邮箱流程 |
| J12 | `test_c55_4_lifecycle_contracts.py`、`DefectWorkflow.test.tsx` | △ | △ | ✅ | `LOCAL GAP`：创建/更新引用隔离和失败转缺陷已覆盖；缺后端全状态链、非法/重复 transition、history/stats/count 和真实 UI |
| J13 | Batch 48 coverage、module、critical path、testplan tests | △ | △ | ✅ | `PARTIAL`：覆盖计算、项目隔离和 requirement trace 已覆盖；缺需求→用例→执行→缺陷→报告完整同源钻取及断链/重复关联 |
| J14 | `test_apitest_assets.py`、`test_openapi_import_knife4j.py`、`test_apitest_generation.py`、`test_apitest_project_isolation.py`、`test_api_execution_snapshots.py` | ✅ | ✅ | ✅ | `EXTERNAL BLOCKED`：合成契约正负面完整；六服务实时契约与授权真实执行分别待 OpenVPN/VPN07 流程 |
| J15 | `test_playground.py`、`test_playwright_executor.py`、`test_ui_artifact_isolation.py` | ✅ | △ | ✅ | `LOCAL GAP`：执行器取消/超时/报告隔离已覆盖；仍缺生成 TS→真实编译→本地页面 Playwright→截图/Trace/report 单一主链 |
| J16 | `test_av_measurements.py` | — | — | ✅ | `LOCAL + DEVICE GAP`：真实统计和坏指标已覆盖；缺 av-check API schema、仓库内真实媒体正负面；真机/弱网仍按周末设备流程 |
| J17 | Batch 48 release fixture、Bundle/Diff mocked UI | — | — | △ | `LOCAL GAP`：缺版本任务/发布包 CRUD、详情/全景同源聚合、不完整链、跨项目和重复发布 |
| J18 | `test_perf_api.py`、`test_perf_collector_contract.py` | ✅ | ✅ | ✅ | `DEVICE BLOCKED`：本地会话、鉴权、WebSocket、指标、schema 和项目隔离已覆盖；真实 SoloX/设备采样待设备 |
| J19 | 各项目隔离、分页和 PostgreSQL 并发测试的分散证据 | △ | △ | △ | `LOCAL GAP`：缺所有资源统一 IDOR 参数矩阵、同条件分页/filter/count 和执行/报告/缺陷/发布包幂等 |
| J20 | Batch 56 PC 真实后端 E2E、`ThemeLab.test.tsx` | ✅ | ✅ | ✅ | `PASS`：PC 11/11 主题/模式、全部静态及有效动态路由、键盘、Axe、溢出、console/network 已闭环；tablet/mobile 为 P2 |
| J21 | `test_openvpn_service.py` 仅覆盖本地 VPN 控制边界 | — | — | △ | `EXTERNAL BLOCKED`：体育生产/测试、运营后台和设计对照必须按授权 VPN/账号流程执行 |
| J22 | Alembic、PG reconciliation、Compose、runtime profile tests | ✅ | ✅ | ✅ | `PARTIAL/WAIVED`：本地迁移契约、部署配置和双端门禁可执行；旧 PG 快照由开发正式豁免但不计 PASS；最终工作树全量仍需在交付 SHA 记录 |

## 3. 可由 Codex 继续补齐、无需用户输入的测试

以下属于仓库内部测试与实现工作，不需要账号、地址或 VPN：

1. J02 Dashboard 全关联/空项目/跨项目矩阵。
2. J03 项目、用户、角色、Token CRUD 和撤权矩阵。
3. J04 dataset/integration 本地 CRUD、脱敏和坏引用矩阵。
4. J08 脑图/导入坏格式、重复、分页/search/sort/count。
5. J09 双击/并发、取消/重试与真实本地浏览器生命周期。
6. J10 报告完整 endpoints；J12 缺陷 transition/history/stats。
7. J15 本地生成 TypeScript 的真实 Playwright 链；J16 仓库内媒体 API。
8. J17 发布包聚合；J19 统一 IDOR/分页/count/幂等矩阵。

这些缺口不应等待外部流程，也不能仅以“现有用例 ID 已登记”关闭。

## 4. 外部流程继续跳过

当前无需用户立刻补充；以下项目保持 `BLOCKED/DEFERRED/WAIVED`：

- 真实 DeepSeek Key 和无 fallback 调用证据；
- 蓝湖原始证据包及运营后台设计源；
- 体育测试 OpenVPN、体育生产 VPN07、运营后台账号会话；
- 六服务实时 OpenAPI；
- SMTP 测试发件箱/收件箱；
- ELK 只读入口、身份、索引和可用 trace；
- 真机/SoloX；
- 未采购的生产测试平台服务器；
- 旧 PostgreSQL 快照（已正式豁免）。

## 5. 追溯矩阵事实

| 项 | 值 |
| --- | --- |
| 文件 | `tests/requirements/traceability-matrix/matrix-v14.csv` |
| SHA-256 | `59ABBF7BBD5AC6ECD0034938BB04363E46764A0E3598A0B5E324ABDAEC59E4DE` |
| CSV 总行数 | 133 |
| 有效需求行 | 108 |
| `covered` 有效需求行 | 108 |
| 版本分隔注释行 | 25 |

`covered` 只表示需求已关联用例，不表示用例已在本批次真实环境执行通过。
