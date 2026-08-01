# Batch 61 真实数据、外部前置与 Test 发布环境清单

## 1. 基线与数据原则

| 项目 | 值 |
| --- | --- |
| 冻结日期 | `2026-08-01` |
| 代码基线 | `7d9a0118f6e2d5d505f9e0dde7b59881f027bb6b` |
| W1 | `feature/batch-61-production-safety-and-test-credibility` |
| W2 | `feature/batch-61-sports-api-ui-r2-acceptance`，仅在 W1 合并后从最新 `main` 创建 |
| W3 | `feature/batch-61-test-release-control-plane-mvp`，仅在 W2 合并后从最新 `main` 创建 |
| 运维项目边界 | 在 `deploy/release-control` **新开独立项目**；独立依赖、schema、CLI、测试和 PR，不把 Batch 62 运维 UI 提前塞入测试平台 |
| 数据原则 | R1、R2、R3、M 分层；历史数据不证明当前环境；缺外部条件时标记 `BLOCKED`，不得造数据或改记 `PASS` |

## 2. 数据等级

| 等级 | Batch 61 用途 | 禁止推导 |
| --- | --- | --- |
| R1 | 继承 Batch 60 已脱敏需求、原型、OpenAPI、历史流量、用例、真实 MP4 和本地闭环数据，支持本地加固与回归 | 不证明当前 Test5/production 状态 |
| R2 | 获授权 Test5 六服务、用户端、运营后台、当前契约、账号和稳定业务记录 | VPN、契约、账号或数据缺一时不得执行/通过；写链需单独授权 |
| R3 | 书面白名单内 production GET/HEAD 只读观测 | 禁止支付、退款、赠送、发布、封禁、推流、压测、账号管理或任何写操作 |
| M | 明确标记的故障注入、坏格式、不可达或边界数据 | 不得替代 R1/R2/R3 正常功能或 PC PASS 快照 |

## 3. R1 可追溯输入

| 数据/资产 | 来源 | Batch 61 用途 | 初始状态 |
| --- | --- | --- | --- |
| 用户端/运营后台原型和更新日志 | Batch 60 manifest 第 3 节 | 路由、菜单、需求和只读旅程基线 | `NOT RUN`（B61 尚未复核） |
| 用户端 290、后台 359、最新版本 179 及 P0 HOME/LIST/DETAIL/PAY/REFUND/BONUS 用例 | Batch 60 manifest 第 4 节 | 体育正负面覆盖和 R2 用例选择 | `NOT RUN` |
| 5-path CamelTv OpenAPI、5 条历史脱敏流量、历史 Test5 六服务用例 | Batch 60 manifest 第 5 节 | 本地五入口回归和 R2 契约差异输入 | `NOT RUN` |
| Batch 60 本地 5 资产/7 用例/计划/报告/缺陷/追溯链 | Batch 60 manifest 第 6 节 | 回归数据结构和断言基线 | `NOT RUN`；不得沿用 B60 PASS 作为 B61 PASS |
| 仓库真实 MP4 | `tests/音视频项目测试/materials/av_sync_test.mp4` | 本地真实媒体回归 | `NOT RUN` |
| Batch 60 PC、API、DB、审计和安全证据 | `work-logs/evidence/batch-60-sports-platform-validation/` | 历史对比和缺陷复测输入 | 仅历史基线 |

## 4. Test5 R2 前置包

| 必需输入 | 状态 | 阻塞日期 | Owner | 不可替代条件 |
| --- | --- | --- | --- | --- |
| OpenVPN 切换授权、vpn07/OpenVPN 互斥规则、回切步骤 | `BLOCKED` | `2026-08-01` | `UNASSIGNED`（Test5/VPN owner） | 未授权不切换适配器、不探测内网 |
| camel 当前 OpenAPI | `BLOCKED` | `2026-08-01` | `UNASSIGNED`（camel contract owner） | 需要导出时间、版本/SHA 和网关路由 |
| live 当前 OpenAPI | `BLOCKED` | `2026-08-01` | `UNASSIGNED`（live contract owner） | 同上 |
| payment 当前 OpenAPI | `BLOCKED` | `2026-08-01` | `UNASSIGNED`（payment contract owner） | 同上；默认只读，写需另批 |
| studio 当前 OpenAPI | `BLOCKED` | `2026-08-01` | `UNASSIGNED`（studio contract owner） | 同上 |
| konfi 当前 OpenAPI | `BLOCKED` | `2026-08-01` | `UNASSIGNED`（konfi contract owner） | 同上 |
| account 当前 OpenAPI | `BLOCKED` | `2026-08-01` | `UNASSIGNED`（account contract owner） | 同上 |
| 最小权限只读账号/Token | `BLOCKED` | `2026-08-01` | `UNASSIGNED`（account owner） | 需要有效期、权限边界、撤销和保管方式 |
| 首页/列表/详情/后台查询稳定业务 key | `BLOCKED` | `2026-08-01` | `UNASSIGNED`（sports data owner） | 按业务 key 选择，禁止“第一行”或随机数据 |
| 支付/退款/赠送专用可丢弃账号与书面授权 | `BLOCKED` | `2026-08-01` | `UNASSIGNED`（product/finance/account owner） | 需要金额上限、窗口、幂等号、账本/审计查询和禁做项 |
| 写数据回滚/清理 API 与 owner | `BLOCKED` | `2026-08-01` | `UNASSIGNED`（cleanup owner） | 清理失败必须建缺陷，不得抹除证据 |

当前 R2 包不完整，故 R2 结论保持 `BLOCKED`。历史 `892/1323`、旧截图、脚本收集或 R1 数据不得替代当前六服务契约和真实会话。

## 5. PostgreSQL 与 Test 发布环境包

| 必需输入 | 状态 | 阻塞日期 | Owner | 解除条件 |
| --- | --- | --- | --- | --- |
| 脱敏旧 PostgreSQL 快照 | `BLOCKED` | `2026-08-01` | `UNASSIGNED`（DBA/data owner） | 来源版本、checksum、恢复步骤、升级前后业务断言 |
| PostgreSQL 16 test 实例 | `BLOCKED` | `2026-08-01` | `UNASSIGNED`（DevOps owner） | 独立数据库、最小权限 Secret reference、备份/恢复位置 |
| Test registry | `BLOCKED` | `2026-08-01` | `UNASSIGNED`（DevOps owner） | 仓库、认证引用、保留与不可变 digest 策略 |
| Jenkins/Runner | `BLOCKED` | `2026-08-01` | `UNASSIGNED`（DevOps owner） | 只消费 `release_id` 的执行身份和审计保留 |
| Backup target | `BLOCKED` | `2026-08-01` | `UNASSIGNED`（DevOps/DBA owner） | 可读性校验、保留期和恢复 runbook |
| Secret reference mechanism | `BLOCKED` | `2026-08-01` | `UNASSIGNED`（DevOps/security owner） | 版本化引用；manifest、日志和证据零明文 Secret |
| DevOps accountable owner | `BLOCKED` | `2026-08-01` | `UNASSIGNED` | 具名人类 owner 接受环境、凭据、部署窗口和回滚责任 |

空库可用于安装链测试，但不能替代真实旧快照 A10；本地 Docker/SQLite 也不能替代 test digest 部署演练。

## 6. 数据使用与清理规则

1. 本地实体统一使用 `batch61-` 前缀和独立项目/数据库；禁止写生产数据。
2. R2 只读优先执行首页、列表、详情、健康、缺/错 Token 和权限负面。
3. 支付、退款、赠送仅在单独书面授权、专用账号、额度、幂等、账本/审计查询和 cleanup owner 全部存在时执行。
4. 自动化写链必须 `try/finally` 回读与清理；清理失败记录 `FAIL` 和缺陷，不得删除失败证据。
5. 凭据只通过未跟踪 Secret 注入；不得进入 AI prompt、命令行回显、截图、trace、HTML、JSON、日志或仓库。
6. 证据使用 canary 扫描 URL/query/header/request/response/body；出现任一敏感值即 `FAIL`。
7. 运维新项目只保存 release/环境/事件的脱敏事实和 Secret reference，不保存 Secret 值。

## 7. 当前结论

- R1：可用作输入，Batch 61 执行状态为 `NOT RUN`。
- R2：`BLOCKED`，owner 均为 `UNASSIGNED`。
- 旧 PostgreSQL：`BLOCKED`，owner 为 `UNASSIGNED`。
- Test 发布基础设施与 DevOps owner：`BLOCKED / UNASSIGNED`。
- Production：`DEFERRED`。
