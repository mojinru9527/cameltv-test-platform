# Batch 61 问题与阻塞台账

## 1. 台账规则

- Batch 60 ID 原样继承，不重编号、不删除、不覆盖原状态；`B61 disposition` 只表示 Batch 61 范围处置。
- `MUST`：Batch 61 test release 候选必须关闭并复测。
- `SHOULD`：应在 Batch 61 完成，但仅可通过具名风险接受决定是否延后。
- `EXTERNAL BLOCKED`：缺外部环境、账号、契约、设备或数据；无通过计数。
- `DEFERRED`：明确进入 Batch 62+，不计通过。
- 执行状态只使用 `PASS`、`FAIL`、`BLOCKED`、`NOT RUN`、`DEFERRED`，定义见 `batch-61-acceptance-matrix.md`。

## 2. Batch 60 继承项与 Batch 61 处置

| 原始 ID | 级别 | Batch 60 原状态 | 问题摘要 | B61 disposition | 工作流 | Owner | B61 当前状态 | 关闭/解除证据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B60-P0-001 | P0 | 已修复待复测 | 体育登录凭据曾进入 Midscene 指令 | `MUST` | W2 | Sports QA / `UNASSIGNED` | `BLOCKED` | 授权 R2 登录 + 产物 secret scan |
| B60-P0-002 | P0 | 已修复待复测 | 体育流量证据深层敏感字段泄露风险 | `MUST` | W2 | Sports QA / `UNASSIGNED` | `BLOCKED` | R2 请求/响应/trace canary 零命中 |
| B60-P0-003 | P0 | 已修复待复测 | 项目切换后陈旧数据与写上下文错位 | `MUST` | W1 | Frontend owner / `UNASSIGNED` | `NOT RUN` | 全项目域页面 A→B 浏览器/API/DB 复测 |
| B60-P0-004 | P0 | 部分关闭 | 多执行入口 production guard 不统一 | `MUST` | W1 | Backend architecture owner / `UNASSIGNED` | `NOT RUN` | 所有入口参数化拒绝/允许证据，拒绝零副作用 |
| B60-P1-002 | P1 | 静态确认 | 成熟模块入口隐藏、命令面板与权限不一致 | `MUST` | W1 | Product/frontend owner / `UNASSIGNED` | `NOT RUN` | 路由/菜单/命令/权限/PRD 对账 |
| B60-P1-006 | P1 | 已修复待复测 | 用例批量删除缺少完整动态闭环 | `MUST` | W1 | Frontend owner / `UNASSIGNED` | `NOT RUN` | 取消零请求；确认后 DB/审计；失败回滚 |
| B60-P1-008 | P1 | 已修复待复测 | 发布包历史交互标注回显/坐标可信度 | `MUST` | W1 | Frontend owner / `UNASSIGNED` | `NOT RUN` | 保存→重载→编辑真实截图闭环 |
| B60-P1-009 | P1 | 部分已修复待复测 | 多页面无权限写入口仍可见 | `MUST` | W1 | RBAC/frontend owner / `UNASSIGNED` | `NOT RUN` | 三身份 UI/API 权限矩阵 |
| B60-P1-010 | P1 | 静态确认 | 大范围 API-only 能力缺 UI 或事实说明 | `DEFERRED` | Batch 62 | Product owner / `UNASSIGNED` | `DEFERRED` | Batch 62 单独能力产品化计划 |
| B60-P1-011 | P1 | 静态确认 | label、aria、键盘、焦点与三视口缺口 | `MUST` | W1 | Accessibility owner / `UNASSIGNED` | `PASS` | 2026-08-01：Chromium headed 三视口 axe/键盘矩阵 21/21，通过页含 login/apitest/uitest/report/schedule/notify/release-bundles |
| B60-P1-012 | P1 | 静态确认 | 体育脚本弱断言、无数据 skip、无后台主链 | `MUST` | W2 | Sports QA / `UNASSIGNED` | `BLOCKED` | 无静默 skip；P0/P1 业务 oracle；R2 数据 |
| B60-P1-013 | P1 | 静态确认 | production smoke 可在登录/API 未工作时假绿 | `MUST` | W2 | Sports QA / `UNASSIGNED` | `BLOCKED` | 缺凭据明确 BLOCKED；真实会话/API/业务断言 |
| B60-P1-015 | P1 | **已关闭** | SQLite、备份和 runtime 制品曾进入仓库 | `MUST`（计划指定防回归） | W1 | Repository hygiene owner / `UNASSIGNED` | `PASS` | 2026-08-01：移除误跟踪 Playwright runtime 产物并补忽略规则；数据库/备份/凭据/调试遗留扫描无本批新增命中 |
| B60-P1-016 | P1 | 静态确认 | PRD、技术栈、认证和能力成熟度漂移 | `MUST` | W1 | Product/docs owner / `UNASSIGNED` | `PASS` | 2026-08-01：PRD、README、CLAUDE 与代码/路由/认证/能力成熟度事实对账完成，双端全量与构建通过 |
| B60-P1-017 | P1 | 静态确认 | 全平台正式验收资产不足，Mock 与真实证据混杂 | `MUST` | W1 | Acceptance QA / `UNASSIGNED` | `NOT RUN` | 正负面功能点矩阵与证据分层统计 |
| B60-P1-019 | P1 | 静态确认 | API 五入口环境、变量、保护和结果不一致 | `MUST` | W1 | Backend/API owner / `UNASSIGNED` | `NOT RUN` | quick/asset/single/group/batch GET/POST 参数化回归 |
| B60-P1-020 | P1 | 静态确认 | 强制改密前端流程缺失 | `MUST` | W1 | Auth owner / `UNASSIGNED` | `PASS` | 2026-08-01：后端强制改密 7/7、相关鉴权/隔离定向回归 51/51；真实 8027/5197 浏览器完成强制改密→退出→新密码重登，旧版访问 JWT、改密前 JWT 与重置 Token 均 fail-closed |
| B60-P1-023 | P1 | 已复现 | 体育自动化 7 个 high runtime 漏洞 | `MUST` | W2 | Supply-chain owner / `UNASSIGNED` | `PASS` | 2026-08-01：Midscene `1.10.8` + audited overrides；clean `npm ci`、`npm audit --omit=dev` 为 0 漏洞；typecheck/security 17/17/38 条收集通过 |
| B60-P2-001 | P2 | 已修复待复测 | 搜索请求提交态仍缺浏览器 Network 复核 | `SHOULD` | W1 | Frontend owner / `UNASSIGNED` | `NOT RUN` | 每次提交 1 个有效 GET、旧请求取消 |
| B60-P2-002 | P2 | 部分关闭 | 移动/平板触控与小按钮全局审计未完成 | `DEFERRED` | Batch 62 | UX owner / `UNASSIGNED` | `DEFERRED` | Batch 62 全局触控矩阵 |
| B60-P2-006 | P2 | 已复现 | 知识中心桌面标签和卡片密度 | `DEFERRED` | Batch 62 | UX owner / `UNASSIGNED` | `DEFERRED` | Batch 62 视觉/响应式复测 |
| B60-BLK-001 | P0 | 阻塞 | Test5 六服务、VPN、契约、账号和清理规则缺失 | `EXTERNAL BLOCKED` | W2 | Test5/VPN owner / `UNASSIGNED` | `BLOCKED` | 见 2026-08-01 前置条件登记 |
| B60-BLK-002 | P0 | 阻塞 | AI/蓝湖/OCR 非生产凭据与授权缺失 | `EXTERNAL BLOCKED` | 外部 | Product/privacy owner / `UNASSIGNED` | `BLOCKED` | 独立非生产凭据、数据范围、费用/隐私授权 |
| B60-BLK-003 | P1 | 阻塞 | SMTP/Webhook/Jira/TAPD/ELK 端点与凭据缺失 | `EXTERNAL BLOCKED` | 外部 | Integration owner / `UNASSIGNED` | `BLOCKED` | 非生产端点、最小权限凭据和脱敏规则 |
| B60-BLK-004 | P1 | 阻塞 | SoloX、ADB/tidevice 与授权真机缺失 | `EXTERNAL BLOCKED` | 外部 | Device/performance owner / `UNASSIGNED` | `BLOCKED` | 设备、包名、采集窗口与恢复方案 |
| B60-BLK-005 | P0 | 阻塞 | 脱敏旧 PostgreSQL 快照缺失 | `EXTERNAL BLOCKED` | W3/M4 | DBA/data owner / `UNASSIGNED` | `BLOCKED` | 快照、来源版本、checksum、恢复与升级断言 |
| OPS0 | P0 | Phase 0 部分完成 | release manifest 机器契约尚未交付 | `MUST` | W3 新项目 | DevOps owner / `UNASSIGNED` | `BLOCKED` | schema/样例/hash/SBOM/签名/QA 绑定 |
| OPS1 | P0 | 未完成 | immutable test 发布、Jenkins、状态机和回滚尚未交付 | `MUST` | W3 新项目 | DevOps owner / `UNASSIGNED` | `BLOCKED` | test digest/revision、事件链、失败恢复/回滚演练 |

## 3. Batch 61 新发现

| ID | 级别 | 发现摘要 | B61 disposition | 工作流 | Owner | 当前状态 | 关闭/接受条件 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B61-P1-001 | P1 | backend lock 中 `ecdsa 0.19.2` 命中 high `GHSA-wj6h-64fc-37mp` / `CVE-2024-23342`（CVSS 7.4），上游无修复版本 | `MUST` | W2 发现，runtime 修复需独立 backend scope | Backend security/supply-chain owner / `UNASSIGNED` | `FAIL` | 移除/替换 `python-jose` 的受影响依赖并全回归，或由具名安全 owner 给出书面风险接受、到期日和升级/架构触发器；当前 HS256 不走 ECDSA 签名仅为 exploitability 说明，不构成接受 |

## 4. 处置汇总

| B61 disposition | 数量 | 说明 |
| --- | ---: | --- |
| `MUST` | 20 | 计划指定 19 项，加本批审计新发现 B61-P1-001；含 B60 已关闭但要求防回归的 B60-P1-015 |
| `SHOULD` | 1 | B60-P2-001 |
| `EXTERNAL BLOCKED` | 5 | B60-BLK-001～005 |
| `DEFERRED` | 3 | B60-P1-010、B60-P2-002、B60-P2-006 |
| 合计 | 29 | 与继承项及 Batch 61 新发现数据行一致 |

## 5. 带日期的外部阻塞登记

| 阻塞范围 | 状态 | 登记日期 | Owner | 解除条件 | 复核时限 |
| --- | --- | --- | --- | --- | --- |
| Test5/VPN/六服务契约 | `BLOCKED` | `2026-08-01` | `UNASSIGNED` | 书面 VPN 窗口、六契约版本/SHA、网关路由 | 条件齐备后 1 个工作日先执行 P0 只读/鉴权负面 |
| Test5 只读与写测试账号 | `BLOCKED` | `2026-08-01` | `UNASSIGNED` | 最小权限只读账号；写账号另含额度、幂等、回滚和清理授权 | 条件齐备后按单独窗口执行 |
| 体育稳定数据与清理 | `BLOCKED` | `2026-08-01` | `UNASSIGNED` | 固定业务 key、状态、保留期、清理 API/owner | 条件齐备后 1 个工作日建 manifest |
| 旧 PostgreSQL 快照 | `BLOCKED` | `2026-08-01` | `UNASSIGNED` | 脱敏快照、来源版本、checksum、恢复步骤与数据断言 | 条件齐备后 M4 执行 |
| DevOps/test release 基础设施 | `BLOCKED` | `2026-08-01` | `UNASSIGNED` | registry、Runner、PG16、备份、Secret reference、访问窗口 | owner 和环境均登记后才能解除 OPS0/OPS1 |

## 6. 状态更新约束

1. B60 历史状态只在来源列保留；B61 复测结果写入 B61 状态，不回写或改名旧 ID。
2. `FAIL` 必须记录输入、预期、实际、环境、证据和缺陷；`BLOCKED` 必须记录 owner 与解除条件。
3. `PASS` 必须同时满足验收矩阵中的最低证据；静态代码存在、脚本收集或历史截图不足以关闭。
4. W1 合并后才能创建 W2；W2 合并后才能创建 W3；每次均从最新 `origin/main` 创建独立 worktree。
