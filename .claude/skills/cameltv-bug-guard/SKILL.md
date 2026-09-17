---
name: cameltv-bug-guard
description: 编码或改测试平台代码前的避坑清单，防止重复触发历史 Bug。Use before writing/reviewing backend (FastAPI/SQLAlchemy/Alembic) or frontend (React/TS) code in test-platform-v2/, when adding routes, migrations, network calls, tests, or dependencies, and when debugging "导入报错/重复请求/422/404/测试全挂/deploy 缺依赖". Triggers: "避坑", "会不会踩到老 bug", "写接口/迁移/测试前检查", "bug guard".
---

# CamelTv 避坑守卫（Bug Guard）

历史上反复触发的 Bug 都收敛成了「铁律」。**动代码前先扫对应区块；改完按对应自检项验证。** 详细成因与真实案例见 [PATTERNS.md](PATTERNS.md)。

## ⚠️ 未关闭的已知风险（审计基线 2026-09-18，main@96cd5b6）

两次全量审计（Batch 255 前的 `10e69b36` 与 Batch 255 的 `96cd5b65`，跨 98 个提交）对比后，
以下问题**两版都在、且不在任何门禁里**。你只要碰到相关文件，就必须顺带修复它，不要只改自己的需求：

| 风险 | 证据位置 | 碰到时该做什么 |
|------|---------|---------------|
| 需求 URL 抓取无 SSRF 守卫（可打内网/云元数据，响应入库可回读） | `app/services/requirement_source_service.py:80`（`_request` 只判 scheme） | 复用 `api_execution_service.py:1163` 的 `_validate_url_no_ssrf`，并对 `follow_redirects` 的最终地址二次校验 |
| 企业 SaaS 令牌按「域名含关键字」外发 | `app/services/requirement_source_service.py:71-75`（`"pingcode" in host` 后带 `Bearer`） | 改配置化域名白名单 + 解析 IP 校验 |
| 本地对象存储路径未收敛到 base 目录 | `app/integrations/object_storage/local.py:24-26`（`normpath(join(base, rel))`） | 与 `app/api/v1/lanhu_evidence_assets.py` 的 `is_relative_to` 写法保持一致 |
| OCR 命令 `shell=True` + `{image}` 未加引号 | `app/services/lanhu_evidence/local_ocr_provider.py:62-74` | 改 `shlex.split` 参数数组，或彻底走内置 RapidOCR |
| 密钥加密两套派生实现（`effective_secret_key` vs `secret_key`） | `app/core/cipher.py:21` vs `app/services/ai_config_service.py:61-62` | 统一走 `cipher.py`；启动时对「无 SECRET_KEY 但已有密文」显式报错 |
| 「`--dry-run` 当沙箱」是失效边界 | `app/services/case_compiler_service.py:290-345`；`test_plan_service._compile_ui_case(validate=False)` | dry-run 仍会执行 spec 顶层语句；执行用户/LLM 产出代码必须进无凭据沙箱容器 |

Playground 的 `uitest:code_execute` 权限门禁（Batch 243 + `tests/test_playground_security.py`）已经修好，**不要回退**：
新增自定义代码执行入口时必须挂 `uitest:code_execute`，不能复用 `uitest:trigger`。

## 后端（FastAPI / SQLAlchemy / Alembic）

- [ ] **静态路径段必须先于同前缀路径参数注册**：`/batch`、`/domains` 一律写在 `/{id}` 之前，否则 `PUT /x/batch` 命中 `/{id}` → `"batch"` 解析 int 失败 → 422。
- [ ] **同一请求链路里，非幂等网络操作只做一次**：SSRF 探测 / API 发现（`discover_spec_urls()`）等，外层拿到结果用参数传给内层，禁止内层再发一遍（双倍探测 + 结果抖动不一致 → 业务失败）。
- [ ] **加列迁移前先搜是否已存在**：`ls alembic/versions/` 搜列名再决定是否新建；dev 用 `AUTO_CREATE_TABLES` 建表会掩盖「迁移在、模型不在」的错位，导致 `duplicate column`。
- [ ] **迁移用 `--sql` 或独立临时库离线校验单步 DDL**，别拿 dev 库（`alembic_version` 常落后于实际表结构）跑 from-base。
- [ ] **`httpx.TimeoutException` 的 except 必须先于 `httpx.HTTPError`**（前者是后者子类），否则超时被误分类为 network。
- [ ] **降级要分类**：只对瞬时失败（timeout/network）降级到本地兜底；契约破损（parse/config）仍走 detailed raise，别把「AI 返回格式变了」静默降级掩盖真 bug。
- [ ] **envelope 码 vs HTTP 码**：本仓约定「查不到 → `R(code=404)` + HTTP 200」。删除是硬删；断言别写 `status_code==404`，应写 `status_code==200 && json()["code"]==404`。
- [ ] **404 双约定（Batch 80）**：**隔离/权限/存在性守卫**（项目不存在、跨项目访问、越权资源）走 HTTP 404 是正确契约（不泄露存在性），测试应断言 `status_code==404`；**业务资源查不到**（用例/环境/报告不存在）走 HTTP 200 + body `code==404`。改测试前先分清属于哪一类，别盲目统一。

## 出网 / 执行 / 凭据安全（2026-09-18 审计新增）

- [ ] **任何由用户提供的 URL 出网前必须过 SSRF 守卫**：只判 `http/https` 不够；私网/回环/链路本地（`169.254.0.0/16`）一律拦；`follow_redirects=True` 时重定向后的最终地址要再校验一次；响应体加大小上限（如 5 MB），别把任意大响应读进内存。
- [ ] **凭据只发给白名单域名**：禁止 `"pingcode" in host` / `"confluence" in host` 这种子串判定，`pingcode.attacker.tld` 会直接收割 Token。白名单写在配置里，并校验解析后的 IP 不在私网。
- [ ] **禁止 `subprocess(..., shell=True)`**；命令模板插值（`{image}` 等）必须走 `shlex.split` + 参数数组，路径含空格和 `;` 时不能变形。
- [ ] **文件路径拼接必须收敛**：`join(base, rel)` 之后 resolve 并断言 `is_relative_to(base)`；本地对象存储、证据包、下载接口全部适用。
- [ ] **执行用户/LLM 产出的代码必须在沙箱里**：独立容器、非 root、无 secret、无持久卷、无内网 egress；`tsc --noEmit` / `playwright --dry-run` 只验证语法，**不是安全边界**（dry-run 仍执行 spec 顶层语句）。
- [ ] **自定义代码执行入口用独立权限点**：`uitest:code_execute`（不要复用 `uitest:trigger`），并保留 `tests/test_playground_security.py` 这类回归。
- [ ] **密钥加密只能有一套派生实现**：以 `app/core/cipher.py`（`effective_secret_key`）为准；换 SECRET_KEY 前先想清楚存量密文怎么办。
- [ ] **限流器别只放进程内存**：登录/注册/开放 API 的阈值在多 worker 下会成倍放宽，若生产多 worker 必须外置（Redis）或明确写「单 worker 约定」。

## 前端（React / TypeScript）

React 副作用四条铁律（违反任一 = Block PR，见 `[[react-effect-hygiene-rules]]`）：

- [ ] **useEffect 含异步必有 cleanup**（`cancelled` 标志或 `AbortController`），防 StrictMode double-invoke 的 race。
- [ ] **useCallback 依赖数组禁止放 callback 内部会 SET 的 state**（循环 cascade），用 `useRef` 守卫。
- [ ] **禁止 N+1 请求**：不在循环里对每个 item 发 count/详情，改后端 GROUP BY 批量返回。禁止 `page_size=1` 探针请求。
- [ ] **TabsContent 必须条件渲染**：`forceMount` + `{activeTab==='x' && <Comp/>}`，否则非活跃 tab 也 mount 并发请求。

其它前端铁律：

- [ ] **Axios 错误提取链必须含 `detail`**：FastAPI `HTTPException` 返回 `{"detail":"..."}`，链写 `msg || detail || message`，否则用户只看到「网络错误」。后端每新增返回字段，前端同步检查提取。
- [ ] **Radix Select 空值用 sentinel**（如 `'__none__'` → `undefined`），**永远别用空字符串或 `0` 做 Select 空值**。
- [ ] **API 面三层都要检查**：router → service → model 每层都到位，别只看 service 存在就以为路由通了（漏注册路由 = 404）。
- [ ] **禁止 `.catch(() => {})` 裸吞错误**：至少 `console.warn`/上报，或写清「静默是刻意的」注释与理由（如健康检查不阻塞主功能）。
- [ ] **首屏数据 effect 也要 cleanup**：`getXxx().then(setState)` 同样要在卸载后停止写状态（`cancelled` 标志），不要只在"看起来异步"的 effect 上加。
- [ ] **孤儿组件**：新组件若 import「规划中但未实现」的 API 函数，会被 tsconfig exclude 掩盖编译错误 → 先补 API 再写组件，或注释 `// TODO: waiting on API X`。

## 测试（pytest / 契约漂移）

- [ ] **in-memory SQLite 夹具必须 `poolclass=StaticPool`**，否则 TestClient 线程与测试线程各拿空库 → `no such table`。
- [ ] **测同一 TestClient 的「无 cookie 鉴权回退/未登录」场景前，先 `client.cookies.clear()`**：login 下发的 cookie 会持久化并静默改变鉴权路径。
- [ ] **`test_*.py` 里 import 任何 `test_` 前缀的业务符号必须别名**（`as _test_x`），否则被 pytest 当测试收集并无参调用 → ERROR。
- [ ] **未实现特性用运行时守卫（`if hasattr/in model_fields`）+ `[SKIP]`，不要模块级硬断言**：import 期断言失败会中断整个套件采集。
- [ ] **测试失败先判定「测试陈旧 vs 端点真 bug」再改**，别盲目改断言掩盖真 bug（登录响应体 `access_token`/`data.user` 漂移属陈旧；批量路由被遮蔽属端点 bug）。契约漂移类可自主连续修复，见 `[[feedback-autonomous-drift-fixing]]`。

## 依赖 / 部署

- [ ] **新增 `import` 立即同步 `requirements.txt`**：本地恰好装过的隐式依赖（如 `pyyaml`）到新环境才暴露。CI 应在隔离 venv 里 `pip install -r requirements.txt && pytest` 兜底。
- [ ] **v1 与 v2 端口冲突**：两后端都 8000、两前端都 5173，别同时启动。

## 环境 / 演示态

- [ ] `/apitest`、`/uitest`、`/special` 三模块已全部对接真实后端引擎（httpx / Playwright / ffprobe，见 `api_execution_service.py:166-177` `playwright_executor.py:245-249` `ffmpeg_service.py:70-71`），**非演示态**。修改前端页面时需确保不破坏与真实后端的契约（API 类型同步、错误提取链等）。
- [ ] 蓝湖 MCP：Cookie 有有效期会过期；Edge CDP 端口 9222 别被占用；缓存基于 `versionId`，内容没更新先查 versionId 是否变。

## 关联

- [PATTERNS.md](PATTERNS.md) — 每条铁律的成因、真实案例与修法
- `work-logs/reviews/2026-09-18-code-audit-baseline.md` — 两次全量审计的对比基线（哪些问题跨 98 个提交仍存在）
- `scripts/git/scan-common-bugs.ps1` — 可自动化避坑项的一键扫描（Batch 76 起，提交前运行；HARD>0 必须处理或注明豁免）
- memory `[[common-pitfalls]]` `[[react-effect-hygiene-rules]]` `[[code-review-checklist]]` `[[bugfix-20260708-swagger-import-duplicate-discovery]]`
- `cameltv-agent-team` skill — Dev 编码前的强制一环；`cameltv-ui-conventions` skill — UI 侧红旗
