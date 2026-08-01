# Batch 60 体育平台接口测试与 UI 自动化生产验收梳理

## 1. 文档目的与当前结论

本文固定 Batch 60 体育平台接口测试与 UI 自动化的需求来源、数据可信等级、覆盖基线、已执行结果和外部阻塞。执行基线为 `feature/batch-60-sports-platform-production-validation` 分支、提交 `d15ed2197e41bbcecfac733f059160a912373317`、独立本地前端 `http://localhost:5196` 和后端 `http://127.0.0.1:8026`。执行人/日期统一为 `Codex Agent Team / 2026-08-01`。

当前客观结论为 **NEEDS WORK**：R1 本地接口资产链和测试平台自身的 Playwright 执行链已形成真实闭环，但 R2 Test5 当前六服务接口回归、体育用户端/运营后台业务 E2E、授权登录以及 R3 生产只读业务旅程尚未完成。历史记录中的 **892 个接口资产 / 1323 条候选用例**仅是需求和回归范围输入，不能计入本轮通过数。

## 2. 需求、契约与测试资产来源

| 来源 ID | 来源 | 本轮用途 | 可信边界 |
| --- | --- | --- | --- |
| SRC-REQ-USER | `产品需求/蓝湖原型-用户端原型-20260611_180510.json`、对应 Markdown 和用户端更新日志 | 用户端页面、导航和交互覆盖基线 | R1 静态快照，不证明当前线上状态 |
| SRC-REQ-ADMIN | `产品需求/蓝湖原型-运营后台-20260611_180605.json`、对应 Markdown 和后台更新日志 | 运营后台页面、角色和业务管理覆盖基线 | R1 静态快照，不证明当前线上状态 |
| SRC-REQ-CASES | `tests/test-cases/functional/BASELINE-用户端-基线功能.md`、`ADMIN-运营后台-全版本.md`、`P0-HOME-首页推荐.md`、`P0-LIST-预测列表.md`、`P0-DETAIL-UGC详情.md`、`P0-PAY-充值支付.md`、`P0-REFUND-首单退币.md`、`P0-BONUS-充值赠送.md` | 体育业务主流程、异常流和发布优先级 | R1 用例资产；必须在当前目标环境重新执行 |
| SRC-API-OAS | `test-platform/tests/api-testing/specs/cameltv-openapi.yaml` | OpenAPI 预览/导入、资产树、用例生成 | 仅 5 个 path，不是六服务全量契约；其中 POST 路径不得直接用于生产写入 |
| SRC-API-CAPTURE | `test-platform/data/prod_api_capture.json`、`test-platform/tests/api-testing/generated/` | 历史流量解析和生成资产核对 | R1 脱敏历史资料；版本和当前可执行性需复核 |
| SRC-API-T5 | `tests/api-testing/cases/Test5-六服务增改查用例.md` | Test5 六服务正负面场景、鉴权/边界/副作用基线 | 历史执行记录；892/1323 不作本轮通过证据 |
| SRC-UI-SPORTS | `tests/automation/ui/tests/`、`tests/automation/ui/playwright.config.ts` | 首页、列表、详情、充值、退币、赠送和安全契约自动化 | 当前业务 E2E 未在获授权 R2/R3 环境执行；脚本被收集不等于用例通过 |
| SRC-UI-RUNNER | `test-platform-v2/backend/tests/playwright/specs/production-smoke.spec.ts`、`app/services/playwright_executor.py` | 验证测试平台本地 Playwright 任务、结果和产物链 | Run #5 的 `BASE_URL` 指向本地测试平台；脚本名中的 production 不改变实际目标环境 |
| SRC-ENV | `batch-60-real-data-manifest.md` | R1/R2/R3/M 等级、地址、生产禁写和外部依赖 | 所有账号、Token、Cookie、密钥和生产响应必须脱敏 |

## 3. 数据等级与执行边界

| 等级 | 本轮可用数据 | 可执行动作 | 不可推导的结论 |
| --- | --- | --- | --- |
| R1 | 仓库中的体育需求、原型、OpenAPI、历史流量、用例和本地真实平台数据 | 本地导入、生成、调试安全本地接口、建立计划/报告、运行本地浏览器任务 | 不能证明 Test5 或生产体育业务当前可用 |
| R2 | Test5 六服务、用户端、运营后台、当前契约及授权账号 | 获授权后执行可清理的 API/UI 正负面回归；写操作必须唯一命名并核对/清理副作用 | 未连接 VPN、无当前契约或凭据时不得记通过 |
| R3 | 体育生产公开站点及明确安全的公开 API | 只允许 GET/HEAD、TLS、页面加载、控制台、公开内容和只读网络观测 | 禁止支付、解锁、发布、封禁、推流、批量变更、压测或猜测鉴权接口 |
| M | 明确标记的模拟故障或边界数据 | 仅用于不可达、超时、坏格式等故障注入 | 不得替代 R1/R2/R3 正常链路，也不得进入甲方 PASS 快照 |

## 4. 两类 UI 自动化必须分开判定

| 判定对象 | 目标 | 当前真实结果 | 可证明 | 不能证明 |
| --- | --- | --- | --- | --- |
| 测试平台本地 UI Runner smoke | 本地 `http://localhost:5196`；平台任务 `batch60-local-platform-playwright-smoke`；脚本 `production-smoke.spec.ts` | Run #5：5 条，共 **4 pass / 0 fail / 1 skip**，耗时约 5.35 秒 | 本地 Runner 能启动真实 Chromium、访问页面、执行断言并持久化终态；无授权凭据时登录用例被跳过而非假通过 | 体育 Test5/生产登录、赛事、文章、充值、退币、赠送和运营后台业务正确性 |
| 体育业务 UI E2E | `tests/automation/ui/tests/` 指向获授权 R2，或 R3 只读生产目标 | **本轮未完成**；业务脚本和安全脚本已盘点，Test5/生产业务结果不可计入通过 | 已建立待执行覆盖范围和凭据/流量脱敏安全前置 | 不能因脚本可收集、本地 Runner 绿色或历史截图而宣称体育平台 E2E 通过 |

Run #5 中通过的是 `TC-PROD-001` 页面加载、`TC-PROD-003` 可交互元素、`TC-PROD-004` 页面网络探测逻辑和 `TC-PROD-005` 加载时间基线；`TC-PROD-002` 因没有授权账号而 skip。`TC-PROD-004` 当前断言允许零个 API 调用，只能证明脚本完成，不能作为体育核心 API 可达证据，需继续按 `B60-P1-013` 加固。

## 5. 功能点覆盖基线

### 5.1 API 功能点

| 功能点 ID | 主流程 | 备选/异常流 | 正面用例 | 负面用例 | 当前执行覆盖 |
| --- | --- | --- | --- | --- | --- |
| API-FP-01 | 预览并导入合法 OpenAPI | 坏格式、缺关键字段、重复导入 | TC-B60-SPAPI-001 | TC-B60-SPAPI-002 | 已执行 |
| API-FP-02 | 从端点资产生成可追溯用例 | 空资产、重复生成、端点不存在 | TC-B60-SPAPI-003 | TC-B60-SPAPI-006 | 正面已执行；负面未执行 |
| API-FP-03 | 选择环境并执行真实安全请求 | 缺/错参数、未知变量、超时、取消 | TC-B60-SPAPI-004 | TC-B60-SPAPI-007、008 | 本地正面已执行；R2 负面阻塞 |
| API-FP-04 | 同时校验 HTTP、业务码和响应结构 | 数字/字符串类型差异、错误 envelope | TC-B60-SPAPI-004 | TC-B60-SPAPI-005 | 已执行并完成缺陷复测 |
| API-FP-05 | 五入口使用相同目标、变量和生产保护 | 绕过确认、入口环境漂移、重复提交 | TC-B60-SPAPI-009 | TC-B60-SPAPI-010 | 未执行 |
| API-FP-06 | RBAC 与项目资源隔离 | 不存在 ID、跨项目 ID、低权限调用 | TC-B60-SPAPI-011 | TC-B60-SPAPI-012 | 未执行 |
| API-FP-07 | Test5 六服务当前契约回归 | 无/错 Token、边界、状态不允许、回滚 | TC-B60-SPAPI-013 | TC-B60-SPAPI-014 | 阻塞 |
| API-FP-08 | 生产公开接口只读观测 | 写请求、未知端点和敏感响应禁止采集 | TC-B60-SPAPI-015 | TC-B60-SPAPI-016 | 未执行/受限 |

设计层面每个功能点均已映射正面和负面用例；执行层面尚未达到 P0/P1 全通过，因此不能放行。

### 5.2 UI 自动化功能点

| 功能点 ID | 主流程 | 备选/异常流 | 正面用例 | 负面用例 | 当前执行覆盖 |
| --- | --- | --- | --- | --- | --- |
| UI-FP-01 | 创建任务、选择脚本/环境并运行 | 缺脚本、缺依赖、坏配置 | TC-B60-SPUI-001 | TC-B60-SPUI-002、003 | 本地已执行 |
| UI-FP-02 | 任务异步运行至终态 | 超时、取消、重复触发、进程异常 | TC-B60-SPUI-004 | TC-B60-SPUI-005、006 | 服务回归已执行；浏览器取消闭环未执行 |
| UI-FP-03 | 查看统计、stdout/stderr 和截图/Trace/HTML | 制品缺失、越权、下载失败 | TC-B60-SPUI-007 | TC-B60-SPUI-008 | Run #5 统计与 5 个产物浏览器复核通过；跨项目负面未执行 |
| UI-FP-04 | 请求成功显示真实列表/空状态 | 403/5xx 显示错误并可重试 | TC-B60-SPUI-009 | TC-B60-SPUI-010 | 自动化回归已执行 |
| UI-FP-05 | 单次加载可用脚本 | 切页/重渲染造成重复 GET | TC-B60-SPUI-011 | TC-B60-SPUI-012 | 自动化回归已执行 |
| UI-FP-06 | 体育用户端首页/列表/详情只读旅程 | 无业务数据、断网、元素缺失不得静默 skip | TC-B60-SPUI-013 | TC-B60-SPUI-014 | R2 阻塞 |
| UI-FP-07 | 体育授权登录和用户态旅程 | 缺/错凭据、会话过期、账号权限不足 | TC-B60-SPUI-015 | TC-B60-SPUI-016 | R2 阻塞；本地 skip 行为已验证 |
| UI-FP-08 | Test5 支付/退币/赠送可控写闭环 | 重复支付、余额不足、回滚、清理失败 | TC-B60-SPUI-017 | TC-B60-SPUI-018 | R2 阻塞；R3 禁止执行 |
| UI-FP-09 | 流量和截图证据脱敏 | 深层 Token/密码/响应体泄露 | TC-B60-SPUI-019 | TC-B60-SPUI-020 | 安全契约通过；真实 R2 产物待复核 |
| UI-FP-10 | 供应链、三视口、键盘和网络门禁 | 高危依赖、移动不可操作、重复 GET | TC-B60-SPUI-021 | TC-B60-SPUI-022 | 高危依赖未关闭；全量门禁未完成 |
| UI-FP-11 | 生产目标标识、范围预览、专门权限和二次确认 | 无权限、无确认、跨项目环境不得创建 run | TC-B60-SPUI-023 | TC-B60-SPUI-023 | UI 自动化直触发已执行；发布包回归等入口仍由 B60-P0-004 跟踪 |

## 6. API 用例与实际结果

| 用例 ID | 需求来源 | 优先级/类型 | 前置条件 | 明确输入与步骤 | 可观察预期（入参/业务/返回/副作用） | 实际结果 | 状态 | 证据 | 缺陷 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TC-B60-SPAPI-001 | SRC-API-OAS / API-FP-01 | P0 正面 | 独立本地项目；使用 R1 OAS | 在 `/apitest` 预览并确认导入 `cameltv-openapi.yaml` | 入参：合法 OAS 3.0；业务：按 service/module 建树；返回：导入成功且 5 path 可回读；副作用：同项目新增 5 个资产 | 5 个体育接口资产持久化并回读 | 通过 | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-API-001-01-openapi-import-PASS.png` | 无 |
| TC-B60-SPAPI-002 | SRC-API-OAS / API-FP-01 | P0 负面 | 本地接口页可用 | 提交坏 YAML/非 OpenAPI 内容并执行预览 | 入参：非法契约；业务：拒绝进入确认导入；返回：明确解析错误；副作用：资产数不增加 | 坏 OAS 被预览阶段拒绝，未形成导入 | 通过 | `batch-60-full-platform-execution-matrix.md` 的 FP-API-001 执行记录 | 无 |
| TC-B60-SPAPI-003 | SRC-API-OAS / API-FP-02 | P0 正面 | 已有上述 5 个资产 | 对导入端点执行生成并按端点分组回读 | 入参：5 个有效 endpoint ID；业务：按方法/参数生成正负面候选；返回：生成数与列表一致；副作用：同项目新增 7 条用例 | 5 个资产生成 7 条用例并可回读 | 通过 | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-API-001-02-generated-cases-PASS.png` | 无 |
| TC-B60-SPAPI-004 | SRC-UI-RUNNER / API-FP-03、04 | P0 正面 | 本地后端运行；选择本地环境 | 在快速调试中请求真实本地 `GET /health`，增加状态码等于 200 断言 | 入参：GET、安全本地 URL；业务：执行所选环境；返回：HTTP 200 且断言通过；副作用：保存真实执行结果，不产生体育业务写入 | HTTP 200，状态码断言通过并留存页面结果 | 通过 | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-API-001-03-local-health-debug-PASS.png` | B60-P1-028（已关闭） |
| TC-B60-SPAPI-005 | API-FP-04 | P1 负面/兼容 | 后端断言服务可测 | 以数值实际值 `200` 对比 UI 提交的字符串期望值 `"200"`；同时回归字符串和布尔语义 | 入参：可安全转数值的异类型值；业务：只在一侧数值、一侧数值字符串时数值比较；返回：等值通过；副作用：不改写原始响应 | 定向后端 3 条回归与真实 `/health` 调试通过 | 通过 | `backend/tests/test_apitest_generation.py`、同上 PC 证据 | B60-P1-028（已关闭） |
| TC-B60-SPAPI-006 | API-FP-02 | P1 负面 | 空项目或不存在 endpoint ID | 对空资产生成，或以不存在/跨项目 ID 触发生成 | 入参：空/非法/跨项目 ID；业务：拒绝且不泄露其他项目资产；返回：受控 4xx；副作用：用例数不变、无审计假成功 | 本轮未完成浏览器/API/DB 联合复核 | 未执行 | — | 待执行 |
| TC-B60-SPAPI-007 | SRC-API-OAS、SRC-API-T5 / API-FP-03 | P0 负面 | 当前 R2 契约和安全查询接口 | 对 `home_match` 缺少/错格式 `day`，以及环境变量缺失执行请求 | 入参：缺失、空、错格式和未知变量；业务：请求不得误发到默认/生产目标；返回：明确参数/变量错误，不得 5xx；副作用：无写入 | 无当前 Test5 连接和契约，未执行 | 阻塞 | `batch-60-real-data-manifest.md` 第 9 节 | B60-BLK-001 |
| TC-B60-SPAPI-008 | SRC-API-T5 / API-FP-03 | P0 负面/鉴权 | Test5 最小权限账号 | 对鉴权查询分别不发 Token、发送无效 Token、发送低权限 Token | 入参：三类鉴权状态；业务：拒绝私有数据与越权；返回：明确 401/403 或契约业务码；副作用：DB/任务/审计无业务写入 | 历史文档有结果，但本轮没有当前环境复测，不能记通过 | 阻塞 | `tests/api-testing/cases/Test5-六服务增改查用例.md`（仅历史输入） | B60-BLK-001 |
| TC-B60-SPAPI-009 | API-FP-05 | P0 正面 | 同一 GET 用例、同一 R2 环境和数据集 | 从快速调试、资产、单条、分组、批量五入口执行同一安全 GET | 五入口请求目标、变量、生产标识和结果 schema 相同；返回/快照可比较；无额外请求 | 尚未执行 | 未执行 | — | B60-P1-019 |
| TC-B60-SPAPI-010 | API-FP-05 | P0 负面/生产保护 | 登记为 production 的环境 | 五入口尝试未勾选 `confirm_prod` 执行，并连续双击执行 | 服务端拒绝；页面显示目标与安全范围；零网络外呼、零任务和零业务副作用 | 统一保护尚未完成，不能放行 | 失败 | `batch-60-issue-register.md` | B60-P0-004、B60-P1-019 |
| TC-B60-SPAPI-011 | API-FP-06 | P0 正面/RBAC | 项目 A 管理员和项目 A 资产 | 列表、详情、生成和安全执行同项目资源 | HTTP/业务成功；结果、计数、审计均属于项目 A | 本轮专项未形成完整证据链 | 未执行 | — | 待执行 |
| TC-B60-SPAPI-012 | API-FP-06 | P0 负面/RBAC | 项目 A 用户、项目 B 资产及不存在 ID | 覆盖列表、详情、生成、执行、结果、快照和子资源 | 403/404 且不泄露名称、数量或结构；无 DB/任务副作用 | 本轮专项未形成完整证据链 | 未执行 | — | 待执行 |
| TC-B60-SPAPI-013 | SRC-API-T5 / API-FP-07 | P0 正面/R2 | OpenVPN 获授权；六份当前契约；最小权限账号；清理规则 | 先安全查询，再对获准实体唯一命名新增→查询 ID→修改→回读；Payment 只读 | 参数符合当前契约；业务码/核心字段正确；写接口 DB/审计一致并按规则清理或登记保留 | 892/1323 和历史增改查只作输入，本轮当前回归未执行 | 阻塞 | `batch-60-real-data-manifest.md`、SRC-API-T5 | B60-BLK-001 |
| TC-B60-SPAPI-014 | SRC-API-T5 / API-FP-07 | P0/P1 负面/R2 | 同上 | 执行缺参、边界、无效 ID、错误状态、重复/并发、超时重试和权限隔离 | 错误语义受控；不得 5xx、脏写、重复数据或跨服务/项目泄露；失败全部回滚 | 当前环境未执行 | 阻塞 | SRC-API-T5 的待执行负向章节 | B60-BLK-001 |
| TC-B60-SPAPI-015 | SRC-API-OAS、SRC-ENV / API-FP-08 | P0 正面/R3 | 明确公开且安全的 GET/HEAD 端点 | 只读探活，记录状态/TLS/时延和最小必要响应结构 | 不猜测鉴权；HTTP 与业务 envelope 分开校验；证据脱敏；无写副作用 | 尚未确认本轮允许的公开 API 清单 | 未执行 | — | 待确认公开端点 |
| TC-B60-SPAPI-016 | SRC-ENV / API-FP-08 | P0 负面/安全 | 生产环境 | 尝试配置 POST/PUT/PATCH/DELETE、支付、发布、封禁、推流或批量任务 | 客户端和服务端均阻止；不产生生产请求、任务或证据泄密 | 统一生产保护仍有缺口 | 失败 | `batch-60-issue-register.md` | B60-P0-004 |

## 7. UI 自动化用例与实际结果

| 用例 ID | 需求来源 | 优先级/类型 | 前置条件 | 明确输入与步骤 | 可观察预期 | 实际结果 | 状态 | 证据 | 缺陷 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TC-B60-SPUI-001 | SRC-UI-RUNNER / UI-FP-01 | P0 正面/本地 | 本地前后端、Chromium 和 runner 依赖可用；Environment ID 3、Job ID 1 | 从平台运行 `specs/production-smoke.spec.ts`，轮询至终态并回读统计 | 真实子进程执行；终态 `done`；总数=pass+fail+skip；结果持久化；PC 页显示同一运行 | Run #5：5 total、4 pass、0 fail、1 skip，约 5.35 秒 | 通过（仅平台本地 smoke） | `evidence/batch-60-sports-platform-validation/pc-usage-snapshots/FP-UI-001-01-local-playwright-run-PASS.png` | 无 |
| TC-B60-SPUI-002 | UI-FP-01 | P0 负面/依赖 | 移除或模拟缺少本地 `@playwright/test` | 启动任务并读取健康/终态 | 启动前 fail-closed；提示执行 `npm ci`；不得因为全局 CLI 而假健康；run 进入可解释失败终态 | 历史 Run #1 暴露缺依赖；本地锁定依赖检查已补回归 | 通过（缺陷复测） | `backend/tests/test_playwright_executor.py`、`app/services/playwright_executor.py` | B60-P1-038（已关闭） |
| TC-B60-SPUI-003 | UI-FP-01 | P1 负面/脚本 | 任务引用不存在 spec | 运行空路径或不存在路径 | 返回可用 spec 列表和明确错误；不启动浏览器；终态失败且统计为 0 | 服务层已有验证，完整浏览器闭环未单独留证 | 未执行 | `app/services/playwright_executor.py` | 待执行 |
| TC-B60-SPUI-004 | UI-FP-02 | P0 正面/进程 | Windows 本地 runner，spec 产生中文和较多 JSON reporter 输出 | 执行至子进程结束并解析结果 | UTF-8 安全解码；stdout 在等待退出前持续排空；无管道死锁；结果统计准确 | 修复后 Run #5 正常结束；完整 executor 文件 24 条通过 | 通过 | `backend/tests/test_playwright_executor.py`、Run #5 PC 证据 | B60-P1-039、B60-P1-040（已关闭） |
| TC-B60-SPUI-005 | UI-FP-02 | P0 负面/取消 | 长运行 spec | 运行中点击取消并重复点击取消 | 仅一次取消生效；进程树终止；终态 cancelled；不发假完成通知；无孤儿进程 | 服务定向取消测试已通过；真实浏览器按钮/DB/审计闭环未完成 | 未执行 | `backend/tests/test_playwright_executor.py`（局部证据） | 待执行 |
| TC-B60-SPUI-006 | UI-FP-02 | P0 负面/超时 | 可控超时 spec | 设置短 timeout 后运行 | 到时终止进程树；终态 timeout/failed 语义明确；保留 stdout/stderr；可再次执行 | 服务定向超时回归已通过；真实浏览器复测未完成 | 未执行 | `backend/tests/test_playwright_executor.py`（局部证据） | 待执行 |
| TC-B60-SPUI-007 | UI-FP-03 | P0 正面/产物 | 成功且生成截图与报告 JSON 的运行 | 打开 Run #5 详情，核对统计并逐项加载/下载产物，确认首个可用输出自动激活 | 页面统计与 API 一致；受保护资源通过带项目头的鉴权 Blob 获取；对象 URL 释放；stdout→stderr→无输出按可用性选择 | 5/4/0/1 正确；5 个产物请求均 200，3 张 PNG 均完整解码为 1280px；默认 stdout 可见真实中文执行输出；报告/WebSocket 的代理与物理分离 URL 契约已回归 | 通过 | `frontend/src/pages/uitest/__tests__/UiRunDetail.test.tsx`、`frontend/src/api/baseUrl.test.ts`、`frontend/src/api/report.test.ts`、`frontend/src/hooks/__tests__/usePerfWebSocket.test.tsx`、`FP-UI-001-02-run-detail-artifacts-PASS.png`、`FP-UI-001-03-default-stdout-PASS.png` | B60-P1-035（已关闭）；B60-P1-007（已关闭） |
| TC-B60-SPUI-008 | UI-FP-03 | P0 负面/RBAC | 低权限项目 A 用户、项目 B 产物和过期会话 | 直接请求图片、Trace、HTML、stdout 及不存在 artifact ID | 403/404；不泄露文件名、大小、URL 和内容；不生成匿名可访问链接 | 尚未完成动态跨项目验证 | 未执行 | — | 待执行 |
| TC-B60-SPUI-009 | UI-FP-04 | P1 正面/空状态 | 授权项目确实无任务 | 打开 `/uitest` 并等待唯一有效 GET 结束 | HTTP 200 空数组时显示真实 EmptyState 和新建入口 | 组件回归覆盖真实空数组分支 | 通过（组件回归） | `frontend/src/pages/uitest/__tests__/UiTestPage.test.tsx` | 无 |
| TC-B60-SPUI-010 | UI-FP-04 | P0 负面/错误 | 模拟 403/5xx/断网 | 打开列表、点击重试 | 显示 ErrorState 和错误语义；不得伪装成“暂无任务”；重试只发一次请求 | 页面错误态组件回归通过 | 通过（组件回归） | `frontend/src/pages/uitest/__tests__/UiTestPage.test.tsx` | B60-P1-035（已关闭） |
| TC-B60-SPUI-011 | UI-FP-05 | P1 正面/网络 | 脚本接口正常 | 打开页面和 ScriptSelector | 只由选择器加载一次脚本；正常回显可用 spec | 去除顶层重复加载，组件测试通过 | 通过（组件回归） | `frontend/src/pages/uitest/__tests__/UiTestPage.test.tsx` | 无 |
| TC-B60-SPUI-012 | UI-FP-05 | P1 负面/网络 | React 重渲染和 Tab 切换 | 多次切换页面状态并统计 `GET /ui-tests/scripts` | 每次有效加载周期仅 1 次 GET；旧请求可清理；不得重复并发 | 当前定向测试覆盖初始重复请求修复；全页面网络矩阵待完成 | 未执行 | `frontend/src/pages/uitest/__tests__/UiTestPage.test.tsx`（局部证据） | B60-P1-035（初始重复已关闭） |
| TC-B60-SPUI-013 | SRC-REQ-CASES、SRC-UI-SPORTS / UI-FP-06 | P0 正面/R2 | Test5 VPN、当前页面和稳定业务数据 | 执行首页推荐→预测列表→文章详情只读旅程，核对 API 与可见业务字段 | 页面/接口同源；排序、筛选、跳转和脱敏内容符合需求；无控制台错误；1440×900 留证 | 本轮未进入 Test5；脚本存在不等于通过 | 阻塞 | `tests/automation/ui/tests/home/`、`list/`、`detail/` | B60-BLK-001、B60-P1-012 |
| TC-B60-SPUI-014 | UI-FP-06 | P0 负面/R2 | Test5 可构造无数据、断网和权限不足 | 执行空列表、API 失败、元素缺失和数据状态不符场景 | 空/错误/无权限有明确语义；关键 P0 缺数据不得静默 skip；接口和页面不假绿 | 现有业务脚本仍有多处无数据直接 skip | 失败 | `tests/automation/ui/tests/` | B60-P1-012 |
| TC-B60-SPUI-015 | SRC-UI-SPORTS / UI-FP-07 | P0 正面/R2 | 授权测试账号；凭据仅本地确定性 locator 使用 | 登录 Test5，验证会话、用户菜单、刷新续期和登出 | 登录后状态可观测；Cookie/Token 不进入 AI 指令、截图或报告；过期后正确恢复 | Run #5 的登录用例因无授权凭据 skip；体育登录未执行 | 阻塞 | Run #5 统计、`tests/automation/ui/utils/auth.ts` | B60-BLK-001、B60-P0-001 |
| TC-B60-SPUI-016 | UI-FP-07 | P0 负面/安全 | 无凭据、错凭据、过期会话 | 分别启动登录用例 | 无凭据必须明确阻塞/skip；错凭据失败且无会话；不得使用默认账号或把凭据发给 Midscene | 无凭据 fail-closed 和本地 locator 安全契约通过；真实错凭据路径未执行 | 未执行 | `tests/automation/ui/tests/security/security-utils.spec.ts`、Run #5 skip | B60-P0-001（已修复待 R2 复测） |
| TC-B60-SPUI-017 | SRC-REQ-CASES、SRC-UI-SPORTS / UI-FP-08 | P0 正面/R2 写路径 | 获授权 Test5 账号、测试支付通道、唯一数据和清理/回滚规则 | 在 Test5 执行充值→余额/订单回读；首单 Loss 退币；活动 Bonus 核对 | UI、API、订单/余额、审计和通知一致；重复执行幂等；测试数据可恢复 | 无授权条件，未执行；生产环境明确禁止 | 阻塞 | `tests/automation/ui/tests/pay/`、`refund/`、`bonus/` | B60-BLK-001 |
| TC-B60-SPUI-018 | UI-FP-08 | P0 负面/事务 | 同上 | 余额不足、重复点击、支付失败、超时重试、非活动套餐、非首单和清理失败 | 不重复扣款/发币；失败全部回滚；错误语义明确；审计可追溯 | 未执行；不得在 R3 注入 | 阻塞 | SRC-REQ-CASES | B60-BLK-001 |
| TC-B60-SPUI-019 | UI-FP-09 | P0 正面/安全 | 自动化捕获开启 | 运行安全请求并生成网络证据 | URL/query/header/body/response 递归脱敏；不同会话隔离；报告仍可定位用例 | 红队契约已验证递归脱敏和会话清理 | 通过（安全契约） | `tests/automation/ui/tests/security/security-utils.spec.ts` | B60-P0-002（已修复待 R2 复测） |
| TC-B60-SPUI-020 | UI-FP-09 | P0 负面/安全 | 构造深层 Token、密码、Cookie、未知原始 body | 捕获请求/响应并扫描输出 | 敏感值均不可出现；未知不可安全解析的 body 必须 fail-closed；不落盘真实凭据 | 安全红队测试通过；真实 Test5 生成物仍需二次扫描 | 未执行 | `tests/automation/ui/tests/security/security-utils.spec.ts`（局部证据） | B60-P0-002 |
| TC-B60-SPUI-021 | UI-FP-10 | P0/P1 正面/门禁 | 本地依赖完整 | 运行类型检查、业务/安全 Playwright、1440×900/768×1024/390×844、键盘、console/network 检查 | 所有 P0/P1 通过；关键 GET 单次；三视口可操作；无严重 a11y 和高危依赖 | 平台前端 269/269、typecheck/build 和体育安全红队 6/6 通过；移动缺陷表格键盘滚动与主题定位器已关闭，但全模块三视口/a11y/network 尚未逐功能完成，且供应链仍有 high | 失败 | 本 QA 报告与 `batch-60-issue-register.md` | B60-P1-011、B60-P1-023 |
| TC-B60-SPUI-022 | UI-FP-10 | P0 负面/供应链 | 当前 `tests/automation/ui` lockfile | 执行生产依赖漏洞审计并核对许可证/升级影响 | 无未接受 high/critical；升级后业务和安全套件无新增失败 | 已记录 7 high、9 moderate、4 low，主要来自 Midscene 0.20.1 传递依赖 | 失败 | `tests/automation/ui/package-lock.json`、`batch-60-issue-register.md` | B60-P1-023 |
| TC-B60-SPUI-023 | UI-FP-11 | P0 正负面/生产保护 | 临时生产标记环境、生产只读 smoke 任务；不实际访问生产 | 列表核对 PROD/环境；无 body 直接触发，再打开 UI 执行范围预览但取消 | 无确认返回 400 且 run 数保持 0；必须同时具备 `uitest:trigger_prod` 和 `confirm_prod=true`；确认页显示任务、环境、地址、脚本；环境须属于当前项目 | 后端 5 条门禁测试、前端 2 文件 19 条相关测试通过；可见 Chrome 400/零 run/范围预览通过，临时任务和 `.invalid` 环境已删除 | 通过（UI 自动化直触发） | `FP-UI-001-04-production-guard-PASS.png`、`backend/tests/test_ui_test_production_guard.py` | B60-P0-004（部分关闭；其余入口仍开放） |

## 8. 当前执行汇总

以下统计只覆盖本文件逐条列出的验收用例，不把历史用例数量、脚本收集数或“局部证据”自动算成通过。

| 领域 | 通过 | 失败 | 阻塞 | 未执行 | 合计 |
| --- | ---: | ---: | ---: | ---: | ---: |
| API | 5 | 2 | 4 | 5 | 16 |
| UI 自动化 | 9 | 3 | 4 | 7 | 23 |
| 合计 | 14 | 5 | 8 | 12 | 39 |

说明：UI Run #5 自身的 4/0/1 是一次本地 Runner 任务内部统计，不能与上表的生产验收用例数量相加。上表将组件/安全/服务级回归仅在其明确证明的功能点内记为通过；需要真实浏览器、R2/R3、RBAC、DB/审计或全量产物的用例仍保持未执行或阻塞。

## 9. 阻塞项与解除条件

| 阻塞范围 | 缺失条件 | 当前已完成 | 解除条件 | 责任人 | 预计时间 | 复测时限 |
| --- | --- | --- | --- | --- | --- | --- |
| Test5 六服务 API | OpenVPN 未启用；缺六份当前契约、有效最小权限 Token 和清理规则 | R1 5-path OAS 导入、7 条本地用例、历史 Test5 场景盘点 | 用户明确授权 VPN 切换；提供当前契约、账号、允许写范围和清理责任 | 项目/运维负责人 | 待确认 | 条件齐备后 1 个工作日内先跑 P0 只读和鉴权负面 |
| 体育用户端/后台 E2E | Test5 当前页面、授权账号、稳定业务数据和运营后台脚本不足 | 本地 Runner 成功；用户端首页/列表/详情/支付等脚本已盘点 | 提供 R2 会话与数据；补后台 P0 旅程；所有关键 skip 改为 fixture 或明确 BLOCKED | 产品/项目/QA | 待确认 | 条件齐备后 1–2 个工作日 |
| 支付/退币/赠送 | 无测试支付通道、余额/订单回滚与清理授权 | R1 用例和脚本存在 | 明确 Test5 可写账号、金额上限、幂等号、回滚/清理机制和审计查询 | 产品/财务/后端/QA | 待确认 | 条件齐备后单独窗口执行；生产永不执行 |
| R3 生产只读 | 尚未固定允许站点、公开 API 白名单和证据保留范围 | R3 地址已登记，生产禁写规则已固定 | 书面确认 GET/HEAD URL 清单、时间窗、频率和脱敏规则 | 项目/运维负责人 | 待确认 | 授权后 1 个工作日 |
| UI 自动化供应链 | Midscene 0.20.1 传递依赖存在 high 漏洞 | 风险和 lockfile 已固定 | 评估升级到兼容版本；重跑安全契约、25 条收集、R2 只读旅程和依赖审计 | 前端/QA | 待确认 | 修复合入后立即复测 |

## 10. 后续执行优先级

1. **P0：关闭假绿和生产误触发风险。** 完成 API 五入口统一环境/变量/`confirm_prod`，加固 `TC-PROD-004` 为“存在明确核心 API 且状态/业务码正确”，并保证关键业务无数据时报告 BLOCKED 而不是静默 skip。
2. **P0：取得 R2 最小授权后先只读。** 固定六服务当前 OpenAPI SHA/导出时间，先跑健康、查询、缺/错 Token、权限隔离和参数边界；输出脱敏请求/响应及 DB/审计无副作用证据。
3. **P0：完成本地平台 UI Runner 闭环。** 在浏览器中复测取消、超时、重复触发、stdout/stderr、截图/Trace/HTML 和项目 A/B 产物隔离；每个成功功能保存 1440×900 快照。
4. **P0：执行体育只读业务 E2E。** Test5 优先覆盖首页推荐、预测列表、详情和授权登录；生产只执行获准 GET/HEAD，不点击可能产生关注、解锁、支付或写入的控件。
5. **P0：单独审批体育写旅程。** 充值、退币和 Bonus 仅在具备测试支付通道、金额上限、唯一幂等号、回滚/清理和审计能力后执行。
6. **P1：补运营后台与三视口/a11y。** 建立后台登录、内容/赛事/配置的 P0 主链及负面权限；在 1440×900、768×1024、390×844 下核对键盘、焦点、控制台和每个 GET 的有效请求次数。
7. **P1：关闭供应链风险并跑全量门禁。** 升级或风险处置 Midscene 依赖，执行体育自动化安全套件、业务套件、类型检查、依赖审计和测试平台前后端全量回归。

## 11. 发布判定规则

只有以下条件同时满足，接口测试和 UI 自动化域才可从 `NEEDS WORK` 提升为候选放行：

- 本文件全部 P0/P1 用例通过，不存在失败、阻塞或未执行；
- Test5 当前契约、授权账号和真实业务数据的结果与 R1 资产逐项可追溯；
- API 入参、业务、返回三类校验齐全，所有写路径同时具备 DB、审计、任务和回滚/清理证据；
- 体育业务 E2E 与测试平台本地 Runner 的结果分开统计、分开索引；
- 生产只执行书面批准的 GET/HEAD，未产生支付、发布、封禁、推流或其他写副作用；
- 每个声明通过的 PC 功能都有已视觉复核的 1440×900 成功状态快照，且全部证据完成凭据和个人信息脱敏；
- 自动化供应链无未接受的 high/critical 风险，最终全量门禁无新增失败。
