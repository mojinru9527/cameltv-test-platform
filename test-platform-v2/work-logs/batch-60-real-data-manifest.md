# Batch 60 体育平台真实数据与环境清单

## 1. 基线

| 项目 | 值 |
| --- | --- |
| 分支 | `feature/batch-60-sports-platform-production-validation` |
| 基线提交 | `d15ed2197e41bbcecfac733f059160a912373317` |
| 本地前端 | `http://localhost:5196` |
| 本地后端 | `http://127.0.0.1:8026` |
| 本地数据库 | 独立 SQLite `platform-local.db`（忽略跟踪） |
| Agent 工作流 | `agent-team` / `codex` |
| 数据原则 | 优先真实体育资料；只有条件缺失才允许 mock，并记录原因、影响和解除条件 |

## 2. 数据等级

| 等级 | 定义 | 允许用途 | 限制 |
| --- | --- | --- | --- |
| R1 | 仓库中可追溯、已脱敏的体育需求、原型、历史流量、测试用例和静态契约 | 本地导入、解析、检索、追溯、用例/计划/报告/缺陷闭环 | 不能证明当前线上状态 |
| R2 | Test5/非生产体育站点、后台、实时接口和授权账号 | 可控读写、API/UI 回归、外部集成 | 需要 OpenVPN、有效账号/Token、当前契约和清理权限 |
| R3 | 体育生产站点和生产 API 的只读观测 | GET/HEAD、TLS、页面加载、控制台与公开内容检查 | 禁止支付、发布、封禁、压测、批量写入或其他破坏性操作 |
| M | 明确标识的模拟数据 | 仅故障注入、不可达依赖或边界验证 | 必须写明为何 R1/R2/R3 均不可用；不得冒充真实通过 |

## 3. R1 产品、原型与需求源

| 资产 | 用途 | 可信边界 |
| --- | --- | --- |
| `产品需求/蓝湖原型-用户端原型-20260611_180510.json` | 用户端 98 页原型、页面 URL、发布包/知识/需求导入 | 版本化静态快照 |
| `产品需求/蓝湖原型-用户端原型-20260611_180510.md` | 人工可读用户端页面说明 | 静态快照 |
| `产品需求/蓝湖原型-运营后台-20260611_180605.json` | 运营后台 72 页原型、页面 URL | 静态快照 |
| `产品需求/蓝湖原型-运营后台-20260611_180605.md` | 人工可读后台说明 | 静态快照 |
| `产品需求/更新日志-用户端原型-结构化.md` | 用户端版本差异、回归范围 | 结构化历史记录 |
| `产品需求/更新日志-运营后台-结构化.md` | 后台版本差异、回归范围 | 结构化历史记录 |
| `产品需求/产品需求-天声猜猜猜-20260617_145800.md` | 真实体育业务需求导入样本 | 静态需求文档 |
| `tests/requirements/documents/用户端原型-需求分析.md` | 用户端脱敏需求导入、功能拆分 | R1，不代表实时线上 |
| `tests/requirements/documents/运营后台-需求分析.md` | 后台脱敏需求导入、功能拆分 | R1，不代表实时线上 |
| `tests/requirements/documents/13.0-baseline.md` | 基线功能追溯 | 历史版本 |
| `tests/requirements/documents/14.0-features.md` | 版本功能追溯 | 历史版本 |
| `tests/requirements/traceability-matrix/matrix-v14.csv` | 需求—用例关联导入和核对 | 历史矩阵 |

## 4. R1 体育测试用例

| 资产 | 已知规模 | Batch 60 用途 |
| --- | ---: | --- |
| `tests/test-cases/functional/BASELINE-用户端-基线功能.md` | 290 条 | 用户端基线用例导入、检索、批量、计划和追溯 |
| `tests/test-cases/functional/ADMIN-运营后台-全版本.md` | 359 条 | 后台用例导入、跨模块和权限验证 |
| `tests/test-cases/体育平台最新版本-测试用例.md` | 179 条 | 当前体育业务用例样本 |
| `tests/test-cases/functional/P0-HOME-首页推荐.md` | P0 集合 | 首页推荐主链 |
| `tests/test-cases/functional/P0-LIST-预测列表.md` | P0 集合 | 列表、筛选、分页 |
| `tests/test-cases/functional/P0-DETAIL-UGC详情.md` | P0 集合 | 详情、互动和状态 |
| `tests/test-cases/functional/P0-PAY-充值支付.md` | P0 集合 | 仅 Test5 授权环境执行写路径；生产禁写 |
| `tests/test-cases/functional/P0-REFUND-首单退币.md` | P0 集合 | 仅 Test5 授权环境执行写路径；生产禁写 |
| `tests/test-cases/functional/P0-BONUS-充值赠送.md` | P0 集合 | 仅 Test5 授权环境执行写路径；生产禁写 |

## 5. R1 接口与历史流量

| 资产 | 用途 | 限制 |
| --- | --- | --- |
| `test-platform/tests/api-testing/specs/cameltv-openapi.yaml` | 验证 OpenAPI 预览/确认导入、端点树、用例生成 | 只有 5 paths，不代表六服务全量 |
| `test-platform/data/prod_api_capture.json` | 脱敏历史请求导入与解析 | 只有 5 条，不代表当前生产契约 |
| `test-platform/tests/api-testing/generated/` | Auth/Client/Sports/Ads 生成资产 | 需验证版本和可执行性 |
| `tests/api-testing/cases/Test5-六服务增改查用例.md` | Test5 历史正负面场景 | 必须在当前 Test5 复测后才能形成 R2 结论 |

历史日志记载 Test5 曾导入 892 个接口资产并生成 1323 条候选用例；仓库没有可复现的 collection、environment、report 或本地数据库资产，因此该数字只作历史输入，不作本轮通过证据。

## 6. Batch 60 本地持久化验收数据

| 实体 | 本地标识/结果 | 真实来源与用途 | 可信边界 |
| --- | --- | --- | --- |
| 接口资产 | R1 OpenAPI 5 paths → 5 资产 → 7 用例 | `cameltv-openapi.yaml`；资产树、用例生成、计划与追溯 | R1 静态契约，不等于 Test5/生产当前接口通过 |
| 接口计划 | ID 1，`Batch 60 CamelTv R1 接口回归计划` | 关联上述 7 条用例，产生真实执行/缺陷/报告闭环 | 本地 SQLite 持久化 |
| 定时任务 | ID 1，`batch60-R1体育接口周回归（禁用）`，Cron `0 6 * * 1` | 绑定接口计划；验收期间保持禁用，避免非预期执行 | 已验证创建、回读和测试员只读；未验证启用后历史 |
| 发布版本链 | ID 1 `batch60-R1体育原型冻结版` → ID 2 `batch60-生产验收基线` | 仓库用户端/运营后台原型快照与固定代码基线 | 已验证版本链与 RBAC；差异/全景/标注尚未完成 |
| 音视频任务 | ID 1，状态 `done`，HTTP，6 项 ffprobe 指标 | `tests/音视频项目测试/materials/av_sync_test.mp4` 经本地 Range HTTP 服务真实探测 | 真实文件级探测；不能替代实时 HLS/FLV/WebRTC/DASH |
| UI 自动化环境 | ID 3，`batch60-local-platform-ui`，`http://localhost:5196` | 隔离测试平台真实页面 | 本地环境，不是体育生产站点 |
| UI 自动化任务 | Job ID 1，`batch60-local-platform-playwright-smoke` | 仓库 `specs/production-smoke.spec.ts`，Chrome/Chromium 本地执行 | 证明测试平台 Runner 闭环，不代表体育业务全量 E2E |
| UI 自动化最终执行 | Run ID 5：5 total / 4 pass / 0 fail / 1 skip / 5.35s；5 个产物 | 三张真实截图经项目头+Cookie 鉴权 Blob 加载；1 条生产授权登录明确跳过 | 跳过不是通过；早期 Run 1–4 失败记录保留作修复证据 |
| 知识前置状态 | AI 关闭、知识源/片段/实体为 0、Wiki 未启用、两条发布包均为 draft | 验证 Skills、图谱提取和 Wiki 同步在任务/写入前明确 fail-closed | 负面 PASS，不代表真实摄取、检索、编译或 AI 执行通过 |
| UI 生产保护临时数据 | `.invalid` production 标记环境 + 只读 smoke 任务 | 验证 PROD 标识、范围预览、无确认 HTTP 400 和 run 数保持 0 | M 边界数据；未访问任何生产地址，任务和环境已在 `finally` 删除 |

以上记录均位于本任务独立 SQLite 和本地 storage，未写入生产体育系统；没有用 Mock 结果替代成功执行。

## 7. R2 已登记地址

| 类型 | 地址 | 当前状态 |
| --- | --- | --- |
| Test5 用户端 | `https://camelive-g3-test5.elelive.cn/` | 需要 OpenVPN 与授权会话 |
| Test5 站点 | `https://camel-to-test5.elelive.cn/id` | 需要 OpenVPN |
| Test5 站点 | `https://camelive-g4-test5.elelive.cn/id` | 需要 OpenVPN |
| Test5 站点 | `https://camelive-g2-test5.elelive.cn/` | 需要 OpenVPN |
| Test5 站点 | `https://camel-g5-test5.elelive.cn/` | 需要 OpenVPN |
| Test5 站点 | `https://camel-g6-test5.elelive.cn/` | 历史有 503，需复测 |
| Test5 运营后台 | `https://camel-admintest5.elelive.cn/login` | 需要 OpenVPN 与授权账号 |
| Test5 Knife4j | `http://camel-api-gateway05.svc.elelive.cn/camel-service/doc.html#/home` | 内网入口 |
| Test5 OpenAPI | `http://camel-api-gateway05.svc.elelive.cn/v3/api-docs` | 历史入口，需核对当前契约 |

VPN 约束：仓库手册禁止 vpn07 与 OpenVPN 同时启用。当前 vpn07/Meta Tunnel 为 Up，OpenVPN TAP 为 Disconnected；切换网络适配器属于单独授权操作，未获得明确授权前不执行。

## 8. R3 已登记地址

| 地址 | 允许动作 |
| --- | --- |
| `https://www.camel1.tv/` | 公开页面 GET/HEAD、TLS、控制台、可见内容 |
| `https://www.camel1.to/` | 公开页面 GET/HEAD、TLS、控制台、可见内容 |
| `https://www.camel2.live/home` | 公开页面 GET/HEAD、TLS、控制台、可见内容 |
| `https://www.camelscore.live/` | 公开页面 GET/HEAD、TLS、控制台、可见内容 |
| `https://www.goals365.live/en` | 公开页面 GET/HEAD、TLS、控制台、可见内容 |
| `https://www.camellofutbol.com/es` | 公开页面 GET/HEAD、TLS、控制台、可见内容 |
| `https://api.cameltv.live` | 只读、公开、明确安全的探活/契约请求；禁止猜测鉴权或写接口 |

所有外部证据必须脱敏；不保存真实 Cookie、Token、账号、个人信息或完整生产响应体。

## 9. 当前外部能力阻塞

| 能力 | 状态 | 缺失条件 | 解除条件 |
| --- | --- | --- | --- |
| DeepSeek 真实生成/反向评审 | BLOCKED | 当前本地 profile `AI_ENABLED=false`，无授权 API Key | 提供独立非生产 Key、额度和允许的数据范围 |
| 蓝湖在线采集/OCR | BLOCKED | 无有效蓝湖登录态和 OCR 运行条件 | 提供授权 Cookie/账号及可处理页面范围 |
| ELK/Kibana trace | BLOCKED | 无 ELK 地址和授权 | 提供非生产 ELK URL、索引和只读权限 |
| SMTP/Webhook 真发送 | BLOCKED | 无收件箱/测试群机器人 | 提供非生产接收端和清理规则 |
| Jira/TAPD 真同步 | BLOCKED | 无授权测试项目/Token | 提供非生产项目与最小权限 Token |
| Test5 六服务全量 | BLOCKED | OpenVPN 未启用，缺当前六份完整契约与账号 | 用户授权 VPN 切换并提供可复核契约/凭据 |
| 真实性能采集 | BLOCKED | SoloX、ADB/tidevice、授权真机缺失 | 提供设备、线缆/代理、包名和采集授权 |
| 实时音视频链路 | BLOCKED | 未提供授权 HLS/FLV/WebRTC/DASH 地址 | 提供非生产流或可公开读取的真实样本 |
| 真实旧 PostgreSQL 迁移 | WAIVED/NOT PASS | 无脱敏旧库快照 | 提供可恢复的脱敏旧库快照和版本说明 |

## 10. 数据清理规则

1. 所有本地写入实体使用 `batch60-` 前缀。
2. 每条外部写用例必须在执行前确认 R2 环境、允许范围和清理权限。
3. 自动化写操作使用 `try/finally` 回读并清理；清理失败单独建缺陷。
4. 生产 R3 不执行写操作、支付、发布、封禁、批量修改或压力测试。
5. Mock 数据只用于明确的故障/边界场景，并在用例、证据和报告三处标记 `M`。
