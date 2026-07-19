---
name: cameltv-bug-guard
description: 编码或改测试平台代码前的避坑清单，防止重复触发历史 Bug。Use before writing/reviewing backend (FastAPI/SQLAlchemy/Alembic) or frontend (React/TS) code in test-platform-v2/, when adding routes, migrations, network calls, tests, or dependencies, and when debugging "导入报错/重复请求/422/404/测试全挂/deploy 缺依赖". Triggers: "避坑", "会不会踩到老 bug", "写接口/迁移/测试前检查", "bug guard".
---

# CamelTv 避坑守卫（Bug Guard）

历史上反复触发的 Bug 都收敛成了「铁律」。**动代码前先扫对应区块；改完按对应自检项验证。** 详细成因与真实案例见 [PATTERNS.md](PATTERNS.md)。

## 后端（FastAPI / SQLAlchemy / Alembic）

- [ ] **静态路径段必须先于同前缀路径参数注册**：`/batch`、`/domains` 一律写在 `/{id}` 之前，否则 `PUT /x/batch` 命中 `/{id}` → `"batch"` 解析 int 失败 → 422。
- [ ] **同一请求链路里，非幂等网络操作只做一次**：SSRF 探测 / API 发现（`discover_spec_urls()`）等，外层拿到结果用参数传给内层，禁止内层再发一遍（双倍探测 + 结果抖动不一致 → 业务失败）。
- [ ] **加列迁移前先搜是否已存在**：`ls alembic/versions/` 搜列名再决定是否新建；dev 用 `AUTO_CREATE_TABLES` 建表会掩盖「迁移在、模型不在」的错位，导致 `duplicate column`。
- [ ] **迁移用 `--sql` 或独立临时库离线校验单步 DDL**，别拿 dev 库（`alembic_version` 常落后于实际表结构）跑 from-base。
- [ ] **`httpx.TimeoutException` 的 except 必须先于 `httpx.HTTPError`**（前者是后者子类），否则超时被误分类为 network。
- [ ] **降级要分类**：只对瞬时失败（timeout/network）降级到本地兜底；契约破损（parse/config）仍走 detailed raise，别把「AI 返回格式变了」静默降级掩盖真 bug。
- [ ] **envelope 码 vs HTTP 码**：本仓约定「查不到 → `R(code=404)` + HTTP 200」。删除是硬删；断言别写 `status_code==404`，应写 `status_code==200 && json()["code"]==404`。

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
- memory `[[common-pitfalls]]` `[[react-effect-hygiene-rules]]` `[[code-review-checklist]]` `[[bugfix-20260708-swagger-import-duplicate-discovery]]`
- `cameltv-agent-team` skill — Dev 编码前的强制一环；`cameltv-ui-conventions` skill — UI 侧红旗
