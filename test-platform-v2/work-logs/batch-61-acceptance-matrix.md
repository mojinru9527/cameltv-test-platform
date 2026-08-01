# Batch 61 生产安全、测试可信度与 Test 发布 MVP 验收矩阵

## 1. 固定基线

| 项目 | 固定值 |
| --- | --- |
| 冻结日期 | `2026-08-01` |
| 分支 | `feature/batch-61-sports-acceptance-and-supply-chain`（W2） |
| 基线提交 | `174e002fbe53d75d49aaf09c269fac622a4c7c58`，W1 PR #89 合并后的 `origin/main` |
| 工作流 / 执行器 | `agent-team` / `codex` |
| 需求源 | Batch 61 实施计划 Task 2；Batch 60 QA、问题、真实数据、PC 快照、全平台矩阵和体育 API/UI 专项报告 |
| 当前候选结论 | `NOT READY`；20 个 MUST 为 5 `PASS`、1 `FAIL`、6 `BLOCKED`、8 `NOT RUN`，不能解释为本地加固或发布已通过 |
| Production | `DEFERRED`；Batch 61 不执行 production 发布或数据库迁移 |

## 2. 唯一执行状态词汇

| 状态 | 精确定义 |
| --- | --- |
| `PASS` | 预期结果与业务、API、数据、副作用及审计证据全部一致，且证据可按 ID 复核 |
| `FAIL` | 已执行，至少一个必需断言不满足；必须关联原始缺陷 ID 或新增缺陷 ID |
| `BLOCKED` | 外部前置条件缺失；不获得通过计数，必须记录阻塞日期、解除条件和 owner；owner 未指定时写 `UNASSIGNED` |
| `NOT RUN` | 可执行条件存在，但 Batch 61 尚未执行或尚未完成 B61 复测 |
| `DEFERRED` | 经范围冻结明确排除出 Batch 61；不得计为通过，必须注明后续批次 |

空态、加载态、错误页、Mock、脚本可收集、单元测试绿色或历史 Batch 60 证据均不能自动转换为 Batch 61 `PASS`。

## 3. 三工作流与顺序合并

| 顺序 | 工作流 / 分支 | 边界 | 创建与合并门禁 |
| ---: | --- | --- | --- |
| 1 | W1 `feature/batch-61-production-safety-and-test-credibility` | 生产保护、项目隔离、RBAC、a11y、PRD/测试资产和本冻结文档 | PR #89 已合入 `main` |
| 2 | W2 `feature/batch-61-sports-acceptance-and-supply-chain` | 体育 Playwright/API 可信度、供应链、Test5 R2 验收 | 当前工作流；基于 W1 合入后的 `origin/main@174e002f`；合入后才创建 W3 |
| 3 | W3 `feature/batch-61-test-release-control-plane-mvp` | **新开独立运维发布项目** `deploy/release-control`，交付 manifest、CLI、状态机、Jenkins 适配和 test 回滚 | 必须基于已合入 W2 的最新 `main`；独立 worktree、PR、依赖和证据，不与测试平台页面代码混作一个项目 |

三个工作流可以在人员规划上并行准备，但仓库集成必须按 W1 → W2 → W3 顺序；禁止从旧 `main` 创建后续 worktree。仅当最终证据对账产生跟踪文件变化时，才另建最终 acceptance PR。

## 4. Batch 61 MUST 冻结矩阵

所有角色均按计划中的职责记录；没有获得真实姓名或书面委派的角色一律为 `UNASSIGNED`，不以 Agent 名称冒充人类审批或外部授权 owner。

| 原始 ID | Batch 60 状态 | 工作流 | Batch 61 必须验收结果 | Accountable role / named owner | Implementer | Reviewer | 起止里程碑 | 最低证据 | Blocker owner | 当前状态 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B60-P0-001 | 已修复待复测 | W2 | 授权 Test5 登录全程使用确定性 locator；凭据不进入 AI 指令、日志、截图或报告 | Sports QA / `UNASSIGNED` | W2 Agent Team / `UNASSIGNED` | Security + acceptance reviewer / `UNASSIGNED` | M2 → M4 | 安全红队、真实会话、产物 secret scan | Test5/VPN/account owner / `UNASSIGNED` | `BLOCKED` |
| B60-P0-002 | 已修复待复测 | W2 | Test5 URL/query/header/body/response 深层脱敏，canary 扫描零命中且保留关联 ID | Sports QA / `UNASSIGNED` | W2 Agent Team / `UNASSIGNED` | Security + acceptance reviewer / `UNASSIGNED` | M2 → M4 | 脱敏单测、真实 R2 trace/JSON/HTML/log 扫描 | Test5/VPN/account owner / `UNASSIGNED` | `BLOCKED` |
| B60-P0-003 | 已修复待复测 | W1 | testcase/testplan/report/defect/trace/environment/dataset/integration/uitest 全部完成 A→B 切换，无陈旧数据或错项目写请求 | Frontend owner / `UNASSIGNED` | Codex Agent Team | Acceptance reviewer / `UNASSIGNED` | M1 → M5 | 浏览器网络、API、DB/任务、A/B 项目隔离截图 | N/A（本地可控） | `NOT RUN` |
| B60-P0-004 | 部分关闭 | W1 | API quick/asset/single/group/batch、UI、发布包回归和双向集成统一服务端 production guard；拒绝时零外呼、零任务、零副作用 | Backend architecture owner / `UNASSIGNED` | Codex Agent Team | Security + acceptance reviewer / `UNASSIGNED` | M1 → M5 | 参数化行为测试、浏览器范围预览、网络/DB/审计零副作用 | N/A（本地可控） | `NOT RUN` |
| B60-P1-002 | 静态确认 | W1 | 成熟模块可发现；未完成模块显式展示状态；菜单、命令面板、权限和 PRD 一致 | Product/frontend owner / `UNASSIGNED` | Codex Agent Team | Acceptance reviewer / `UNASSIGNED` | M1 → M5 | 路由/菜单矩阵、三身份浏览器证据、文档 diff | N/A（本地可控） | `NOT RUN` |
| B60-P1-006 | 已修复待复测 | W1 | 批量删除确认显示数量/项目/不可逆语义；取消零请求；确认后 UI/API/DB/审计一致，失败回滚 | Frontend owner / `UNASSIGNED` | Codex Agent Team | Acceptance reviewer / `UNASSIGNED` | M1 → M5 | 浏览器、Network、DB 前后、审计及失败注入 | N/A（本地可控） | `NOT RUN` |
| B60-P1-008 | 已修复待复测 | W1 | 保存截图标注后重载并编辑；历史真实坐标不被清空，旧语义合成坐标不得冒充真实定位 | Frontend owner / `UNASSIGNED` | Codex Agent Team | Acceptance reviewer / `UNASSIGNED` | M1 → M5 | 保存→重载→编辑浏览器视频/截图、API/DB 回读 | N/A（本地可控） | `NOT RUN` |
| B60-P1-009 | 部分已修复待复测 | W1 | testplan/requirement/report/schedule/environment/dataset/notify/API 调试统一隐藏或禁用无权限写入口，后端仍拒绝 | Frontend + RBAC owner / `UNASSIGNED` | Codex Agent Team | Security + acceptance reviewer / `UNASSIGNED` | M1 → M5 | admin/tester/readonly 三身份 UI/API 矩阵 | N/A（本地可控） | `NOT RUN` |
| B60-P1-011 | 静态确认 | W1 | 目标页 label、可访问名称、键盘、焦点、axe、三视口和网络门禁通过 | Frontend accessibility owner / `UNASSIGNED` | Codex Agent Team | Acceptance reviewer / `UNASSIGNED` | M1 → M5 | axe/键盘/焦点、1440×900/768×1024/390×844、GET 次数 | N/A（本地可控） | `PASS` |
| B60-P1-012 | 静态确认 | W2 | 每个体育 P0/P1 旅程具备业务 oracle；缺数据为结构化 BLOCKED，不允许无解释 skip；补最小运营后台只读链 | Sports QA / `UNASSIGNED` | W2 Agent Team / `UNASSIGNED` | Acceptance reviewer / `UNASSIGNED` | M2 → M4 | Playwright 结果、DOM/API/data oracle、三次首跑 | Sports data/account owner / `UNASSIGNED` | `BLOCKED` |
| B60-P1-013 | 静态确认 | W2 | production smoke 无凭据不得绿色；登录、核心 API 和业务元素使用非恒真断言 | Sports QA / `UNASSIGNED` | W2 Agent Team / `UNASSIGNED` | Acceptance reviewer / `UNASSIGNED` | M2 → M4 | 正负面脚本、真实 R2 只读执行、失败截图/trace | Test5/VPN/account owner / `UNASSIGNED` | `BLOCKED` |
| B60-P1-015 | **已关闭** | W1 | 保留原关闭事实；Batch 61 防回归确认无 SQLite、备份、凭据、runtime 输出或临时制品进入交付 | Repository hygiene owner / `UNASSIGNED` | Codex Agent Team | Acceptance reviewer / `UNASSIGNED` | M1 → M5 | `git status`、跟踪文件扫描、secret/artifact scan | N/A（本地可控） | `PASS` |
| B60-P1-016 | 静态确认 | W1 | React/Auth/模块成熟度/随机或真实执行等 PRD 与代码、路由、OpenAPI、README 一致 | Product/docs owner / `UNASSIGNED` | Codex Agent Team | Acceptance reviewer / `UNASSIGNED` | M1 → M5 | 事实对照表、文档 diff、路由/OpenAPI 清单 | N/A（本地可控） | `PASS` |
| B60-P1-017 | 静态确认 | W1 | 建立生产级全功能点正负面资产；Mock、组件、真实后端和外部证据分开统计 | Acceptance QA / `UNASSIGNED` | Codex Agent Team | Independent acceptance reviewer / `UNASSIGNED` | M1 → M5 | 功能点→用例→证据→缺陷矩阵及覆盖率自检 | N/A（本地可控） | `NOT RUN` |
| B60-P1-019 | 静态确认 | W1 | API quick/asset/single/group/batch 五入口的环境、变量、授权、production guard、结果 schema 完全等价 | Backend/API owner / `UNASSIGNED` | Codex Agent Team | Security + acceptance reviewer / `UNASSIGNED` | M1 → M5 | GET/POST 参数化契约、Network、结果快照、零误触发 | N/A（本地可控） | `NOT RUN` |
| B60-P1-020 | 静态确认 | W1 | `must_change_password` 前端声明和受保护流程完成；弱密码、取消、过期、重置后业务路由均 fail-closed | Auth owner / `UNASSIGNED` | Codex Agent Team | Security + acceptance reviewer / `UNASSIGNED` | M1 → M5 | API、路由守卫、浏览器、审计和密码策略证据 | N/A（本地可控） | `PASS` |
| B60-P1-023 | 已复现 | W2 | 体育 UI 自动化无未接受 high/critical runtime 漏洞；升级后安全、类型、收集和真实 R2 只读旅程无回归 | Frontend supply-chain owner / `UNASSIGNED` | Codex Agent Team | Security + acceptance reviewer / `UNASSIGNED` | M2 → M5 | Midscene 1.10.8 lockfile、clean `npm audit --omit=dev` 0、typecheck、安全 17/17、38 条收集 | N/A（本地可控） | `PASS` |
| B61-P1-001 | W2 审计新发现 | W2/后续独立 backend scope | backend runtime 不含未接受 high/critical；`ecdsa` 高危需移除/替换或具名限期接受 | Backend security/supply-chain owner / `UNASSIGNED` | `UNASSIGNED`（W2 scope 不含 runtime 依赖） | Security + architecture reviewer / `UNASSIGNED` | M2 → M5 | 锁定 `pip-audit`、依赖替换回归，或批准记录含 exploitability/owner/expiry/trigger | Backend security owner / `UNASSIGNED` | `FAIL` |
| OPS0 | Batch 60 Phase 0 部分完成 | W3 | 新项目的 release manifest schema、正负样例、内容 hash、SBOM/签名/checksum/Alembic/QA 绑定可机器校验 | DevOps owner / `UNASSIGNED` | W3 Agent Team / `UNASSIGNED` | Architecture + acceptance reviewer / `UNASSIGNED` | M3 → M5 | schema 测试、schema-check、secret scan、manifest hash | DevOps owner / `UNASSIGNED` | `BLOCKED` |
| OPS1 | Batch 60 未完成 | W3 | test 按 digest 幂等部署；锁、备份、migration、健康、Smoke、审计、失败恢复和应用回滚通过；production 稳定拒绝 | DevOps owner / `UNASSIGNED` | W3 Agent Team / `UNASSIGNED` | DBA + acceptance reviewer / `UNASSIGNED` | M3 → M5 | test 部署/回滚演练、实际 digest/revision、事件链 | DevOps owner / `UNASSIGNED` | `BLOCKED` |

### 4.1 当前 MUST 汇总（W1 + W2 检查点）

| 状态 | 数量 |
| --- | ---: |
| `PASS` | 5 |
| `FAIL` | 1 |
| `BLOCKED` | 6 |
| `NOT RUN` | 8 |
| `DEFERRED` | 0 |
| 合计 | 20 |

### 4.2 W1/W2 当前证据与未关闭边界

- 后端：`python -m ruff check app/ --select F821` 通过；初始化 `lanhu-mcp` 子模块后的全量 `pytest tests -q` 为 `976 passed, 3 skipped, 0 failed`。3 条 skip 为 PostgreSQL 并发专用条件，不计作通过证据。
- 前端：`npm test -- --run` 为 `291/291`；`npm run typecheck` 与 `npm run build` 通过。
- 浏览器：在本 worktree `http://127.0.0.1:5197` 以 Chromium headed 模式运行四组 Batch 61 矩阵，`39/39` 通过；其中包含三视口 axe/键盘 21 条、项目切换 11 条、三角色 RBAC 3 条、删除与强制改密 4 条。
- 真实后端浏览器链：使用本 worktree `8027` 后端与 `5197` 前端完成首次登录强制改密、旧会话退出、新密码重新登录到工作台；临时凭据仅经进程环境传递，启动日志已清空删除。
- B60-P1-011、015、016、020 已达到本检查点最低证据，记为 `PASS`。
- B60-P0-003、004 和 B60-P1-002、006、008、009、017、019 仍缺计划要求的真实后端/DB/审计、全部入口浏览器基数或历史标注保存回读等动态闭环，继续记为 `NOT RUN`，不得以 Mock E2E、组件测试或全量回归绿色替代。
- W2 体育自动化：Midscene 升至 `1.10.8`，clean `npm audit --omit=dev` 为 0；typecheck、安全合同 `17/17`、sports 收集 `38 tests in 9 files`、production smoke 合同 `6/6` 均通过，B60-P1-023 关闭。
- W2 R2：API 16 条为 `13 P0 + 3 P1 BLOCKED`，UI 23 条为 `20 P0 + 3 P1 BLOCKED`；Test5 请求/浏览器均为 0，故 B60-P0-001/002、P1-012/013 继续 BLOCKED。
- backend 依赖观察：`pip-audit 2.10.1` 审计 118 个锁定依赖，发现 1 个 high `ecdsa 0.19.2`（B61-P1-001）；当前 HS256 不触发 ECDSA 签名路径，但无具名风险接受且上游无修复，A11 保持 FAIL。

## 5. 外部前置条件冻结

| 前置条件 | 状态 | 阻塞登记日期 | Owner | Day 2 解除条件 |
| --- | --- | --- | --- | --- |
| OpenVPN 切换窗口与互斥网络规则确认 | `BLOCKED` | `2026-08-01` | `UNASSIGNED`（Test5/VPN owner） | 书面授权窗口、回切步骤和联系人 |
| camel/live/payment/studio/konfi/account 六份当前契约 | `BLOCKED` | `2026-08-01` | `UNASSIGNED`（service contract owners） | 提供导出时间、版本/SHA、网关路由和兼容说明 |
| 最小权限 Test5 只读账号/Token | `BLOCKED` | `2026-08-01` | `UNASSIGNED`（account owner） | 提供有效期、权限边界、保管与撤销方式 |
| 稳定业务记录键、写测试专用账号、额度和清理规则 | `BLOCKED` | `2026-08-01` | `UNASSIGNED`（sports data/cleanup owner） | 固定业务 key；写链另有书面授权、上限、回滚/清理 owner |
| 脱敏旧 PostgreSQL 快照 | `BLOCKED` | `2026-08-01` | `UNASSIGNED`（DBA/data owner） | 提供来源版本、校验和、恢复步骤和升级前后断言 |
| Test registry、Jenkins/Runner、PostgreSQL 16、备份与 Secret reference | `BLOCKED` | `2026-08-01` | `UNASSIGNED`（DevOps owner） | 完成环境登记、访问授权、Secret 引用和恢复位置确认 |

计划中的 Day 2 是相对里程碑；批次绝对开工日尚未由产品 owner 批准，因此绝对 Day 2 日期保持 `UNASSIGNED`，不得自行推算或伪造承诺日期。

## 6. 正负面覆盖基线

| 验收域 | 正面主流程 | 负面/异常流 | 必须验证 |
| --- | --- | --- | --- |
| 生产保护 | 获授权目标显示范围后执行安全请求 | 无权限、无确认、跨项目环境、重复点击、production 未配置 | 服务端拒绝优先；拒绝后网络、任务、DB、审计业务副作用均为 0 |
| 项目/RBAC | 同项目 admin/tester/readonly 合法操作 | 跨项目、不存在资源、低权限、切换中陈旧响应 | 列表/详情/子资源/写操作一致，不泄露名称、数量或结构 |
| 体育 API/UI | 当前契约和稳定 R2 数据的只读首页/列表/详情/鉴权 | 缺参、错 Token、无数据、断网、元素缺失、供应链风险 | 无静默 skip；HTTP/业务/核心数据或 DOM/API/data oracle 同时成立 |
| Test 发布 | 一个 immutable manifest 部署到 test 并重试幂等 | digest 漂移、多 Alembic head、Secret/备份缺失、迁移/健康/Smoke 失败 | 状态机 fail-closed；实际 digest/revision 匹配；应用回滚有证据，数据库不自动 downgrade |

## 7. 放行规则

- `READY FOR TEST RELEASE`：20 个 MUST 全部 `PASS`；P0/P1 无 `FAIL`、`BLOCKED` 或 `NOT RUN`；Test 发布和应用回滚演练通过；required checks 绿色。
- `LOCAL HARDENING COMPLETE / EXTERNAL BLOCKED`：本地可控 MUST 全部 `PASS`，但 Test5、旧 PG 或 test release 基础设施仍有外部 `BLOCKED`。该结论不是 release approval。
- 任一本地 MUST 为 `FAIL`/`NOT RUN`，或证据/owner 不完整时，不得声称本地加固完成。
- Production 始终为 `DEFERRED`；OPS2 控制面 API/UI 与 OPS3 production 同 digest 晋级属于 Batch 62/63。
