# Bug 模式详解（成因 · 案例 · 修法）

> 蒸馏自 memory `[[common-pitfalls]]`、`[[bugfix-20260708-swagger-import-duplicate-discovery]]`、`[[react-effect-hygiene-rules]]` 与 `work-logs/` 修复记录。每条：**现象 → 根因 → 修法 → 自检**。SKILL.md 是快查清单，本文件是「为什么」。

---

## 后端

### B1. 静态路径段被路径参数遮蔽（→ 422）

- **现象**：`PUT/DELETE /test-cases/batch` 返回 422。
- **根因**：FastAPI 按注册顺序匹配；`@router.put("/{case_id}")` 注册在 `/batch` 之前，`/batch` 命中 `/{case_id}`，`"batch"` 解析为 int 失败。
- **修法**：把所有静态段（`/batch`、`/domains`、`/export` …）整块移到同前缀的 `/{id}` 路由**之前**。
- **自检**：新增带静态子路径的路由后，肉眼确认它在 `/{...}` 之上。

### B2. 请求链路里重复的非幂等网络调用（Swagger 导入报错的主因）

- **现象**：Swagger URL 导入报 `无法解析 OpenAPI 文档`。
- **根因**：`import_preview → discover_spec_urls()`（展示用）→ `_resolve_spec → discover_spec_urls()`（下载用）**探测两遍**；每遍 12+ HTTP 请求，第二遍因网络抖动可能返回空 → `None` → 通用错误。
- **修法**：`_resolve_spec` 改为接受 `spec_url: str | None`，外层把第一次发现结果传入，消除内层重复调用。
- **自检**：任何网络 I/O 函数若可能被多处调用，检查是否在同一链路被执行两次。一次请求 = 一次探测 + 一次下载。

### B3. Alembic 迁移重复加列 / from-base 打断

- **现象**：`alembic upgrade head` 报 `duplicate column name`（如 `imported_func_count`、`template_id`）。
- **根因**：dev 用 `AUTO_CREATE_TABLES=true`（`create_all`）建表，长期没人从 base 跑全链；某迁移重复 ADD 初始 schema 已有的列。ORM 模型漏声明该列时，还会出现「迁移在、模型不在」的错位。
- **修法**：新建加列迁移前 `ls alembic/versions/` 搜列名；用 `alembic upgrade <prev>:<new> --sql` 离线校验单步 DDL，或独立临时库验证，别拿 dev 库跑 upgrade/downgrade。
- **自检**：迁移正确性绝不以 dev 库跑通为准（其 `alembic_version` 常落后于实际表结构）。

### B4. httpx 异常捕获顺序 + 降级分类

- **根因**：`TimeoutException < TransportError < RequestError < HTTPError`。先捕获父类会把超时误判为 network。
- **修法**：`except httpx.TimeoutException` 写在 `except httpx.HTTPError` 之前。`_call_ai_api` 返回 `failure_kind`，让上层区分瞬时（timeout/network → 可降级本地兜底）与契约破损（parse/config → detailed raise，保存原始响应）。
- **自检**：降级前问自己「这是基础设施抖动，还是对方格式变了？」后者不该被静默降级掩盖。

### B5. envelope 码约定

- **约定**：查不到 → service 返回 `R(code=404)` = **envelope code 404 + HTTP 200**；`delete_*` 是硬删。
- **修法/自检**：断言写 `resp.status_code==200 and resp.json()["code"]==404`，别写 `status_code==404`。参照 `test_testcase.py::test_delete_case`。

---

## 前端

### F1. React 副作用四铁律（2026-07-08 刷新后 20+ 重复请求复盘）

根因是三层叠加：StrictMode ×2 + useCallback 循环依赖 cascade + N+1 eager loading + 全量 tab 挂载。

1. **cleanup**：
   ```tsx
   useEffect(() => {
     let cancelled = false
     fetchData().then(d => { if (!cancelled) setData(d) })
     return () => { cancelled = true }   // 或 AbortController
   }, [dep])
   ```
   canonical 的 StrictMode 修法还包括在 cleanup 里 `didInitialFetch.current = false`，允许重新挂载时重新 fetch（见 `useApi.ts`）。
2. **无循环依赖**：useCallback 依赖数组不放该 callback 内部会 SET 的 state；一次性自动选择用 `useRef` 守卫。
3. **无 N+1**：列表计数走后端 GROUP BY，前端列表接口直接返回 count 字段。
4. **TabsContent 条件渲染**：`forceMount` + `{activeTab==='x' && <Comp/>}`。
- **自检**：提交前 DevTools Network 刷新页面——每个 GET 在 StrictMode 下 ≤2 次（含 1 次 cancelled），生产构建严格 1 次；无 `page_size=1` 探针。

### F2. Axios 拦截器漏 `detail`

- **根因**：拦截器只读 `err.response?.data?.msg`，但 FastAPI `HTTPException(detail=...)` 返回 `{"detail":"..."}` → 用户看到通用「网络错误」。
- **修法**：错误链 `msg || detail || message`。后端每新增返回字段，前端同步检查提取链。

### F3. Radix Select 空值 sentinel

- **根因**：Radix Select 不支持空字符串 value。
- **修法**：用 `'__none__'` sentinel 映射 `undefined`，显式转换。**永远别用 `''` 或 `0` 做空值**。

### F4. API 面三层 / 孤儿组件

- **根因**：`template_service.py` 有完整 CRUD、model+schema 也在，但 `router.py` 从未注册模板路由 → 前端 404。另：`TemplateManager.tsx` import 了 `@/api/report` 里不存在的函数，被 tsconfig exclude 掩盖编译错误。
- **修法**：新功能逐层确认 router → service → model 全链贯通；新组件先补依赖 API 再写，或 exclude 时注释 `// TODO: waiting on API X`。

---

## 测试基础设施与契约漂移（2026-07-09 大修复）

背景：`conftest` 的 `client`/`auth_headers` 夹具曾全线失败，掩盖了大量下游漂移；修好后第二波真实失败才浮现。全套件 166 passed/10 failed/1 error → 175 passed/0 failed。

### T1. in-memory SQLite 缺 StaticPool

- **根因**：`create_engine("sqlite:///:memory:")` 缺 `poolclass=StaticPool`，TestClient 请求线程与测试线程各拿一个空 `:memory:` 库 → `no such table: sys_user`。
- **修法**：`from sqlalchemy.pool import StaticPool` 并传入。或新写测试自带 StaticPool 引擎 + `app.dependency_overrides[get_current_user]` 直接注入 `CurrentUser` 绕过登录（见 `tests/test_knowledge.py` 的 `kdb`/`kclient`）。

### T2. 登录响应体漂移

- **根因**：契约是 `LoginOut.access_token`（不是 `token`），`MeOut` 把用户嵌在 `data.user` 下。旧测试仍取 `data["token"]`/`data["username"]`。
- **修法**：断言对齐真实契约（同 `test_auth.py`）。缺 seed 用户时补 `admin_user` 夹具（声明即 seed，与 `client` 共享同一 in-memory `db_session`）。

### T3. TestClient cookie 持久化污染鉴权回退测试

- **根因**：login 下发的 cookie 被 TestClient 持久化；后续即使带 Authorization 头，`get_current_user` 仍优先用 cookie（`used_fallback=False`）→ 「弃用告警」断言失败。**端点行为正确，别改断言**。
- **修法**：login 后 `client.cookies.clear()` 隔离出纯 Authorization 头场景。

### T4. pytest 误采集 `test_` 前缀导入 / 脚本式 import 断言

- **根因**：`from ...service import test_connection` 把业务函数以 `test_` 名导入 `test_*.py` → 被当测试无参调用 → ERROR。另有整文件是 import 期硬断言的脚本式 smoke，未实现特性断言失败会**中断整个套件采集**。
- **修法**：import 别名 `test_connection as _test_connection`；未实现段加特性存在性守卫（`if "template_id" in ReportCreate.model_fields and hasattr(TestReport, "template_id")` 否则 `[SKIP]`），不掩盖也不擅自实现。

### T5. 判定「测试陈旧 vs 端点真 bug」

- **原则**：夹具修好后暴露的失败，先分类再改。示例：登录响应体漂移=陈旧（改测试）；批量路由被 `/{id}` 遮蔽=端点 bug（改路由，见 B1）；`POST /test-plans/{id}/execute` 404=陈旧（真实端点是 `/auto-execute`，无客户端用 `/execute`，改测试而非加无人用的别名）。
- **协作**：契约漂移类问题可**自主连续修复**，修完一个接着下一个不逐个询问（见 `[[feedback-autonomous-drift-fixing]]`）。

---

## 依赖 / 环境

### D1. 隐式依赖未声明（PyYAML）

- **根因**：`openapi_import_service.py` 用 `yaml.safe_load()` 但 `requirements.txt` 缺 `pyyaml`；本地恰好装过不报错，新环境部署才暴露。
- **修法**：新增 `import` 立即加进 `requirements.txt`（`pyyaml>=6.0`）；CI 在隔离 venv 里 `pip install -r requirements.txt && pytest` 兜底。

### D2. 其它已知点

- APScheduler 在 `--reload` 多 worker 下重复启动 → `main.py` 加 `if scheduler.state == 0` 判断。
- SQLite WAL 支持并发读但写串行；高并发写考虑 PostgreSQL。
- CORS 本地 `allow_origins=["*"]`；生产 CORS 由 Nginx 处理，后端不配。
- v1/v2 端口冲突（都 8000/5173），不要同时启。
