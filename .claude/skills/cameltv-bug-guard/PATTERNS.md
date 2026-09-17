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

---

## 出网与执行安全（2026-09-18 两次全量审计新增）

> 口径：对比 main `10e69b36`（Batch 255 前）与 `96cd5b65`（Batch 255）两次全量审计。
> 下面 S1–S6 在**两版都存在**，说明它们不是"某次疏忽"，而是流程没覆盖到——
> 所以固化成铁律，而不是等下一次审计再发现。

### S1. 用户可控 URL 出网没有 SSRF 守卫

- **现象**：需求「URL 导入」可以把内网服务、`127.0.0.1`、云元数据（`169.254.169.254`）的响应抓回来，
  存进需求文档并在页面展示（可回读）。
- **根因**：`requirement_source_service._request()` 只校验 `scheme`，随后 `httpx.get(..., follow_redirects=True)`；
  代码库里其实**已有** `_validate_url_no_ssrf()`（`api_execution_service.py`），但需求抓取这条路没复用。
- **修法**：抽出共享的 `assert_public_url(url)`；校验原始地址 + 每个重定向目标；限制响应体大小；解析后用 `ipaddress` 判定私网/回环/链路本地。
- **自检**：任何"用户填 URL → 服务端去拉"的功能，先问三个问题：私网能打吗？重定向能绕吗？响应有上限吗？

### S2. 凭据按"域名关键字"判定可信来源

- **现象**：`classify_url()` 用 `"pingcode" in host` / `"atlassian"/"confluence" in host` 判定供应商，
  然后把 `PINGCODE_API_TOKEN` / `CONFLUENCE_API_TOKEN` 作为 `Authorization: Bearer` 发出去。
- **根因**：把"像供应商"当成"是供应商"；主机名匹配没有锚定根域，也没有校验解析后的 IP。
- **修法**：白名单配置化（根域精确匹配或后缀匹配 + `.` 边界），并对解析 IP 做私网校验；
  凭据只发给白名单内的 host，其余走"通用无凭据抓取"。
- **自检**：凡是"认证信息 + 用户输入地址"同时出现，先确认地址是否可能由攻击者控制。

### S3. `shell=True` + 模板插值

- **现象**：本地 OCR 命令模板 `lanhu_ocr_command.replace("{image}", image_path)` 直接进 `shell=True`。
- **根因**：图省事的字符串模板；路径含空格/`;`/`&&` 时命令会变形甚至注入。
- **修法**：`shlex.split(template)` → 参数数组；`{image}` 作为独立 argv 元素；或改用内置 RapidOCR（Batch 247 已引入）不再走外部命令。
- **自检**：`rg "shell=True"` 结果必须为空，或每处都有明确豁免理由。

### S4. 文件路径拼接未收敛到基目录

- **现象**：`LocalStorage._path()` 用 `os.path.normpath(os.path.join(base_dir, rel))`，`rel` 里的 `../` 可以逃出 `base_dir`。
- **根因**：`normpath` 只做规范化，不做边界检查；`make_uri` 也只替换反斜杠。
- **修法**：与 `app/api/v1/lanhu_evidence_assets.py` 的写法对齐——`Path(...).resolve()` 后 `is_relative_to(base)`，不满足直接 403/异常。
- **自检**：新增任何"上传/导出/取证/下载"落盘逻辑时，同时写一条越过 `..` 的测试。

### S5. 密钥加密出现两套派生实现

- **现象**：`cipher.py` 用 `settings.effective_secret_key`（dev 会自动生成随机会话密钥），
  `ai_config_service._fernet()` 用 `settings.secret_key`。SECRET_KEY 为空时后者对空串做 sha256 → 等价公开常量密钥。
- **根因**：两处各自实现 Fernet 派生，没有单一入口。
- **修法**：全部改调 `cipher.py`；启动时若"没有 SECRET_KEY 但库里已有密文"直接 fail-fast；轮换 SECRET_KEY 必须同时提供重加密脚本。
- **自检**：`rg "sha256\(.*secret_key"` 只应命中 `cipher.py` 一处。

### S6. 把 `--dry-run` 当沙箱

- **现象**：用例编译链路把 `npx tsc --noEmit` + `npx playwright test --dry-run` 称为"sandbox 校验"，
  计划执行路径甚至 `validate=False` 直接执行 LLM 生成的 spec。
- **根因**：Playwright 的 dry-run 仍会**加载并执行 spec 模块的顶层语句**，只能查语法/收集结构，不能阻止 `child_process`/`fs`。
- **修法**：危险 API 静态拦截（`child_process`/`fs`/`net`/`process.env`）+ 独立无凭据沙箱容器执行；把"dry-run ≠ 沙箱"写进设计说明。
- **自检**：任何"生成代码 → 落盘 → 执行"的链路，先确认执行环境的 secret/卷/网络三件事。

### S7. 静默吞异常与异常链丢失（长期不降）

- **现象**：`except Exception: pass/continue` 11 + 7 处；`raise ...` 缺 `from err` 32 处（比上一版还多 4 处）。
- **根因**：为了"不阻断主流程"就地兜底；缺少"兜底也要留痕"的默认动作。
- **修法**：兜底一律 `logger.warning/debug(..., exc_info=True)`；重新抛错统一 `raise X(...) from err`；
  前端禁止裸 `.catch(() => {})`（至少 `console.warn` 或注明刻意静默的理由）。
- **自检**：`ruff check app/ --select S110,S112,B904` 的数量只能下降，不能上升。

### S8. 类级可变默认值（RUF012）

- **现象**：18 处（比上一版 +3），集中在 `services/sync/*.py`、`smart_regression/service.py`。
- **根因**：用 `X: dict[str, str] = {}` 表达类级配置，实例间共享同一个对象。
- **修法**：改 `ClassVar[...]` 标注（表达"就是类级常量"）或 `field(default_factory=...)`。
