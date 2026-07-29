---
title: "Batch 56 测试平台全功能生产级验收执行矩阵"
owner: "qa-team"
created: "2026-07-29"
last_reviewed: "2026-07-29"
status: "executed-needs-work"
tags: ["batch-56", "production-acceptance", "evidence", "real-input", "agent-team"]
related:
  - "../superpowers/plans/2026-07-29-batch-56-full-platform-production-acceptance.md"
  - "../测试平台全功能验收文档-环境链接与账号汇总.md"
  - "../../tests/test-case-standards/生产级模块验收规则.md"
  - "../../test-platform-v2/work-logs/batch-55-acceptance-closure-qa-report.md"
---

# Batch 56 测试平台全功能生产级验收执行矩阵

## 1. 文档用途与当前结论

本文件先作为 Batch 56 的预执行验收账本建立，现已完成执行回填。第 11 节是固定 SHA 上的权威执行摘要；前面的 `NOT RUN` 行保留为执行前快照，不再代表最终状态。

截至本文件创建时：

- Batch 56 的功能、接口、浏览器、迁移和供应链验收尚未在固定执行 SHA 上完成。
- 仓库内 R1 输入已完成路径、大小和 SHA-256 登记；这只证明文件可读取且内容被固定，不证明对应业务功能通过。
- 外部 R0 的地址和凭据只以逻辑 ID 引用；本文件不保存或复述地址、账号、密码、Token、Cookie、请求头、查询参数和生产业务数据。
- 当前 worktree 存在其他 Agent 的并行开发改动，最终执行前必须重新冻结代码 SHA 和变更清单。
- Batch 55 的历史通过项可作为回归基线，不能自动继承为 Batch 56 的 `PASS`。
- 当前机械结论仍为 `NEEDS WORK`：本地平台、回归、容器和代码门禁已通过，但外部测试节点、六服务契约、运营后台会话、真实 AI/OCR、真机性能、ELK 和旧库快照仍有 P0/P1 失败或阻断。

## 2. 状态与证据口径

### 2.1 执行状态

| 状态 | 本文件中的唯一含义 |
| --- | --- |
| `PASS` | 当前固定 SHA、指定环境和指定输入下，全部预期满足且证据可复核 |
| `FAIL` | 任一必须预期不满足；必须关联 Batch 56 缺陷 ID |
| `BLOCKED` | 权限、网络、环境、外部服务或必要数据缺失；必须登记解除条件 |
| `NOT RUN` | 尚未执行；P0/P1 的 `NOT RUN` 不得放行 |

禁止使用“部分通过”“基本可用”“HTTP 200”“页面能打开”“源码存在”替代以上状态。一个旅程同时有成功和失败证据时按 `FAIL`；有已通过子项但仍缺必要外部条件时按 `BLOCKED`；只有设计或历史证据时按 `NOT RUN`。

### 2.2 证据最小字段

每条执行证据必须包含：

| 字段 | 要求 |
| --- | --- |
| `case_id` | 使用 `Jxx-P`、`Jxx-N` 或关联的细分用例 ID |
| `commit_sha` | 执行时完整 Git SHA；工作区不干净时不得形成放行证据 |
| `executed_at` | ISO 8601 时间，含时区 |
| `environment_id` | 只写逻辑 ID，如 `R0-LOCAL-PLATFORM`；不得写敏感地址 |
| `input_id` | R0/R1/R2/M 输入 ID |
| `command_or_steps` | 可复现命令或可复现 UI 步骤 |
| `exit_code` | 自动化命令必须填写 |
| `expected` / `actual` | 可观察的预期与实际差异 |
| `artifact_ref` | 脱敏截图、Trace、请求响应、DB/审计查询或命令输出 |
| `redaction` | `PASS` 才可进入交付证据索引 |
| `cleanup` | 写操作必须记录回读和清理结果 |

建议将后续脱敏执行证据索引到 `test-platform-v2/work-logs/evidence/batch-56-production-acceptance/`；本文件只登记逻辑引用，不提交原始凭据、浏览器会话、数据库或未脱敏产物。

## 3. 代码与环境预执行基线

| 项 | 预执行观测 | 当前状态 | 最终执行要求 |
| --- | --- | --- | --- |
| 分支 | `feature/batch-56-full-platform-production-acceptance` | 已确认 | 执行前再次确认 |
| worktree | Batch 56 独立 Codex Agent Team worktree | 已确认 | 不得与其他任务复用数据库和端口 |
| `origin/main` 起始基线 | `206802431d487a517f3c6d8901143825e11f0ea7` | 已确认 | 保留为批次起点 |
| 创建本文时 HEAD | `457d159c49b3eae9c2099cdde85cba0791ddadc2` | 非最终执行 SHA | 开发完成且工作区干净后重新冻结 |
| 前端/后端端口 | `5173` / `8000` | 元数据已配置，运行未验证 | 健康检查、登录和受保护路由均需真实通过 |
| 数据库 | 独立 PostgreSQL | 未验证 | 记录类型、版本、逻辑库 ID、迁移状态，不记录密码 |
| 浏览器 | Playwright Chromium | 未执行 | 记录实际版本和三视口结果 |
| 外部访问 | 由授权环境和 ignored 配置注入 | 未预检 | 不读取或提交凭据；按 R0 逻辑 ID 留证 |

## 4. R0/R1/R2/M 真实输入清单

### 4.1 输入等级

| 等级 | 定义 | 可以证明 | 不能单独证明 |
| --- | --- | --- | --- |
| R0 | 当前获授权的真实客户环境、页面、契约、服务、设备或旧数据 | 当前连通性和真实外部行为 | 未授权写入、生产负载安全 |
| R1 | 从 R0/客户资产派生且已脱敏、带来源/时间/SHA-256/脱敏日志的不可变快照 | 可重复的真实业务结构与内容约束 | 当前实时连通性 |
| R2 | 从 R1 schema、枚举、约束和数据分布生成的生产形态数据 | 边界、分页、并发、RBAC、非法输入 | 客户主路径真实可用 |
| M | mock、stub、故障注入和确定性演示数据 | 难以稳定触发的异常 UI/服务状态 | 任何生产主路径通过 |

### 4.2 R0 清单

| 输入 ID | 输入用途 | 允许动作 | 当前状态 | 进入执行的必要证据 |
| --- | --- | --- | --- | --- |
| `R0-LOCAL-PLATFORM` | 本地 React → FastAPI → PostgreSQL 平台 | 本地受控增改查与清理 | `NOT RUN` | 前后端健康、迁移、登录、受保护路由、数据库定位信息 |
| `R0-SPORTS-PROD-READONLY` | 体育平台生产页面/API 对照 | 仅 GET/HEAD；禁止登录尝试、写入、支付、发布、重放和压测 | `BLOCKED` | 当前 VPN/访问授权和脱敏只读网络证据 |
| `R0-SPORTS-TEST` | 体育平台测试用户端和内部 API | 默认只读；受控写入须明确授权、唯一前缀、回读和清理 | `BLOCKED` | 当前授权范围、可恢复数据说明、清理证明 |
| `R0-ADMIN-TEST` | 运营后台测试环境 | 默认只读；不得改共享配置或触发广播/任务 | `BLOCKED` | 当前授权会话、可执行动作清单 |
| `R0-LANHU-USER` | 用户端蓝湖需求源 | 只读提取 | `BLOCKED` | 可访问性、目标范围、采集时间和脱敏证据 |
| `R0-LANHU-ADMIN` | 运营后台蓝湖需求源 | 只读提取 | `BLOCKED` | 可访问性、目标范围、采集时间和脱敏证据 |
| `R0-OAS-SIX-LIVE` | Test5 六服务实时 OpenAPI/Knife4j | 只读拉取和契约对比 | `BLOCKED` | 六服务来源数、拉取时间、每份 SHA-256、解析结果 |
| `R0-AI-LIVE` | 真实 LLM/OCR 需求解析、生成和 Agent | 仅最小必要客户脱敏输入 | `BLOCKED` | 服务配置有效、无 fallback、调用与输出已脱敏 |
| `R0-ELK-READONLY` | 测试/生产日志与 trace 对照 | 只读查询 | `BLOCKED` | 内网授权、查询范围和脱敏 trace 结果 |
| `R0-MEDIA-DEVICE` | 真实媒体流、ffprobe 和物理设备 | 测试环境低影响检查；生产不压测 | `BLOCKED` | 设备/流授权、采样窗口、清理或无副作用声明 |
| `R0-LEGACY-PG` | 真实旧版 PostgreSQL 数据 | 仅隔离脱敏副本升级 | `BLOCKED` | 快照来源、版本、SHA-256、行数基线和恢复副本 |

### 4.3 已固定的仓库 R1

以下 `AVAILABLE` 只表示文件存在且本轮已计算 SHA-256，不表示任何 J 旅程或 A 门禁通过。

| 输入 ID | 仓库路径 | 字节数 | SHA-256 | 适用范围 |
| --- | --- | ---: | --- | --- |
| `R1-PLATFORM-PRD` | `test-platform-v2/docs/CamelTv测试平台-完整PRD.md` | 21229 | `cefc99292ab1b92563368e82ae0449057affa443ac895323456eb5b3169b2ddf` | 全平台需求基线 |
| `R1-CURRENT-PRD` | `test-platform-v2/docs/现状功能PRD.md` | 23528 | `ce46bf066183459601dd4283802f602aba1faca69e65096f218a4477879147e2` | 当前实现范围 |
| `R1-API-PRD` | `test-platform-v2/docs/接口测试模块优化PRD.md` | 15307 | `71f4f2fb8d238620202923603e258f2be6495a683c492ed2ca7bdafda8cfe0ce` | API 测试模块 |
| `R1-TEST5-HISTORY` | `test-platform-v2/docs/DEV-Test5-使用与授权清单.md` | 7521 | `64b5f362efa45afb6599bb72c79531473693eee37b9092275916b6ac87941941` | 历史导入规模与授权边界，不作当前连通证据 |
| `R1-LANHU-RUNBOOK` | `test-platform-v2/docs/蓝湖证据包OCR导入-运维与验收手册.md` | 5969 | `b7b45847a653ecd653fd29c36bf098d4c61dd938df8172cdc8c2368cff11650d` | 蓝湖证据包结构与验收方法 |
| `R1-USER-REQ` | `tests/requirements/documents/用户端原型-需求分析.md` | 19430 | `0ac601bc19a01c456bf42638473548ceeb277f8b33e74f7c28d68028b465ca02` | 用户端 8 大业务域 |
| `R1-ADMIN-REQ` | `tests/requirements/documents/运营后台-需求分析.md` | 31062 | `e1282cc4fa3b0bf7c199254c28aa29231ab7dbad90fef597be492d9e04b02e59` | 运营后台 9 大业务类别 |
| `R1-V13-REQ` | `tests/requirements/documents/13.0-baseline.md` | 3313 | `ac65e73c2f0f592439c1b6c7c1b100bd635445b948722a4d866946910b15b271` | 版本基线 |
| `R1-V14-REQ` | `tests/requirements/documents/14.0-features.md` | 5541 | `3d59a728507d8b0f7b4e03e37805129ee9d7823a2cfa63825527f2c2c4b10eb6` | 当前核心需求 |
| `R1-USER-CASES` | `tests/test-cases/functional/BASELINE-用户端-基线功能.md` | 60224 | `6fa83d83db899fb1e4757f5c5ca691aac797581b76bea6737d938f2764f6b11e` | 用户端功能与 API 场景 |
| `R1-ADMIN-CASES` | `tests/test-cases/functional/ADMIN-运营后台-全版本.md` | 97965 | `9459497f0b589c37154c42da97ed6c66cb9ba5612b422fb60d94dd050a8df232` | 后台功能与 API 场景 |
| `R1-LATEST-CASES` | `tests/test-cases/体育平台最新版本-测试用例.md` | 38072 | `95d41a415c5e3e723e1967a6d9ebaa183f718d32ada1a29620188c7b070a9d88` | 最新版本 P0/P1 场景 |
| `R1-TRACE-V14` | `tests/requirements/traceability-matrix/matrix-v14.csv` | 12668 | `59abbf7bbd5ac6ecd0034938bb04363e46764a0e3598a0b5e324abdaec59e4de` | 108 条有效已覆盖需求的追溯种子 |
| `R1-OAS-NARROW` | `test-platform/tests/api-testing/specs/cameltv-openapi.yaml` | 4285 | `79ad14de7d7afaeac21cf0f7981194f6cb54e3cc38702c1a48c7de1a319d3883` | 仅 5 个 path 的历史静态契约，不代表六服务全量 |

### 4.4 必须补齐的 R1、R2 与 M

| 输入 ID | 等级 | 当前状态 | 用途 | 关闭条件 |
| --- | --- | --- | --- | --- |
| `R1-LANHU-USER-PACK` | R1 | `BLOCKED` | 用户端页面树、截图、OCR/合并文本、产物和追溯引用 | 从 R0 重新采集或导出脱敏不可变证据包并登记 SHA-256 |
| `R1-LANHU-ADMIN-PACK` | R1 | `BLOCKED` | 后台页面树、截图、OCR/合并文本、产物和追溯引用 | 同上 |
| `R1-OAS-SIX-SNAPSHOT` | R1 | `BLOCKED` | 六服务确定性接口回归 | 从 R0 拉取六份脱敏快照，记录捕获时间和 SHA-256 |
| `R1-HAR-SANITIZED` | R1 | `BLOCKED` | 页面网络、GET 次数和接口追溯 | 完成 R0 只读/测试链路并脱敏导出 |
| `R1-LEGACY-PG-SNAPSHOT` | R1 | `BLOCKED` | A10 升级、行数、索引、关系和重复升级 | 取得授权脱敏副本和快照说明 |
| `R2-PAGINATION-LARGE` | R2 | `NOT RUN` | 超过一页的查询、排序、搜索和 count | 从 R1 字段约束生成并记录生成规则 |
| `R2-RBAC-PROJECT-AB` | R2 | `NOT RUN` | 管理员、测试员、受限用户及 Project A/B | 经公开 API/seed 创建并验证清理 |
| `R2-CONCURRENCY-IDEMPOTENCY` | R2 | `NOT RUN` | 重复导入、任务、调度、并发写与重试 | 在真实 PostgreSQL 多连接执行 |
| `R2-INVALID-BOUNDARY` | R2 | `NOT RUN` | 空/null、超长、错误类型/枚举/ID、损坏文件、坏 OAS | 从真实 schema 派生边界表 |
| `R2-MEDIA-BOUNDARY` | R2 | `NOT RUN` | 损坏、短时长、可变帧率和弱网 | 记录生成/来源、预期和清理 |
| `M-FAILURE-INJECTION` | M | `NOT RUN` | 网络超时、5xx、Worker 崩溃、通知失败 | 真实成功主链路先通过，再单独执行 |
| `M-UI-STATES` | M | `NOT RUN` | loading、empty、error UI | 真实有数据路径先通过，再单独执行 |
| `M-OCR-LLM-STUB` | M | `NOT RUN` | OCR/LLM 确定性回归 | 只能进入 M 结果，不得解除真实服务阻断 |

## 5. J01–J22 可执行旅程矩阵

### 5.1 通用执行协议

每个 J 旅程至少拆为两个原子结果：

- `Jxx-P`：使用 R0 或 R1 的正面主流程。
- `Jxx-N`：使用同一真实 schema 派生的负面、越权、边界、回滚或异常流。

写操作一律使用本批次唯一前缀，通过真实 UI 或公开 API 创建；执行后必须回读 UI/API/DB/审计/任务状态，并在 `finally` 清理。不得直接插库制造主路径通过。生产外部环境只读。

### 5.2 旅程状态

| ID | 优先级 | 模块与入口 | 主输入 | 正面/负面执行要点与可观察预期 | A 门禁 | 当前状态 | 当前证据 | 阻断或下一动作 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| J01 | P0 | 登录、会话、注销；`/login`、auth | `R0-LOCAL-PLATFORM`、`R2-INVALID-BOUNDARY` | P：可见表单登录后进入受保护页，会话和登录审计一致。N：错密、空值、过期会话被拒，不能创建有效会话或泄露账号状态 | A02–A06/A09/A12 | `NOT RUN` | Batch 55 仅有登录壳历史证据，不计本批次执行 | 固定 SHA 后验证本地 PostgreSQL、真实会话和审计 |
| J02 | P0 | 工作台、Dashboard；`/workbench`、dashboard | J05–J13 产生的真实关联数据 | P：需求、用例、计划、执行、缺陷、报告计数与下游一致。N：空项目和受限角色不显示其他项目名称、数量或结构 | A03/A05/A06/A08/A09 | `NOT RUN` | 无 Batch 56 执行证据 | 先完成关联数据主链，再核对 UI/API/count |
| J03 | P0 | 项目、系统、用户、角色、Token；`/project`、`/system` | `R0-LOCAL-PLATFORM`、`R2-RBAC-PROJECT-AB` | P：管理员建立两项目和角色，授权后操作生效。N：低权限、跨项目、已撤权身份对列表/详情/子资源/写操作均无泄露 | A03–A07/A09/A12 | `NOT RUN` | 无 Batch 56 执行证据 | 通过公开接口准备 Project A/B 和三类身份 |
| J04 | P0 | 环境、数据集、集成；`/environment`、`/dataset`、`/integration` | `R0-SPORTS-TEST`、`R0-OAS-SIX-LIVE`、`R2-INVALID-BOUNDARY` | P：脱敏变量、数据集和集成配置可创建、验证、引用、更新、删除。N：密钥不回显，坏文件/坏地址/跨项目引用被拒且无副作用 | A03–A09/A12 | `BLOCKED` | 仅有环境文档索引；无当前连通或授权证据 | 明确测试环境动作授权并完成本地平台预检 |
| J05 | P0 | 需求、需求模块、审查；`/requirement`、动态 review | `R1-USER-REQ`、`R1-ADMIN-REQ`、`R1-V14-REQ` | P：真实需求文档导入、解析、模块化、人工审查并持久化。N：空/损坏/重复/越权输入被拒或幂等，失败不产生半成品 | A03–A09/A12 | `NOT RUN` | R1 文件和 SHA 已登记；未执行导入 | 在真实 PostgreSQL 通过 UI/公开 API 执行正负面 |
| J06 | P0 | 蓝湖证据包、OCR、需求模块 | `R0-LANHU-USER`、`R0-LANHU-ADMIN`、两份缺失的 R1 证据包 | P：页面树、截图、OCR、合并文本、Job/Page ID 和需求追溯闭环。N：附件失败进入可观察人工处理，不伪造成成功 | A03–A07/A09/A12 | `BLOCKED` | 只有历史“已采集”文档和运行手册；当前原始证据包缺失 | 重新采集或导出脱敏、带 SHA 的两端证据包 |
| J07 | P0 | 知识、RAG、Wiki、Agent；`/knowledge`、`/agent-workbench` | J06 证据包、`R0-AI-LIVE`、R1 版本/追溯文档 | P：摄取、切片、检索、Wiki 生成/对比、Agent 任务结果均引用真实来源。N：服务失败、无权限、无来源时不生成假结论且可重试 | A03–A07/A09/A12 | `BLOCKED` | C55-3 仍 Open；无本批次真实 AI/蓝湖证据 | 完成 J06 并验证真实 AI/OCR 无 fallback |
| J08 | P0 | 测试用例、脑图；`/testcase`、`/mindmap` | 三套 R1 用例、J05 审查结果、`R2-PAGINATION-LARGE` | P：从真实需求生成/导入用例和脑图并关联需求。N：重复、坏格式、越权、无来源被拒；跨页搜索/排序/count 一致 | A03–A09/A12 | `NOT RUN` | 用例资产和 SHA 已登记；未导入 | 先完成 J05，再执行正负面和大分页 |
| J09 | P0 | 测试计划、计划详情、执行 | J08 的真实用例、`R2-CONCURRENCY-IDEMPOTENCY` | P：创建计划、关联用例、执行、刷新后状态持久。N：非法状态迁移、重复点击、并发执行、取消/重试保持唯一且可恢复 | A03–A09 | `NOT RUN` | C55-4 仍 Open；无本批次浏览器链路 | 完成 J08 后走真实 UI/API/DB/审计闭环 |
| J10 | P0 | 报告、报告模板；`/report` | J09 执行、J12 缺陷、J13 追溯 | P：报告与模板生成、查看、导出，统计与真实执行一致。N：无数据、跨项目、失败执行和坏模板不产生假报告 | A03–A06/A08/A09/A12 | `NOT RUN` | 无 Batch 56 执行证据 | 依赖 J09/J12/J13 的同源数据 |
| J11 | P1 | 定时任务、通知；`/schedule`、`/notify` | J09 计划、授权通知端点、`M-FAILURE-INJECTION` | P：调度触发一次、状态/审计/通知可追溯。N：重复触发、无权限、端点失败可重试且不重复业务执行 | A03–A07/A09 | `BLOCKED` | 无当前通知服务授权或运行证据 | 先用本地授权端点完成真实成功流，再单列 M 失败流 |
| J12 | P0 | 缺陷管理；`/defect` | J09 的真实失败执行、R1 用户/后台预期 | P：从失败执行建缺陷并完成合法状态迁移，关联/计数/审计一致。N：非法迁移、越权、重复提交被拒且不漂移 | A03–A07/A09/A12 | `NOT RUN` | C55-4 仍 Open；无本批次缺陷状态机证据 | 用 J09 可复现失败结果创建缺陷 |
| J13 | P0 | 质量追溯；`/trace` | `R1-TRACE-V14`、J05/J08/J09/J12 | P：需求→用例→计划/执行→缺陷/报告同源可钻取，覆盖率计算正确。N：断链、重复关联、跨项目数据不计入且有明确状态 | A03–A06/A08/A09/A12 | `NOT RUN` | 108 条 R1 有效需求行已登记；未形成当前执行链 | 导入矩阵并与 J05/J08/J09/J12 实体关联 |
| J14 | P0 | API 测试、OpenAPI、调试、执行；`/apitest` | `R0-OAS-SIX-LIVE`、`R1-OAS-NARROW`、`R2-INVALID-BOUNDARY` | P：六服务拉取、解析、资产/用例生成、授权调试和断言执行。N：坏 schema、错参、业务拒绝、响应错误、跨项目资产被准确判失败 | A03–A09/A11/A12 | `BLOCKED` | 静态 R1 仅 5 paths；历史 892 资产/1323 候选记录不能证明当前状态 | 获取六服务实时契约或脱敏六份 R1 快照 |
| J15 | P0 | UI 自动化、Playground；`/uitest`、playground | R1 P0 用例、真实浏览器、授权外部只读页面 | P：真实用例生成 TypeScript、编译、Playwright 运行并产出截图/Trace/报告。N：编译错误、元素不存在、超时明确失败，不接受 route mock 通过 | A03/A04/A06/A07/A09/A11 | `BLOCKED` | C55-4/C55-5 未关闭；无本批次真实执行 | 本地真实页面先通过；外部页面需当前只读访问授权 |
| J16 | P1 | 音视频专项；`/special`、av-checks | `R0-MEDIA-DEVICE`、`R2-MEDIA-BOUNDARY` | P：真实流/文件的格式、帧率、音轨和健康结果可复核。N：损坏/短时长/可变帧率/弱网被准确识别且任务可恢复 | A03/A04/A07/A09/A11 | `BLOCKED` | 仅有历史材料，无当前真实媒体/设备证据 | 提供获授权媒体样本或测试设备，生产不压测 |
| J17 | P0 | 版本任务、发布包、详情、全景；`/release-bundles` 及动态路由 | R1 V13/V14、J05–J13 同源数据 | P：创建版本任务/发布包，详情和全景展示同一需求、用例、执行、缺陷和风险。N：不完整链、跨项目引用、重复发布被拒 | A03–A09/A12 | `NOT RUN` | R1 版本需求已登记；未执行 | 依赖 J05–J13 完整关联链 |
| J18 | P1 | 性能、设备、历史、WebSocket；`/perftest` | 测试环境安全端点、真实设备、R2 本地负载 | P：测试环境或本地受控负载可启动、观测、停止并持久化。N：无权限、断连、取消、重复启动和阈值失败状态准确 | A03/A04/A07/A09/A11 | `BLOCKED` | 无获授权目标和本批次运行证据 | 指定非生产安全端点、负载上限和停止条件 |
| J19 | P0 | 跨模块 RBAC、分页、搜索、count、幂等 | `R2-RBAC-PROJECT-AB`、`R2-PAGINATION-LARGE`、`R2-CONCURRENCY-IDEMPOTENCY` | P：所有列表/详情/写接口在同一过滤条件下 UI/API/DB/count 一致。N：跨项目 ID、N+1 页、重复/并发请求不泄露、不重复、不漂移 | A05–A08/A12 | `NOT RUN` | 无 Batch 56 横向矩阵证据 | J03–J18 主流程可用后执行横向专项 |
| J20 | P0 | 六主题、全部静态/动态路由、三视口、a11y、network；含 `/theme-lab` | J01–J18 的真实填充数据、真实浏览器 | P：六主题和支持模式下页面语义、主要操作、表单/表格/弹窗可用。N：空/错/加载状态仍可理解；无 serious/critical Axe、溢出、控制台错误、重复有效 GET | A03/A06/A09/A12 | `NOT RUN` | C55-5 仍 Open；Batch 55 仅登录壳局部证据 | 先准备有效动态路由实体，再执行 1440/768/390 三视口 |
| J21 | P0 | 体育生产只读、体育测试、运营后台测试和需求源对照 | 对应外部 R0 + 用户/后台 R1 | P：生产只读页面、测试用户端、后台和需求预期逐项对照。N：未授权动作不执行；访问失败明确阻断，不以测试成功推断生产写可用 | A01/A03/A04/A09/A12 | `BLOCKED` | 环境索引存在；未读取凭据、未执行外部访问 | 完成 VPN、会话、只读/写授权边界预检 |
| J22 | P0 | PostgreSQL 迁移、双端全量、构建、供应链和文档一致性 | `R0-LEGACY-PG`/`R1-LEGACY-PG-SNAPSHOT`、当前代码 | P：旧库升级、数据保留、重复升级、唯一 head、零漂移；双端全量和构建通过。N：升级失败可恢复；新增回归和 high/critical 风险阻断 | A01/A02/A10–A12 | `BLOCKED` | Batch 55 历史门禁不继承；当前缺旧 PG 快照，Batch 56 全量未执行 | 先补旧库输入，再在最终干净 SHA 执行全部命令和审计 |

## 6. A01–A12 证据矩阵

该矩阵是 Batch 56 初始状态。历史证据只进入“已知基线”，不会把本批次状态提升为 `PASS`。

| 门禁 | 必须完成的 Batch 56 验证 | 输入/J 旅程 | 当前状态 | 当前证据 | 缺口或解除条件 |
| --- | --- | --- | --- | --- | --- |
| A01 基线可追溯 | 固定最终 SHA、需求/API/历史缺陷/功能点/用例映射和差异清单 | 全部 R1；J01–J22 | `NOT RUN` | R1 路径和 SHA 已登记；起始 main 已固定 | 并行开发未结束；需冻结干净执行 SHA，并补完整功能点正负面映射 |
| A02 隔离环境 | 独立 worktree、5173/8000、独立 PostgreSQL、配置和清理 | `R0-LOCAL-PLATFORM`；J01/J03/J22 | `NOT RUN` | Agent Team 元数据存在 | 未执行健康、迁移、数据库定位和登录预检 |
| A03 主/备选/异常流 | 每个功能点至少一正一负，P0/P1 全执行 | J01–J22 | `NOT RUN` | 只有旅程设计和历史用例资产 | 尚无本批次逐条执行结果 |
| A04 API 三类校验 | 入参、业务、返回值；写操作核对 DB/审计/任务 | J01/J03–J18/J21 | `NOT RUN` | 静态 OAS 仅作受限 R1 | 六服务实时契约缺失；全 API 三类校验未执行 |
| A05 RBAC/项目隔离 | 无权限、低权限、跨项目的列表/详情/子资源/写操作 | J01–J04/J06–J19 | `NOT RUN` | R2 Project A/B 设计完成 | 未通过真实 API/seed 创建并执行身份矩阵 |
| A06 UI/API/DB/审计一致 | 页面、响应、DB、计数、审计同时成功或回滚 | J01–J20 | `NOT RUN` | 无本批次端到端事务证据 | 需要至少一条完整客户链并覆盖所有写域 |
| A07 幂等/并发/重试 | 重复点击、并发写、超时重试、恢复和最终唯一状态 | J03–J19 | `NOT RUN` | R2 并发输入设计完成 | 未在真实 PostgreSQL 多连接执行 |
| A08 跨页查询一致 | 超过一页，搜索/筛选/排序/page/total/count 同条件 | J02/J04/J05/J08–J20 | `NOT RUN` | R2 大分页输入设计完成 | 尚未从 R1 约束生成并通过 UI/API/DB 核对 |
| A09 浏览器/a11y/network | 三视口、键盘、焦点、Axe、控制台、网络、完整 P0 旅程 | J01–J21 | `NOT RUN` | Batch 55 登录壳历史结果不计当前通过 | 六主题、全部动态路由和真实数据旅程未执行 |
| A10 真实旧库迁移 | 真实旧版脱敏快照升级、数据保留、重复升级、唯一 head、零漂移 | `R0-LEGACY-PG`/`R1-LEGACY-PG-SNAPSHOT`；J22 | `BLOCKED` | 仅有历史空库/旧批次材料 | 当前没有可用旧 PostgreSQL 脱敏快照 |
| A11 自动化/供应链 | F821、Pytest、typecheck、Vitest、build、Playwright、依赖/许可证/漏洞 | J14–J22 | `NOT RUN` | Batch 55 历史全量不继承 | 在最终干净 SHA 执行并记录命令、退出码和完整失败集合 |
| A12 文档/证据一致 | PRD、OAS、README、ADR、用例、报告、代码事实和脱敏证据一致 | 全部输入；J01–J22 | `NOT RUN` | 本文件建立了预执行索引 | 执行、缺陷、QA、Leader Verdict 和最终 SHA 尚未生成/核对 |

## 7. R0/R1/R2/M 计分与发布规则

### 7.1 原子结果

1. 每个 J 旅程至少产生 `Jxx-P` 和 `Jxx-N` 两个原子结果。
2. 原子结果必须声明输入等级；混合输入以主断言依赖的最低真实等级记录，例如真实主数据 + R2 边界仍分别记录为 R1 主路径和 R2 边界。
3. 一条原子结果包含多个必须断言时，只有全部满足才是 `PASS`。
4. `BLOCKED` 和 `NOT RUN` 始终进入分母，不得从通过率中删除。

### 7.2 分层计分

```text
R0_P0P1_真实通过率
= R0 的 P0/P1 PASS 数
  / R0 的 P0/P1（PASS + FAIL + BLOCKED + NOT RUN）数 × 100%

R1_P0P1_真实通过率
= R1 的 P0/P1 PASS 数
  / R1 的 P0/P1（PASS + FAIL + BLOCKED + NOT RUN）数 × 100%

R2_边界回归通过率
= R2 PASS 数 / R2（PASS + FAIL + BLOCKED + NOT RUN）数 × 100%

M_故障回归通过率
= M PASS 数 / M（PASS + FAIL + BLOCKED + NOT RUN）数 × 100%
```

规则：

- 生产真实验收只看 R0/R1；R2 和 M 必须单独展示，权重为 0，不得与 R0/R1 加权成一个更高分。
- 标记为“R0 必需”的旅程不能用 R1、R2 或 M 替代。例如实时六服务契约、生产只读链路和真实旧库缺失时保持阻断。
- R1 必须有来源、捕获时间、SHA-256 和脱敏记录；仅有历史说明文档但没有源产物时不能计为 R1 通过。
- 对同一旅程，J 状态按 `FAIL` > `BLOCKED` > `NOT RUN` > `PASS` 汇总。

### 7.3 发布结论

| 结论 | 机械条件 |
| --- | --- |
| `READY` | R0/R1 的 P0/P1 原子结果 100% PASS；A01–A12 全部 PASS；无 P0/P1 阻断/未执行；无严重未关闭缺陷；R2/M 结果单列 |
| `CONDITIONAL` | 仅剩经书面批准的 P2/P3 风险，且有责任人、到期日和批准证据；不得包含安全隔离、事务、数据、A10 或外部关键链路风险 |
| `NEEDS WORK` | 任一 P0/P1 FAIL/BLOCKED/NOT RUN，或任一 A 门禁非 PASS，或证据不足/矛盾/泄密 |

全量测试、构建、HTTP 200、静态源码扫描、mock 测试或旧批次通过均不能单独把结论提升为 `READY`。

## 8. 缺口登记

| Gap ID | 优先级 | 状态 | 缺口与影响 | 责任角色 | 解除条件 | 复测时限 |
| --- | --- | --- | --- | --- | --- | --- |
| `G56-001` | P0 | `OPEN` | 最终代码 SHA 尚未冻结，当前有并行开发改动；A01/A11 不能判定 | 开发负责人 / QA | 开发停止变更、worktree 干净、记录最终 SHA 和差异清单 | 条件具备后立即 |
| `G56-002` | P0 | `OPEN` | 本地 5173/8000/PostgreSQL 尚无完整健康、登录、迁移和隔离证据 | 开发负责人 / QA | 完成 R0 本地平台预检和专用清理验证 | 条件具备后 1 个工作日内 |
| `G56-003` | P0 | `BLOCKED` | 体育生产只读、体育测试和运营后台测试未完成当前授权/网络预检；J04/J21 阻断 | 环境所有者 / QA | 明确只读/写边界并提供当前可用授权会话，不把凭据写入仓库 | 条件具备后 1 个工作日内 |
| `G56-004` | P0 | `BLOCKED` | 用户端与运营后台蓝湖只有历史采集声明，当前缺原始或脱敏证据包；J06/J07 阻断 | 产品负责人 / QA | 重新采集或导出两端证据包，含来源、时间、SHA 和脱敏记录 | 条件具备后 1 个工作日内 |
| `G56-005` | P0 | `BLOCKED` | 六服务实时 OpenAPI 和不可变快照缺失；静态 OAS 仅 5 paths；J14 阻断 | 服务负责人 / QA | 拉取六服务实时契约或提供六份脱敏 R1 快照 | 条件具备后 1 个工作日内 |
| `G56-006` | P0 | `BLOCKED` | 真实 LLM/OCR 配置和无 fallback 证据缺失；J07 阻断 | AI 服务负责人 / QA | 验证真实服务调用、输出来源与脱敏，关闭 fallback | 条件具备后 1 个工作日内 |
| `G56-007` | P1 | `BLOCKED` | ELK 只读权限和当前 trace 证据缺失，跨系统审计能力不能证明 | 运维负责人 / QA | 提供当前只读访问并保存脱敏 trace 查询结果 | 条件具备后 1 个工作日内 |
| `G56-008` | P1 | `BLOCKED` | 真实媒体流/物理设备和安全测试窗口缺失；J16 阻断 | 媒体服务负责人 / QA | 提供授权样本/设备、采样窗口和无生产负载声明 | 条件具备后 1 个工作日内 |
| `G56-009` | P0 | `BLOCKED` | 缺真实旧 PostgreSQL 脱敏快照；A10/J22 必然阻断 | 数据库负责人 / QA | 提供隔离脱敏快照、版本、SHA、行数基线和恢复副本 | 条件具备后 1 个工作日内 |
| `G56-010` | P1 | `BLOCKED` | 性能测试缺少获授权非生产目标、负载上限和停止条件；J18 阻断 | 性能负责人 / 环境所有者 | 明确安全端点、负载模型、上限、停止和清理规则 | 条件具备后 1 个工作日内 |
| `G56-011` | P0 | `OPEN` | C55-3 Knowledge/Wiki/Trace 深层功能尚未以当前真实输入闭环 | 开发负责人 / QA | J06/J07/J13 的 P/N 原子结果全部 PASS | 修复后 1 个工作日内 |
| `G56-012` | P0 | `OPEN` | C55-4 真实浏览器关键业务旅程尚未完成 | 开发负责人 / QA | J05/J08/J09/J10/J11/J12 的真实 UI/API/DB/审计链全部 PASS | 修复后 1 个工作日内 |
| `G56-013` | P0 | `OPEN` | C55-5 六主题、全部路由、三视口、a11y/network 尚未完成 | 前端负责人 / QA | J20 全矩阵 PASS，动态路由使用真实实体 | 修复后 1 个工作日内 |
| `G56-014` | P0 | `OPEN` | 全平台正负面功能点矩阵尚未逐项关联 J01–J22 和现有用例 ID | QA 负责人 | 每个需求点至少一正一负；API 三类校验齐全 | J 执行开始前 |
| `G56-015` | P0 | `OPEN` | Batch 56 双端全量、真实 E2E、依赖/许可证/漏洞审计未执行 | 开发负责人 / QA | 最终干净 SHA 上运行 A11 全部命令并记录完整失败集合 | 交付判定前 |
| `G56-016` | P0 | `OPEN` | QA 报告、Leader Verdict、缺陷、证据索引和代码事实尚未对账 | QA Leader | 按 A12 完成逐 ID 对账和脱敏扫描 | 交付判定前 |

## 9. 执行与回填顺序

1. 关闭 `G56-001`：冻结最终干净 SHA、范围和历史缺陷基线。
2. 执行 A02 本地预检：PostgreSQL 迁移、后端健康、前端 5173、真实登录和清理。
3. 固定 R1 哈希；对所有新增 R1 补来源、捕获时间和脱敏日志。
4. 按 J01 → J03 → J05 → J08 → J09 → J12 → J13 → J10 建立第一条真实关联链。
5. 执行 J02/J17 验证工作台、发布包和全景对同一链的统计与展示。
6. 执行 J04/J06/J07/J14/J15/J16/J18/J21 的授权外部或专项链；缺条件保持 `BLOCKED`。
7. 执行 J11、J19、J20 的通知、横向 RBAC/分页/并发和六主题全路由矩阵。
8. 执行 J22 的真实旧库迁移、双端全量、真实 Playwright 和供应链审计。
9. 回填每个 `Jxx-P/Jxx-N` 的实际结果、证据、缺陷和清理；重新计算四个分层通过率。
10. 逐项更新 A01–A12；任何非 PASS 门禁都使最终结论保持 `NEEDS WORK`。
11. 完成证据脱敏扫描和 A12 对账后，再生成 Batch 56 QA 报告与 Leader Verdict。

## 10. 安全复核清单

- [x] 文档和证据中无密码、Token、Cookie、Authorization、私钥和数据库连接串。
- [x] 外部环境只用逻辑 ID，不包含敏感主机、路径、查询参数或内部网络拓扑。
- [x] 截图、HAR、Trace、请求响应、日志和 DB 查询已去除个人信息与真实生产数据。
- [x] 生产体育环境只有 GET/HEAD，无登录尝试、写入、支付、发布、重放或压测。
- [x] 测试环境写操作有授权、唯一标识、状态回读、`finally` 清理和清理复核。
- [x] R2/M 结果与 R0/R1 分开统计，没有以模拟结果关闭真实阻断。
- [x] `BLOCKED` 和 `NOT RUN` 没有计为通过或从分母删除。
- [x] 最终状态只引用当前固定 SHA 的证据，没有继承 Batch 47/48/55 的 PASS。

## 11. Batch 56 执行回填（权威摘要）

### 11.1 固定代码与本地环境

| 项 | 执行结果 | 状态 |
| --- | --- | --- |
| 固定代码 | `30c76a4ddeebf485e8285ae1e8b0effc2ff71fcf` | PASS |
| worktree / 执行器 | 独立 Agent Team worktree / Codex | PASS |
| 启动证据 | 端口占用 fail-closed；listener 命令含本 worktree 绝对路径；runtime manifest 的 SHA 与 clean 状态匹配 | PASS |
| 本地数据层 | PostgreSQL 16、Alembic 唯一 head、`alembic check` 无新增操作 | PASS |
| 本地 UI | `http://localhost:5173/` 保持运行，后端为 `127.0.0.1:8000` | PASS |

### 11.2 自动化、构建与运行时门禁

| 门禁 | 结果 | 状态 |
| --- | --- | --- |
| 后端 F821 | 0 项 | PASS |
| 后端全量 Pytest | 860 collected；857 passed、3 个仅限显式 PostgreSQL 集成的 skip、0 failed | PASS |
| PostgreSQL 并发回归 | 3/3 passed | PASS |
| 前端 Vitest | 52 files、210 tests、0 failed | PASS |
| TypeScript / build | typecheck 与 Vite production build 均成功 | PASS |
| 真实后端 Playwright | desktop 30 路由、mobile 16 路由，2/2 passed；无 route fulfill/mock/skip | PASS |
| 历史 UI 专项 | Batch 53、54、55 的需求模块、主题、未授权和代理/a11y 共 4/4 passed | PASS |
| 性能 WS 传输 | Vite 真实 101、Cookie/Origin/项目权限通过；无 SoloX 时返回 `collector_error` 并清理 | PASS（传输）/ BLOCKED（真机采集） |
| 容器 | backend/frontend 实际构建成功；Nginx 配置通过；非 root UID 10001、volume 初始化及写入探针通过 | PASS |
| 供应链 | Python Linux hash lock、Playwright 1.61.0 双端一致、基础镜像 digest 固定、`pip check` 通过 | PASS |
| 前端 npm audit | high/critical 为 0；React Router 留有 2 个 moderate，修复要求破坏性大版本升级 | RISK |

### 11.3 真实客户输入与横向安全

| 旅程 | 实际结果 | 状态 |
| --- | --- | --- |
| 真实需求上传 | 用户端、运营后台两份 R1 文档经公开 API 上传、解析、回读和审计；解析正文非空 | PASS |
| 登录与错误密码 | admin/tester 登录成功，错误密码 401 | PASS |
| 跨项目 RBAC | tester 对非成员项目访问返回 403；性能 REST/WS 新增双项目 IDOR 回归 | PASS |
| 真实 AI 提取 | 无 Key 时业务 400，未生成 fallback 结果 | BLOCKED |
| 真机性能 | 不再生成 Mock 设备/随机指标；缺设备代理/SoloX 时 devices/start 均 503，session 保持 pending | BLOCKED |

### 11.4 外部环境执行结果

| 输入 | 网络边界 | 实际结果 | 状态 |
| --- | --- | --- | --- |
| 体育生产镜像 | vpn07；仅 GET/HEAD | 7 个端点 HEAD/TLS 通过；一个浏览器超时，一个节点有效内容不足 | FAIL |
| 体育测试节点 | OpenVPN | 5 个节点浏览器通过；第 6 节点为 503 | FAIL |
| 测试 OpenAPI | OpenVPN | Knife4j v2 可访问；旧 v3 地址 404；实际网关仅 15 paths/17 operations，未证明六服务 | FAIL |
| 测试 API 安全 | OpenVPN | 11 个无参 GET 为 200；无效 Bearer 仍为 200，与声明的安全契约不一致 | FAIL |
| 运营后台测试登录 | OpenVPN | 图形验证码和短信流程接口返回成功，但浏览器未建立 Cookie/storage 会话且仍停留登录页 | FAIL |
| 用户端/后台设计源 | 只读 | 缺当前可复核的原始或脱敏证据包 | BLOCKED |
| ELK、真实 OCR/AI、旧库 | 专项授权 | 未取得必要配置、只读授权或脱敏快照 | BLOCKED |

### 11.5 Gap 处置

- 已关闭：`G56-001`、`G56-002`、`G56-011`、`G56-012`、`G56-013`、`G56-014`、`G56-015`。
- 部分关闭但仍有外部失败：`G56-003`、`G56-005`。
- 保持阻断：`G56-004`、`G56-006`、`G56-007`、`G56-008`、`G56-009`、`G56-010`。
- `G56-016` 已随最终 QA 报告和 `NEEDS WORK` Verdict 对账关闭；它不改变
  业务门禁仍为 `NEEDS WORK` 的结论。

### 11.6 最终机械结论

`NEEDS WORK`。本地 Batch 54/55 遗留、全路由 UI、RBAC、性能真实性与安全、
启动证据、部署安全及供应链已达到可复核交付标准；但全平台生产放行要求
R0/R1 P0/P1 100% 通过。当前仍有测试节点 503、六服务契约缺失、测试 API
鉴权不一致、运营后台无法形成会话，以及真实 AI/OCR、真机性能、ELK 和旧库
快照阻断，因此不得标记为 `READY` 或 `CONDITIONAL`。
