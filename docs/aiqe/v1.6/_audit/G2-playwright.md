# V16-002 独立审计报告（G2）：Playwright 全请求链 TargetPolicy 拦截

- 审计 Issue：**V16-002 / AUD-001：Playwright 未拦截请求（P0）**
- 规格：《CamelTv AIQE V1.6 修复与生产化开发实施计划》第 272–308 行（V16-002），并参照 0.1 / 0.2.3 / 0.2.4 / 0.2.8、V16-016（Web/Playwright 边界）、TC-AIQE-003 / TC-AIQE-005
- 仓库：`F:\CamelTv-worktrees\DeepSeek_Harness-aiqe-v1-6`
- 分支：`release/aiqe-v1-6`；HEAD：`86a44b2cbb7c9c44d3ef6af1e324d1f42c3eae6f`
- 审计时间：2026-11-19T19:04:44+08:00
- 审计方式：只读代码；未修改任何业务文件，唯一写入为本报告。

## 0. 审计口径与工作树状态（重要）

1. **工作树有在途改动（V16-001），本报告基于审计时刻的工作树快照，而非 HEAD 提交。**
   `git status --short` 在审计时刻为 24 项未提交（初始 14 项，审计过程中继续增长，新增 `scripts/qa/aiqe_local_runner.py`、`app/api/v1/execution_jobs.py` 等）。这些改动属于 V16-001（`target_policy.py` 新增 `PolicyDecision`/`resolve_execution_policy`/`from_snapshot`、`node_executor.execute_node` 改为必填 `policy_context`、`PlaywrightDriver` 构造改为必填 `policy`）。
2. **为避免行号漂移，本报告对关键文件记录了 SHA256 快照**；若审计后文件再被并行修改，请以 hash 对齐后再复核行号：

| 文件 | 字节 | SHA256 |
|---|---|---|
| `test-platform-v2/backend/app/aiqe/drivers/playwright_driver.py` | 28285 | `A13C7DC06C25473D30DEC9CD3940B0C07E324A8D638810B67262797F505085D5` |
| `test-platform-v2/backend/app/aiqe/services/node_executor.py` | 30014 | `AAB249D85D3843372C6755A6CB90063A3366C2E795900EE857234E122A8E5483` |
| `test-platform-v2/backend/app/aiqe/security/target_policy.py` | 25892 | `32F11C05EBA145A0D3B93DC6EA71F8CD35298B5D98BFC487FB3E76A394197697` |
| `scripts/node/cameltv_node/drivers/playwright_driver.py` | 8152 | `8EDE3AF45425DAAAC8EFDBEB9107D95F02B1171201095D1B2AFD40CC86F894C9` |
| `scripts/node/cameltv_node/executor.py` | — | `A547738C7383F1A2B12C6977C4594AFAC3414B571E50B3EB640B9345C4BC7DF7` |

3. **判定口径**：只以代码行证据判定，不凭类名/文件名/文档声明。规格 0.2.3 明确"Mock 不能替代本次 Issue 要证明的核心组件"；0.2.8 明确"只直接调用内部 Driver/helper""用 Mock Driver 证明真实 Driver 可用"均不得作为证据。
4. **本 Issue 不涉及数据库结构变更**：规格未要求新增表/列，仓库也无对应 alembic 迁移；`resolved_addresses` 等字段属于 V16-001 的策略快照，本报告只在"浏览器是否消费这些字段"范围内核对。
5. **范围说明**：AIQE 浏览器节点在生产链路上的实际执行者是 `scripts/qa/aiqe_local_runner.py`（外部 Runner CLI）→ 后端 `node_executor.execute_node()` → 后端 `PlaywrightDriver`。`scripts/node/cameltv_node` 是另一套执行器（API 用例 / `/uitest` Playwright spec），其 `drivers/playwright_driver.py` 当前无任何调用方（仅测试用 `importlib` 加载），但同样属于"Runner 内可启动 Chromium"的路径，纳入 G7。

## 1. 总体结论

| Issue | 状态 | 一句话结论 |
|---|---|---|
| **V16-002** | **MISSING** | 只有"非 ALLOW 策略不启动浏览器"这一个入口闸门（由在途 V16-001 提供）；**V16-002 定义的三层防护全部未实现**：应用层主导航 URL 校验 0 行、浏览器层 `context.route` 0 行、网络层 egress 只有离线 WSL2 证据且未在任何 Runner/容器落地。 |

**为什么不是 PARTIAL**：V16-002 的安全属性是"每一个主请求与子请求都被策略复核"。代码中对 `route` / `route_web_socket` / `service_workers` / `popup` / URL 规范化 / DNS / redirect 复核 / `blocked_cidrs` 的引用数为 **0**（见 §7 命令）。唯一已实现的是构造签名与"决策非 ALLOW 即 BLOCKED"，它属于 V16-001 的 fail-closed 范畴，且对"ALLOW 策略 + 未授权目标"完全不设防（G2）。因此不能判 PARTIAL、更不能判 IMPLEMENTED。

### 1.1 分项状态

| 规格项 | 状态 | 依据（详见 §2/§3） |
|---|---|---|
| 目标架构层 1：应用层主导航 URL 由服务端 SafeTargetValidator 校验 | **MISSING** | `_execute_playwright` 只检查 url 非空（`node_executor.py:533-541`），不调用 `SafeTargetValidator` |
| 目标架构层 2：`context.route("**/*")` 逐请求拦截 | **MISSING** | `playwright_driver.py:148-175` 创建 context 后直接 `new_page()`；全仓 `app/aiqe` 无 `route` |
| 目标架构层 3：Runner egress deny-by-default | **PARTIAL（仅证据，未落地）** | `docs/aiqe/evidence/runner-egress/` 有 WSL2 一次性实验与 `policy.json`；compose/CI 无任何 egress 配置；`approved_by: null` |
| 实施步骤 1：构造函数接收 ResolvedExecutionPolicy、移除 Workflow `allowed_hosts` | **IMPLEMENTED（在途补丁）** | `playwright_driver.py:119-130`；`node_executor.py:542-546` |
| 实施步骤 2：创建 Context 后、任何 Page 前安装 route handler | **MISSING** | `playwright_driver.py:161-170` |
| 实施步骤 3：每次请求 URL 规范化（scheme/host/port/userinfo/punycode/尾点/数字 IP/IPv4-mapped/zone id，拒绝非 HTTP(S)） | **MISSING** | 浏览器路径无任何规范化；可复用的 `safe_target.normalize_host`（`safe_target.py:112-138`）未接入 |
| 实施步骤 4：服务端 DNS A/AAAA 全量解析 + 短时缓存 + egress 二次约束 | **MISSING** | 浏览器由 Chromium 自行解析；无 `host-resolver-rules`/代理；`resolved_addresses` 声明但从未赋值（`target_policy.py:180,308`） |
| 实施步骤 5：每个 redirect 重新校验 | **MISSING** | `page.goto` 由 Playwright 自动跟随；`max_redirects`/`allow_cross_host_redirect` 对浏览器无效 |
| 实施步骤 6：WebSocket / Service Worker / 下载 / 弹窗 / iframe 不可绕过 | **MISSING** | 无 `route_web_socket`、`new_context` 未设 `service_workers="block"`/`accept_downloads=False`、无 popup 处理 |
| 实施步骤 7：拦截行为写安全审计事件（Run/Node/Request ID、规范化目标、策略 hash、拒绝原因，不含敏感头/query） | **MISSING** | 浏览器分支无事件；`security.target_policy_denied` 只在 HTTP secure 路径（`node_executor.py:375-391`） |
| 实施步骤 8：默认拒绝 loopback/link-local/private/multicast/reserved/unspecified/元数据，禁止 Workflow 开 `allow_private` | **PARTIAL** | 策略侧有 `DEFAULT_BLOCKED_CIDRS` 与 `allow_private_cidrs`（`target_policy.py:40-50,163-164`），但浏览器路径从不读取这些字段；Workflow 输入已无法直接授权（由 V16-001 入口拦截） |
| 测试矩阵 8 条（主请求放行 / 302 到私网 / iframe 等子请求 / DNS 混合 / DNS 变更 / WebSocket / 弹窗 / 断言目标零命中） | **MISSING（0/8）** | 无任何真实 Chromium 安全测试；driver 单测全部 `FakePage` |
| 验收：真实 Chromium Runner + 本地受控 HTTP/DNS fixture | **MISSING** | 见 §5；后端 CI 未安装 Chromium（`main-quality-gate.yml:181-187`） |
| 验收：Runner egress 测试报告归档 | **PARTIAL** | 证据已归档（`docs/aiqe/evidence/runner-egress/`），但非实际 Runner、无浏览器流量、未审批、未进 CI |

## 2. 关键证据（文件相对路径:行号）

### 2.1 浏览器路径没有 route、没有逐请求校验

1. `test-platform-v2/backend/app/aiqe/drivers/playwright_driver.py:148-175` — `start()` 依次 `sync_playwright()` → `chromium.launch(headless=...)` → `browser.new_context(viewport=..., ignore_https_errors=False)`（161-164）→ `tracing.start`（166）→ `context.new_page()`（170）→ 只注册 `console/pageerror/request/response` 被动监听（171-174）。**创建 context 后没有任何 `context.route(...)`，也没有 `route_web_socket`、`service_workers="block"`、`accept_downloads=False`。**
2. `test-platform-v2/backend/app/aiqe/drivers/playwright_driver.py:220-247` — `_on_request` / `_on_response` 仅把 method/url/resource_type/status 追加到 `self._network`（上限 200 条），**是旁路日志，不是拦截器**：不 abort、不 continue、不判定。
3. `test-platform-v2/backend/app/aiqe/drivers/playwright_driver.py:275-294` — `perform()` 对 `navigate|goto` 直接 `self._page.goto(action.url, wait_until="domcontentloaded", timeout=...)`（289-294），入参 URL 原样交给浏览器，**没有 scheme/host/port/IP 判定**。
4. `git grep -n "\.route(\|route_web_socket\|service_workers"` 限定 `test-platform-v2/backend/app/aiqe`、`scripts/node/cameltv_node`、`scripts/qa` 结果为 **0 命中**（exit 1）。仓库内 `page.route` 只出现在 `test-platform-v2/backend/tests/playwright/specs/*.spec.ts`，用途是 **stub 外部接口让 UI 冒烟稳定**，不是安全门禁。

### 2.2 入口只校验"是不是 TargetPolicy"，不校验"目标是否被授权"

5. `test-platform-v2/backend/app/aiqe/services/node_executor.py:518-546` — `_execute_playwright()` 的校验只有两件事：`isinstance(policy_context, TargetPolicy)`（526-532）与"url/actions 非空"（533-541）；随后直接 `PlaywrightDriver(policy=policy_context)` 构造（542-546）并 `driver.execute(spec_input)`（548）。**`policy_context.allowed_hosts` / `allowed_ports` / `blocked_cidrs` / `allow_private_cidrs` 一次都没有被读取。**
6. `test-platform-v2/backend/app/aiqe/services/node_executor.py:104-179` — `_policy_denial()` 对 `TargetPolicy` 只判 `decision is ALLOW` 与 `expires_at` 过期（137-159），**不判目标**。浏览器分支（484-488）复用它，因此"ALLOW 即放行任意目标"。
7. `test-platform-v2/backend/app/aiqe/drivers/playwright_driver.py:128-130,529-542` — `self.policy` 仅在 `execute()` 里用于判断 `decision is not ALLOW`；`allowed_hosts` 在整个 driver 中只出现在第 129 行的注释里（`git grep -n "allowed_hosts"` 该文件仅命中注释）。
8. 可复核的绕过场景（静态可证）：策略 `TargetPolicy(decision=ALLOW, allowed_hosts=("example.com",), allowed_ports=(443,))` + Workflow 节点 `{"driver":"playwright","url":"https://evil.test/"}` → `execute_node` 放行 → `_execute_playwright` 放行 → `driver.execute` 放行 → `page.goto("https://evil.test/")`。没有任何一行代码会拒绝。

### 2.3 策略里的目标约束字段在浏览器路径上全部失效

9. `test-platform-v2/backend/app/aiqe/security/target_policy.py:149-180` — `TargetPolicy` 定义了 `allowed_hosts`(160)、`allowed_ports`(161)、`allow_private_cidrs`(163)、`blocked_cidrs`(164)、`decision`(175)、`resolved_addresses`(180)；`allows_host()` 在 267-273。**这些能力只被 HTTP 侧消费**（`safe_target.py:169-257`、`safe_http.py:135-154`）。
10. `test-platform-v2/backend/app/aiqe/security/target_policy.py:180,308` — `resolved_addresses` 只出现在字段声明与 `snapshot()` 输出，`resolve()`/`from_mapping()` 从不赋值（`from_mapping` 只映射 allowed_hosts/ports/schemes/cidrs/methods/limits，314-352），因此策略快照里的 `resolved_addresses` 永远是 `()`——"DNS 解析结果进入策略快照"未落地。
11. `test-platform-v2/backend/app/aiqe/security/safe_target.py:112-138` — 仓库里已有完整的 host 规范化（IDNA/punycode、尾点、zone id、`0x`/纯数字/八进制混淆、IPv4-mapped 在 `_unwrap` 96-99），且 `validate()`（169-257）做 scheme/userinfo/port/method/host/全地址校验、`validate_redirect()`（260-279）做逐跳复核。**浏览器路径没有复用这些实现**，属于"能力已存在但未接线"。

### 2.4 事件与证据

12. `test-platform-v2/backend/app/aiqe/services/node_executor.py:181-197,334-391` — `_emit_security_event()` 已存在，但只在 `_execute_http_secure()` 内被调用（347-353 `security.policy_override_ignored`、375-391 `security.target_policy_denied`）。**浏览器分支没有任何安全事件调用点**。
13. `test-platform-v2/backend/app/aiqe/services/execution_service.py:573-631` — 非 ALLOW 决策会由 `_block_node_for_policy()` 写 `security.target_policy_denied|unavailable|missing_binding`（595-598）并写入 policy hash/version。**这只能覆盖"整条策略不可用"，覆盖不了"ALLOW 但某个子请求越权"**——而后者正是 V16-002 的验收对象。
14. `test-platform-v2/backend/app/aiqe/drivers/playwright_driver.py:166,520-527` — `tracing.start(screenshots=True, snapshots=True, sources=True)` 会把页面/网络上下文写入 `trace.zip`，`capture_evidence` 原样作为 Artifact 返回；而 `network.json` 本身不含 headers（这是对的），**但 trace 不受 route 约束、也没有 header/Secret 过滤**（与 V16-003 的"trace 假 sanitized"交叉，见 `execution_service.py` 的 `_upload_binary_artifact` 逻辑）。

### 2.5 Egress 只有离线证据

15. `test-platform-v2/deploy/docker-compose.yml:154-176` — `runner` 服务 `extends: backend`，只有 `cap_drop`、`mem_limit`、`pids_limit`、`security_opt`、healthcheck、restart；**没有 `networks:` / `network_mode` / 内部网络 / egress 代理**。`git grep -n "network_mode\|networks:\|internal:"` 对该文件 0 命中。
16. `docs/aiqe/evidence/runner-egress.md:6-14` — 明确写"当前 Runner 主机没有'出站 allowlist'，因此不能声称已限制外联"；第 53-56 行的方式 B 才要求"生产在云安全组/NACL 落地"。
17. `docs/aiqe/evidence/runner-egress/policy.json:1-33` — `default_action: deny`、只允许 `192.168.50.170:443`、DNS、loopback；`approved_by: null`，notes 自述"生产需在云安全组/NACL 落地同一 allowlist"。
18. `test-platform-v2/backend/scripts/aiqe/verify_runner_egress_wsl.sh:1-71` — 手工脚本（需 root、`iptables -F OUTPUT` + `-P DROP`、`trap` 恢复），探针只有 `curl` 与 `python socket`，**不启动 Chromium**；allowlist 由命令行参数传入，**不读取 `policy.json`**；脚本不在 `.github/workflows` 中（`git grep -nw "egress"` 于 workflows 为 0 命中）。
19. `docs/aiqe/runner-deployment.md:143-145` — 文档声称"Runner 出站只放行平台、被测环境、对象存储与 DNS"，但引用的是上述离线证据，**没有可执行/可校验的落地物**（compose、systemd、SG 导出均无）。

### 2.6 Runner 侧的第二套浏览器实现

20. `scripts/node/cameltv_node/drivers/playwright_driver.py:28-77` — 该 `PlaywrightDriver` 构造函数**没有 policy 参数**，`start()` 同样 `new_context()`（69-72）→ `tracing.start`（73）→ `new_page()`（74），无 route；`goto()`（107-111）直接执行。全仓库 `PlaywrightDriver(` 仅 5 处：后端 driver、后端 `node_executor`、两个测试、该文件 docstring —— 即该驱动当前无生产调用方（仅 `test_aiqe_playwright_driver.py` 用 `importlib` 加载）。
21. `scripts/node/cameltv_node/executor.py:274-300` — `_default_page_factory()` 自行 `sync_playwright().start()` → `chromium.launch()` → `new_context()` → `new_page()`，**无策略、无 route**；`run_web_cases()`（303）用它执行 Workflow web 用例。
22. `scripts/node/cameltv_node/executor.py:501-580` — `run_spec_files()` 直接 `npx playwright test`（574-580）在 Runner 主机上跑任意 spec 文件，同样不受任何 route/egress 约束。这两条路径说明"Runner 上可发起任意浏览器流量"的实现不止一处。

## 3. 差异项（Gaps，逐条可验证）

> 排序：G1–G6 为 V16-002 关闭必须项；G7–G8 为同源风险与测试/CI 缺口。

### G1（P0，核心）浏览器层零拦截
**差异**：`BrowserContext` 创建后未安装 `route("**/*")` / `route_web_socket("**/*")`，也未设置 `service_workers="block"`、`accept_downloads=False`、popup 处理器。主请求、iframe、图片、脚本、字体、XHR/fetch、WebSocket、Service Worker、弹窗、下载全部按浏览器默认行为直连。
**验证**：`playwright_driver.py:161-175`；`git grep -n "\.route(\|route_web_socket\|service_workers" -- test-platform-v2/backend/app/aiqe scripts/node/cameltv_node scripts/qa` → 0 命中。
**后果**：规格目标架构第 2 层完全缺失，测试矩阵 8 条中 6 条（302/iframe/DNS 混合/DNS 变更/WebSocket/弹窗）在实现上不可能通过。

### G2（P0）应用层不校验主导航，ALLOW 策略可导航到任意主机
**差异**：`_execute_playwright` 只判 `isinstance(TargetPolicy)` 与 URL 非空；`allowed_hosts`/`allowed_ports` 未被消费；`page.goto` 直接使用 Workflow 提供的 URL。
**验证**：`node_executor.py:526-546`；`playwright_driver.py:128-130,289-294`；`git grep -n "allowed_hosts" -- test-platform-v2/backend/app/aiqe/drivers/playwright_driver.py` 仅命中注释。
**后果**：只要项目有一条 ALLOW 策略（哪怕 `allowed_hosts=("example.com",)`），任何域名/公网 IP 都能被浏览器访问。这是本 Issue 最直接的 fail-open。

### G3（P0）redirect / WebSocket / DNS / 非 HTTP(S) scheme 无任何处理
**差异**：`page.goto` 默认跟随 302/307；无逐跳 URL 复核、无跨主机策略、`max_redirects` 不生效；Chromium 自行解析 DNS，无 `--host-resolver-rules`、无 egress 代理、无 `pinned_dns` 等价物；`file://`/`data:`/`blob:`/`ftp:` 等 scheme 未拒绝（`page.goto("file:///...")` 可读取本机文件）。
**验证**：`playwright_driver.py:289-294`；`target_policy.py:149-180` 的 `max_redirects`/`allow_cross_host_redirect` 在 driver 中 0 引用；`git grep -n "host-resolver-rules\|proxy" -- test-platform-v2/backend/app/aiqe/drivers/playwright_driver.py` → 0。

### G4（P1）策略目标约束与 DNS 快照字段在浏览器路径上不可审计
**差异**：`resolved_addresses` 从未赋值；`blocked_cidrs`/`allow_private_cidrs` 不被浏览器读取；没有"本次导航用了哪个策略版本/hash、解析到哪些地址"的节点级证据。
**验证**：`target_policy.py:180,308`（仅声明与输出，无赋值点）；`node_executor.py:576` 返回的 `detail` 只有 driver 结果，无策略快照；`execution_service.py:765` 只写 `policy` 快照（不含解析地址）。

### G5（P1）无浏览器侧安全审计事件
**差异**：规格要求"Run/Node/Request ID、规范化目标、策略 hash、拒绝原因"事件，且不得记录 Authorization/Cookie/敏感 query。当前浏览器路径没有任何拒绝事件；即便未来加 route，也缺少事件模型与 request id。
**验证**：`node_executor.py:181-197`（函数仅被 347/375 调用，均在 HTTP 分支）；`execution_service.py:594-631` 只覆盖"整条策略非 ALLOW"。

### G6（P0）egress 未在 Runner/容器落地，只有离线证据
**差异**：compose 无网络限制；无防火墙/代理落地脚本接入部署；WSL2 脚本为一次性手工实验（root、flush OUTPUT、不跑浏览器、不读 `policy.json`、不进 CI）；`policy.json` 未审批；文档把"应放行"写成"已放行"。
**验证**：`docker-compose.yml:154-176`；`runner-egress.md:6-14`；`policy.json:29-33`；`verify_runner_egress_wsl.sh:1-71`；`git grep -nw "egress" -- .github/workflows` → 0。
**后果**：规格"即使浏览器层漏拦也不能访问云元数据或内网"的兜底层不存在；TC-AIQE-003/005 的"请求未抵达目标服务器"外部证据无法产生。

### G7（P1）Runner 内存在第二/第三套无策略浏览器入口
**差异**：`scripts/node/cameltv_node/drivers/playwright_driver.py`（无 policy、无 route）与 `executor.py::_default_page_factory`/`run_spec_files`（无 policy、无 route，`npx playwright test`）都能在 Runner 主机发起任意浏览器流量。前者当前为死代码，后者是 `/uitest` 正式执行路径。
**验证**：`scripts/node/cameltv_node/drivers/playwright_driver.py:28-77,107-111`；`scripts/node/cameltv_node/executor.py:274-300,501-580`；`git grep -n "PlaywrightDriver(" -- .` 仅 5 处、该文件无导入方。
**后果**：只修后端 `PlaywrightDriver` 不能闭合"Runner 内浏览器不能访问未授权目标"，egress 层必须覆盖同一台主机上的全部 Chromium 进程。

### G8（P0，验收）测试与 CI 完全未覆盖
**差异**：无任何真实 Chromium + 本地受控 HTTP/DNS fixture 的测试；driver 单测全部 `FakePage`；唯一的 dispatch 测试 `monkeypatch` 掉了被验证函数；新增的 `execute()` 策略闸门 0 测试；后端 CI 未安装 Chromium；egress 脚本不在 CI。
**验证**：`tests/test_aiqe_playwright_driver_v2.py:217-229`（`playwright_factory=FakeCM(...)`）；`tests/test_aiqe_ui_device_executor.py:64-75`（`monkeypatch.setattr(node_executor, "_execute_playwright", ...)`）；`tests/test_aiqe_playwright_driver_v2.py` 全文无 `.execute(` 调用；`.github/workflows/main-quality-gate.yml:181-187`（后端仅 `pytest -q`）、`:262-265`（Chromium 只在前端 job 安装）。

## 4. 已存在测试与入口质量

| 测试 | 覆盖内容 | 入口 | 是否能证明 V16-002 | 问题 |
|---|---|---|---|---|
| `tests/test_aiqe_playwright_driver_v2.py`（312 行，6 个用例） | 真实 click / probe 分离 / locator 断言 / 点击拦截分类 / 证据文件 | 直接构造 `PlaywrightDriver`，`FakePage`/`FakeContext`/`FakeBrowser` | ❌ | 无 route、无 URL 策略、无 DENY 策略、无 `execute()`；假浏览器 |
| `tests/test_aiqe_playwright_driver.py`（219 行，5 个用例） | Runner 副本驱动的 login/证据/异常/关闭/trace | `importlib` 加载 `scripts/node/cameltv_node/drivers/playwright_driver.py` | ❌ | 该驱动无 policy；测试本身也在固化"无策略驱动可用" |
| `tests/test_aiqe_ui_device_executor.py:64-75` `test_playwright_is_dispatched` | 断言 browser driver 被分发 | `execute_node(node, policy_context=_allow_policy())` | ❌ | **`monkeypatch` 掉 `_execute_playwright`**，等于用 Mock 替代被验证链路；规格 0.2.8 明令禁止 |
| `tests/test_aiqe_ui_device_executor.py:78-98` | 浏览器不可用 → BLOCKED；缺 URL → FAILED；`ExecutionCapabilities.NONE` → BLOCKED | 直调 `_execute_playwright()`（helper 级） | ⚠️ 仅证明入口拒绝 | 未覆盖 ALLOW 但目标未授权；未经过 Worker/Job |
| `tests/test_aiqe_v16_001_policy_fail_closed.py`（427 行） | Worker 入口无策略/异常/过期 → BLOCKED；私网/元数据 HTTP 节点拒绝 | `job_consumer.run_job()` 正式 Worker | ⚠️ 对 V16-001 有效 | 全部 `driver="http"`；**没有一条 playwright 用例** |
| `tests/test_aiqe_aud001_target_policy.py` | SafeTargetValidator/SafeHttpExecutor 的 redirect、DNS 重绑定、混淆 IP、私网拒绝 | 直调 helper / MockTransport | ❌ 对浏览器无效 | 证明的是 HTTP 层能力，未接到浏览器 |
| `tests/e2e/aiqe/test_tc_aiqe_001_010.py` | 10 个 TC 共用 `goto /runs` + `body.count()==1` | 真实 Chromium，但无 `AIQE_E2E_BASE_URL` 时全 skip | ❌ | 规格 0.2.8 明确"相同页面打开断言冒充多个场景"不算；TC 编号语义还与 V1.6 的 TC-AIQE-003 不一致 |
| `tests/test_aiqe_playwright_mcp_explorer.py` | Explorer allowlist/动作记录 | `FakeDriver` | ❌ | 只校验首个 URL，且 allowlist 由调用方传入；非生产 driver |
| `tests/test_aiqe_local_runner_resolver.py` / `_heartbeat.py` | 变量解析/心跳 | `importlib` 加载 Runner 脚本 | ❌ | 不执行 `run_once()`，不启动浏览器 |

**入口质量结论**：不合格。
1. **没有一条测试从"API → Run → Job → Worker/Runner → PlaywrightDriver → 目标服务器"进入**；浏览器节点在正式 Worker 中根本不会被认领（`job_consumer.py:30-32` 的 `INPROCESS_DRIVERS` 不含浏览器 driver），正式入口是手工 CLI `scripts/qa/aiqe_local_runner.py`，而它没有自动化测试。
2. 现有浏览器测试**全部替换了被验证组件**（FakePage / `monkeypatch` `_execute_playwright` / FakeDriver），恰好绕开"route 拦截 + 目标校验"。
3. 没有"目标服务器收到 0 个请求"的断言，也没有真实 Chromium / 真实 DNS fixture。
4. `execute()` 中新增的策略闸门（`playwright_driver.py:529-542`）没有任何测试覆盖。

## 5. 最小整改建议（文件/函数级，不含补丁代码）

> 原则：复用 `app/aiqe/security/safe_target.py` + `target_policy.py`，不在 Driver 内新建第二套出网判定（`security/__init__.py:1-3` 已把这条写成包契约）。

### R1（P0）浏览器层：在 `start()` 内、`new_page()` 前安装拦截器
- 文件：`test-platform-v2/backend/app/aiqe/drivers/playwright_driver.py`，函数：`PlaywrightDriver.start()`
- `browser.new_context(...)` 增加 `service_workers="block"`、`accept_downloads=False`；禁止 `ignore_https_errors=True`。
- 在 `new_page()` 之前注册 `context.route("**/*", handler)` 与 `context.route_web_socket("**/*", handler)`；`page.on("popup")` 中对新页面同样校验（context 级 route 可覆盖 popup，但必须显式断言）。
- handler 内部：`SafeTargetValidator.validate(request.url, policy, method=request.method)`（复用 `safe_target.py:169-257`）；失败 `route.abort("blockedbyclient")`，成功 `route.continue_()`；对 `data:`/`blob:` 仅允许作为文档内子资源（按策略显式开关），其余非 http(s) 一律 abort。
- 每次 abort 生成结构化事件（见 R3）。
- 明确"Chromium DNS 不由 Python 解析"：必须选择其一并在代码注释中写明：①`chromium.launch(args=["--host-resolver-rules=MAP host ip, ..."])` 配合服务端 `resolved_addresses`；②统一经本地 egress 代理（见 R4）。仅依赖 `pinned_dns` 对 Chromium 子进程无效。

### R2（P0）应用层：主导航先校验，再创建 Driver
- 文件：`app/aiqe/services/node_executor.py`，函数：`_execute_playwright()`
- 在 `PlaywrightDriver(...)` 之前，对最终导航 URL（`spec_input["url"]` 与 `actions` 中第一个 `navigate|goto` 的 `url`）调用 `SafeTargetValidator().validate(url, policy_context, method="GET")`；失败返回 `BLOCKED/TARGET_POLICY_DENIED` 并调用 `_emit_security_event(..., "security.browser_navigation_denied", {...})`。
- `_execute_playwright` 只接受 `decision is ALLOW`（当前仅 `isinstance` 检查，依赖 `execute_node` 的前置门；直接调用该 helper 时可绕过）。
- 驱动构造函数中把 `policy.decision`、`policy_hash`、`version`、`expires_at` 固化到实例，`perform()` 入口再判一次；`start()`/`perform()` 需要外部不可直接调用的护栏（例如内部 `_started_with_authorization` 标志），避免"绕过 `execute()` 直接 `perform()` 导航"的分支。

### R3（P1）审计事件
- 新增 RunEvent：`security.browser_request_denied`（字段：`run_id`/`node_run_id`/`request_id`/`normalized_target`/`scheme`/`host`/`port`/`resource_type`/`policy_hash`/`policy_version`/`reason_code`/`decision`），**不得**包含 Authorization/Cookie/query 值；复用 `node_executor._safe_url_for_event()`（`node_executor.py:200-224`）的规范化规则。
- 事件发出点：R1 handler、R2 主导航校验、R4 网络层（若有代理日志）。

### R4（P0）网络层：把 egress 变成可部署、可测试的制品
- `test-platform-v2/deploy/docker-compose.yml:154`（runner 服务）：改为独立 `networks: [runner-egress]`（`internal: true`）+ 允许出口的代理 sidecar，或提供 host 级 iptables/nftables 渲染脚本。
- 新增"由 `docs/aiqe/evidence/runner-egress/policy.json` 生成实际规则"的脚本（当前 `verify_runner_egress_wsl.sh` 用命令行参数、与 policy.json 无关联），并做 `policy.json` 与生成规则的 hash 对账。
- `policy.json` 补 `approved_by` 与审批时间；`runner-deployment.md:143-145` 的"已放行"措辞改为引用实际落地物。
- 新增 CI job（Linux runner）跑"允许目标 200 / 未授权 `example.com`、`169.254.169.254` 超时"并归档 iptables 与探针日志；**必须包含一条 Chromium 探针**（`page.goto("http://169.254.169.254/")` 必须失败），否则只证明 curl 被拦。

### R5（P1）统一浏览器入口
- 删除或改造 `scripts/node/cameltv_node/drivers/playwright_driver.py`（当前无调用方、无策略），避免"第二套无策略驱动"被误用。
- `scripts/node/cameltv_node/executor.py::_default_page_factory` / `run_spec_files`：至少纳入同一 egress 命名空间/代理；若 `/uitest` 不在 V16-002 范围，必须在 V16-016 Capability/边界文档中显式声明其残余风险，不能默认"Runner 已被 egress 保护"。

### R6（P0）必须新增的负向测试（建议 `tests/aiqe/test_v16_002_browser_target_policy.py`）
> 全部使用**真实 Chromium** + 本地 `ThreadingHTTPServer`/受控 DNS fixture；只允许 Mock"平台 API"（外部系统），**不得 Mock `PlaywrightDriver`、`route`、`node_executor` 或目标服务器**。每条都要断言"被拒目标服务器 hit count == 0"。

1. 正向：ALLOW（`allowed_hosts=["127.0.0.1"]`、`allowed_ports=[<port>]`、`allow_private_cidrs=["127.0.0.0/8"]`）→ 导航成功、hit==1、节点 PASSED。
2. 主机白名单：ALLOW（`allowed_hosts=["allowed.test"]`）+ 实际 `http://127.0.0.1:<port>/` → BLOCKED、hit==0（证明 allowed_hosts 真正被浏览器路径消费）。
3. 302：允许主机 302 → `http://127.0.0.1:<port>/secret` → 阻断；第一跳 hit==1、第二跳 hit==0；`max_redirects=0` 时第一跳即拒。
4. 私网/元数据矩阵：`127.0.0.1`、`10.0.0.5`、`172.16.3.4`、`192.168.1.9`、`169.254.169.254`、`[::1]`、`[fe80::1]`、`[::ffff:127.0.0.1]`、`2130706433`、`0177.0.0.1`、`0x7f.0.0.1`、`127.0.0.1.` → 全部 BLOCKED、所有 fixture hit==0。
5. 子请求：页面含 `<iframe src>`、`<img>`、`<script src>`、`fetch()` 指向私网 fixture → 全部阻断（每个 fixture 端点 hit==0），同时页面主文档仍成功（证明不是"整页失败"造成的假绿）。
6. WebSocket：`ws://127.0.0.1:<port>` → 阻断；断言服务端从未收到 Upgrade。
7. 弹窗：`window.open("http://127.0.0.1:<port>/")` → 新页面被拒；hit==0。
8. DNS：fixture 同时返回公网+私网 → 拒绝；首次公网、二次私网的 rebinding → 第二次拒绝或 egress 阻断；hit==0。
9. 非 HTTP(S)：`file:///etc/hosts`、`data:text/html,<script>` → BLOCKED/`SCHEME_NOT_ALLOWED`；无本地文件读取证据。
10. 决策负向：`DENY` / `UNAVAILABLE` / `MISSING_BINDING` / 已过期 → 通过 `job_consumer.run_job()`/`execute_inprocess_job()` 断言 BLOCKED、`chromium.launch` 调用计数 0、目标 hit==0、事件 `security.target_policy_*` 存在。
11. 审计事件：上述任一拒绝都产生含 `policy_hash`/`policy_version`/`normalized_target`/`reason_code` 的事件，且事件 payload 中不含 Authorization/Cookie/query 值。
12. Egress：在受控网络命名空间/容器内，允许 fixture 可达、`example.com:443` 与 `169.254.169.254:80` 超时，且**用 Chromium 发起** `page.goto` 验证同样失败；归档 iptables-save 与探针日志；在 CI 中执行。

### R7（P0）CI
- `.github/workflows/main-quality-gate.yml` 后端 job 增加 Chromium 安装（`python -m playwright install --with-deps chromium`），并新增独立 `aiqe-browser-security` job 跑 R6；失败阻断 required check。
- 后端 `pytest -q` 已覆盖 `tests/`，但安全用例需要 Chromium 与本地端口，建议独立 job + 独立 marker，避免拖慢全量。

## 6. 验收标准对照

| 规格验收 | 结论 |
|---|---|
| 所有负向测试使用真实 Chromium Runner + 本地受控 HTTP/DNS fixture | ❌ 不存在任何此类测试 |
| 只 Mock `route` handler 不算通过 | ⚠️ 现状连 route handler 都没有；现有测试用 FakePage 等价于更弱的替代 |
| 断言被阻断的请求未抵达测试目标服务器 | ❌ 无 hit-count 断言 |
| Runner 网络 egress 测试报告必须归档 | ⚠️ 已归档 WSL2 证据（`docs/aiqe/evidence/runner-egress/`），但非实际 Runner、无浏览器、`approved_by: null`、不进 CI；只能算"证据存在"，不能算"验收通过" |

## 7. 可复核命令（PowerShell，仓库根目录执行；不修改文件）

```powershell
cd F:\CamelTv-worktrees\DeepSeek_Harness-aiqe-v1-6

# 0) 基线
git rev-parse HEAD; git status --short | Measure-Object
Get-FileHash test-platform-v2\backend\app\aiqe\drivers\playwright_driver.py -Algorithm SHA256

# 1) 浏览器层零拦截：期望 0 命中（exit 1）
git grep -n "\.route(\|route_web_socket\|service_workers" -- test-platform-v2/backend/app/aiqe scripts/node/cameltv_node scripts/qa
git grep -n "\.route(" -- test-platform-v2/backend/tests/playwright/specs   # 仅 UI 冒烟 stub，反证

# 2) driver 从未消费目标字段：仅命中注释行
git grep -n "allowed_hosts\|allows_host\|SafeTargetValidator\|blocked_cidrs\|allow_private_cidrs\|pinned_dns" -- test-platform-v2/backend/app/aiqe/drivers/playwright_driver.py

# 3) 构造 context 后直接 new_page（无 route 安装点）
Select-String -Path test-platform-v2\backend\app\aiqe\drivers\playwright_driver.py -Pattern "new_context|new_page|tracing.start" -Encoding UTF8

# 4) 入口只判类型，不判目标
Select-String -Path test-platform-v2\backend\app\aiqe\services\node_executor.py -Pattern "def _execute_playwright|isinstance\(policy_context, TargetPolicy\)|PlaywrightDriver\(" -Encoding UTF8

# 5) 安全事件只在 HTTP 分支
Select-String -Path test-platform-v2\backend\app\aiqe\services\node_executor.py -Pattern "_emit_security_event\(|security\." -Encoding UTF8

# 6) 浏览器节点不会被进程内 Worker 认领（浏览器只能走外部 Runner CLI）
Select-String -Path test-platform-v2\backend\app\aiqe\services\job_consumer.py -Pattern "INPROCESS_DRIVERS" -Encoding UTF8

# 7) egress 未落地：compose 无网络限制、CI 无 egress
git grep -n "network_mode\|networks:\|internal:" -- test-platform-v2/deploy/docker-compose.yml
git grep -nw "egress" -- .github/workflows
Get-Content docs\aiqe\evidence\runner-egress\policy.json -Encoding UTF8
Select-String -Path docs\aiqe\evidence\runner-egress.md -Pattern "没有|allowlist|安全组" -Encoding UTF8

# 8) 测试缺口：driver 测试全部 fake；dispatch 测试被 monkeypatch
git grep -n "PlaywrightDriver(\|playwright_factory" -- test-platform-v2/backend/tests
Select-String -Path test-platform-v2\backend\tests\test_aiqe_ui_device_executor.py -Pattern "monkeypatch|_execute_playwright" -Encoding UTF8
git grep -n "\.execute(" -- test-platform-v2/backend/tests/test_aiqe_playwright_driver_v2.py   # 期望 0

# 9) CI 后端未装 Chromium
Select-String -Path .github\workflows\main-quality-gate.yml -Pattern "Backend Full Test Suite|playwright install" -Encoding UTF8

# 10) Runner 侧第二套无策略驱动 / 无策略 npx
Select-String -Path scripts\node\cameltv_node\drivers\playwright_driver.py -Pattern "def __init__|new_context|new_page|policy" -Encoding UTF8
Select-String -Path scripts\node\cameltv_node\executor.py -Pattern "def _default_page_factory|chromium.launch|npx" -Encoding UTF8
```

## 8. 交叉影响与注意事项

1. **与 V16-001 的边界**：`PlaywrightDriver` 的 `policy` 参数与 `execute()` 非 ALLOW 闸门属于在途 V16-001 补丁（工作树未提交）。本报告按"工作树现状"承认该子项，但**不把它算作 V16-002 的拦截能力**；V16-002 关闭必须以 `context.route` + 目标校验 + 真实 Chromium 负向矩阵为准。
2. **与 V16-003 的交叉**：`trace.zip` 由 `tracing.start(screenshots=True, snapshots=True, sources=True)` 生成后原样上传（`playwright_driver.py:166,520-527`），未做 header 过滤；一旦 V16-002 开始记录拦截事件与真实浏览器流量，必须同时确认"审计事件/Artifact 不含 Authorization/Cookie/query"。
3. **与 V16-016/017 的交叉**：V16-016 明确"Web/Playwright 按 V16-002 完成真实请求拦截和证据采集"；TC-AIQE-003/005 的外部证据（"危险目标请求没有抵达目标服务器"）依赖本 Issue 的 route + egress，未完成前这两个 TC 只能是 BLOCKED，不能计入 PASS。
4. **与 H1 沙箱的交叉**：`/uitest` 的 `npx playwright test`（`executor.py:501-580`）在 Runner 主机执行任意 spec，属于 H1 执行隔离范畴；V16-002 的 egress 层必须覆盖"同一主机所有 Chromium 流量"，否则只修 AIQE driver 仍可被 `/uitest` 绕过。
5. **工作树漂移**：审计期间（19:00–19:05）工作树从 14 项未提交增至 24 项，`target_policy.py` 由 571 行增至 628 行（新增 `from_snapshot` 等）。若本报告引用的行号与后续实现不一致，请先按 §0 的 SHA256 对齐；**建议 V16-002 整改开始前先冻结 commit，避免再次出现"审计对象与实现对象不一致"**。
6. **无迁移/无前端**：本 Issue 不需要 alembic 变更（仓库也没有对应迁移）；`test-platform-v2/frontend/src` 无 `allowed_hosts`/`target_policy` 相关 UI（0 命中），整改集中在后端 Driver/Executor/Runner/部署与 CI。

---

**报告结论**：V16-002 当前为 **MISSING**。V16-002 的 8 个实施步骤中仅第 1 步（构造签名）由在途 V16-001 补丁满足；主导航校验、`context.route`、redirect/WebSocket/DNS/Service Worker/popup 复核、浏览器侧审计事件、Runner egress 落地与真实 Chromium 负向测试矩阵全部缺失。在完成 R1/R2/R4/R6 前，不得把本 Issue 标记为 IMPLEMENTED/VERIFIED，也不得宣称 TC-AIQE-003/005 的"危险目标未抵达"已验收。
