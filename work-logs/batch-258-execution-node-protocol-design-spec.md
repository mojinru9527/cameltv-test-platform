# Batch 258 — Design Spec

> **Design (🎨)** | Date: 2026-09-18 | Status: 就绪

## 0. 技术体系确认

后端：FastAPI + SQLAlchemy 2.0（`Mapped`/`mapped_column`）+ Alembic；统一响应信封 `R.ok` / `R(code=…)`。
前端（仅 B1-6）：shadcn/ui + Radix + Tailwind + CVA，Token 走语义类（`bg-muted` / `text-muted-foreground` / `border` / variant）；
细节走 `cameltv-ui-conventions`。

本批以**模块/接口契约**为主，UI 面只有 B1-6 一处，按 §2 给出四态。

## 1. 模块与接口规格表

### 1.1 新增：`app/core/url_guard.py`（B1-1 唯一入口）

| 符号 | 契约 | 失败模式 |
|------|------|---------|
| `class UrlNotAllowedError(ValueError)` | 守卫拒绝的统一异常 | — |
| `resolve_addresses(host, port) -> set[ip_address]` | 解析全部 A/AAAA；解析失败 → 拒绝 | `UrlNotAllowedError("无法解析目标主机")` |
| `assert_public_url(url, *, allow_private=False) -> str` | 校验 scheme ∈ {http,https}；有 hostname；无 username/password；端口合法；每个解析地址 `is_global` | 逐条给可读中文原因 |
| `assert_public_url_after_redirect(base_url, location) -> str` | `urljoin` 后复用 `assert_public_url` | 同上；用于逐跳二次校验 |
| `parse_http_url(url) -> SplitResult` / `effective_port(parsed) -> int` | 供需要自行编排请求的链路复用同一套解析（如带 Header 的抓取） | 同上 |
| `resolver` 注入参数 | `assert_public_url(..., resolver=...)`：离线单测与「已解析地址复用」用，避免二次 DNS 探测 | — |

**关键决策**：不新建第二套 IP 判定。`outbound_policy` 的 `resolve_addresses` / `validate_outbound_url` **迁移**到
`url_guard`，`outbound_policy` 改为 `from app.core.url_guard import ...` 并保留 `validate_outbound_url` 同名别名，
使既有调用点（`app/api/v1/apitest_assets.py:17`）与既有测试 `tests/test_outbound_policy.py` 零改动通过。
`url_guard` **不导入 settings**（保持纯函数、可离线测），响应体上限仍由 `outbound_policy` 的
`settings.outbound_max_response_bytes` 承担。

### 1.2 配置项（`app/core/config.py`，B1-1/B1-2/B1-3）

| 键 | 默认 | 用途 |
|----|------|------|
| `outbound_max_response_bytes` | `10 * 1024 * 1024`（既有） | 响应体硬上限；本批把需求抓取接入 |
| `requirement_lanhu_domains` | `"lanhuapp.com"` | 蓝湖识别根域 |
| `requirement_pingcode_domains` | `"pingcode.com"` | 可接收 PingCode 令牌的根域 |
| `requirement_confluence_domains` | `"atlassian.net"` | 可接收 Confluence 令牌的根域 |

匹配规则：`host == pattern or host.endswith("." + pattern)`（均为小写、去首点、逗号分隔可配多值）。
**禁止**子串匹配——`pingcode.attacker.tld` 必须不命中。

### 1.3 `app/services/requirement_source_service.py`（B1-1 / B1-2）

| 函数 | 变更后契约 |
|------|-----------|
| `classify_url(url)` | 白名单根域匹配 → `lanhu|pingcode|confluence`；未命中 → `generic`；空/非法 → `RequirementSourceError(kind="input")` |
| `_request(url, *, headers=None)` | 出网前 `assert_public_url(url)`；`follow_redirects=False`，手动逐跳（`assert_public_url_after_redirect`）≤ `settings.outbound_max_redirects`；流式读取并在 `settings.outbound_max_response_bytes` 处截断报错；`RequirementSourceError(kind="guard")` |
| `fetch_url_content(url, *, kind=None)` | 行为不变；令牌只在 `kind in {pingcode, confluence}` 时注入（结构上保证 H3） |

`httpx.TimeoutException` 的 `except` 仍**先于** `httpx.HTTPError`（bug-guard 铁律），新增的守卫异常在两者之前抛出。

### 1.4 `app/services/lanhu_evidence/local_ocr_provider.py`（B1-3）

| 步骤 | 契约 |
|------|------|
| 模板解析 | `shlex.split(template)`，其中 `{python}` / `{image}` 先用**哨兵 token**（`__CAMELTV_PYTHON__` / `__CAMELTV_IMAGE__`）占位 |
| 回填 | 把哨兵的 argv 元素替换为真实路径（**不经过 shell**），保证含空格/`;` 的路径是单一 argv |
| 调用 | `run_process(argv, shell=False, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)` |

**为什么必须哨兵**：若先 `.replace("{image}", path)` 再 `shlex.split`，`/tmp/a b.png` 会被切成两个 argv，
命令语义变形；哨兵法把「分词」与「插值」解耦。

### 1.5 `ExecutionJob` 协议（B1-4，接口面）

| 方法/路径 | 契约 |
|-----------|------|
| `POST /api/v1/execution-jobs` | 登记任务：`kind(api|web)`, `case_refs[]`, `env_ref`, `project_id` |
| `POST /api/v1/execution-jobs/claim` | 认领：仅取本项目、`pending` 或租约过期者；返回租约 `expires_at` |
| `POST /api/v1/execution-jobs/{id}/heartbeat` | 续租；非持有节点 → 404（不泄露存在性） |
| `POST /api/v1/execution-jobs/{id}/report` | 上报结果 + `evidence_bundle_id` |
| `POST /api/v1/execution-jobs/reclaim-stale` | 回收过期租约 → 回 `pending`，`attempt += 1` |

权限点独立（不复用 `uitest:trigger`），节点令牌按项目隔离（H5）。

**与方案 §3.2 的一处刻意偏离（需 Leader 复核）**：方案的数据模型表把 `JobLease` 列为独立对象，
但同一行的说明是「沿用 `AiJob` 的 claim/heartbeat/stale 语义」——而 `AiJob` 的租约**就是**
`locked_at`/`heartbeat_at`/`agent_id` 三个内联字段，并无独立租约表。
本批选择**内联**：`execution_jobs.node_id / claimed_at / lease_expires_at / heartbeat_at`。
理由：同一份租约两处记账正是 Batch 240–255 清理过的「双栈漂移」成因；独立租约表要到 B4
需要"租约历史"证据链时才有增量价值，届时可另加 `job_lease_events` 追加式表，而不必拆分现有真源。
若 Leader 判定必须独立成表，属可回退的设计变更（迁移已支持 downgrade）。

## 2. 状态设计核对（四态，B1-6 节点状态）

| 状态 | 触发 | 呈现 |
|------|------|------|
| Loading | 首次拉取节点状态 | 骨架占位，不显示「无节点」误判 |
| Empty / 离线 | 在线节点数 = 0 | 明确文案「本地节点未连接」+ 一键启动指引（`cameltv-node up` 命令可复制） |
| Error | 拉取失败 | 错误文案 + 重试；走 `msg \|\| detail \|\| message` 提取链 |
| 在线 | ≥1 节点在线 | 在线数 + 队列长度 + 最近心跳时间 |

刷新：轮询间隔须使「节点上线 → 状态更新」≤10s（backlog B1-6 DoD）；`useEffect` 必须带 cleanup。

## 3. 设计 QA 走查发现（P0–P3，均附文件:行号）

### 🔴 P1-1 用户可控 URL 出网无守卫，且守卫件就在隔壁没用
`app/services/requirement_source_service.py:77-91` 的 `_request()` 只校验 scheme，`follow_redirects=True` 且无字节上限；
而 `app/core/outbound_policy.py:47-72` 已有完整实现且被 `app/api/v1/apitest_assets.py:17` 正常使用。
→ **建议**：抽 `app/core/url_guard.py` 作为唯一入口，需求抓取逐跳校验并限流读取（Task 1/2）。

### 🔴 P1-2 令牌按域名子串外发
`app/services/requirement_source_service.py:66-74`：`if "pingcode" in host` 命中即 `Bearer`。
→ **建议**：根域白名单 + 解析 IP 校验；非白名单回落 generic 从而不带 Header（Task 3）。

### 🔴 P1-3 OCR 命令经 shell 拼串
`app/services/lanhu_evidence/local_ocr_provider.py:74` `shell=True`，`{image}` 直接插值。
→ **建议**：哨兵 + `shlex.split` + `shell=False`（§1.4）。

### 🟠 P2-1 错误分类缺「被守卫拒绝」这一类
`RequirementSourceError.kind` 现有 `input/timeout/network/http/parse/auth/lanhu_gate`，
守卫拒绝若复用 `network`，前端只能显示「网络错误」，与 bug-guard「降级要分类」冲突。
→ **建议**：新增 `kind="guard"`，文案指向「该地址不允许访问（内网/非法地址）」。

### 🟡 P3-1 节点状态页缺失，首页在无节点时无任何提示
平台当前无「执行节点」概念页（grep `NodeRegistration` 无结果），页面无法回答「为什么点了没反应」。
→ **建议**：B1-6 按 §2 四态实现，且承诺必须配可执行校验（bug-guard 规则 4）。

## 4. 设计签核

结论：**通过**（P1-1/P1-2/P1-3 即本批 Task 1–4 的交付内容，不构成阻断项；P2-1/P3-1 已纳入本批）。
