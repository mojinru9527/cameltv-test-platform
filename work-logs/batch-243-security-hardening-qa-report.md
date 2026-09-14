# Batch 243 — QA Report
> **QA (🔍)** | Date: 2026-09-14 | Verdict: PASS

## 测试总览

| 条件数 | 通过 | 失败 | 阻塞 |
|--------|------|------|------|
| 5 | 5 | 0 | 0 |

## 可执行门禁

| 检查 | 命令 | 结果 |
|------|------|------|
| Backend import | `python -c "import app.main"` | ✅ app-import-ok |
| Backend F821 | `ruff check app --select F821` | ✅ All checks passed |
| Backend security targeted | 新增安全测试 + auth/playground/runner/RBAC 回归 | ✅ 22/22 security；87/87 相关回归；34/34 runner/UI 回归 |
| Backend full | `pytest -q` | ✅ 2670 passed, 51 skipped, 1 xfailed in 645.75s |
| Frontend typecheck | `NODE_OPTIONS=--max-old-space-size=4096 npm run typecheck` | ✅ |
| Frontend lint | `NODE_OPTIONS=--max-old-space-size=4096 npm run lint` | ✅ |
| Frontend build | `NODE_OPTIONS=--max-old-space-size=4096 npm run build` | ✅ 3671 modules transformed |
| Frontend full | `NODE_OPTIONS=--max-old-space-size=4096 npm test -- --maxWorkers=2` | ✅ 159 files / 698 tests passed |
| G0 common bugs | `scripts/git/scan-common-bugs.ps1` | ✅ HARD=0；WARN=331（存量，不属于本批回归） |
| Compose contract | `docker compose config --quiet` | ✅ compose-config-ok |
| Frontend image | `docker build .../frontend/Dockerfile` | ✅ image built |
| HTML header smoke | Nginx container + `Invoke-WebRequest` | ✅ CSP/HSTS/X-Frame present；`theme-bootstrap.js` 200 |
| Backend api image | `docker build --target api` | ⚠️ Docker daemon unavailable during local retry；CI required backend build job仍会执行 |

## 逐条件验证

### C1: 用户 Playwright 执行边界

- 新增 `uitest:code_execute`，默认 tester 不授予该权限。
- `playground/execute`、自定义 UI job create/update/trigger 已改走新权限；前端按钮同步按该权限显示。
- Playwright/UI Runner 子进程使用最小环境，不再继承 `SECRET_KEY`、数据库、AI 或蓝湖凭据。
- POSIX 资源限制已接入；Compose backend/runner 继承 `cap_drop: ALL`、`no-new-privileges` 和 PIDs 限制。
- Chromium 在 `--cap-drop ALL --security-opt no-new-privileges` 容器参数下启动成功。
- 证据：`test_execution_sandbox.py`、`test_playground_security.py`、`test_rbac_project_roles.py`、`test_playwright_executor.py`。

### C2: OpenAPI URL SSRF

- 新增出站策略：scheme、用户信息、端口、DNS 全地址、私网/保留地址、重定向和响应体上限。
- OpenAPI URL 导入已切换到策略化读取，策略错误以 400 业务错误返回。
- 证据：`test_outbound_policy.py`、`test_apitest_assets_security.py`、`test_apitest_assets.py`。

### C3: reset token

- token 显式 30 分钟过期，不再沿用 access-token 的 24 小时默认值。
- token 绑定密码版本；成功重置后旧 token 因密码版本变化不可重放。
- 行锁避免并发双消费。
- 证据：`test_auth_reset_security.py`、`test_forced_password_change.py`。

### C4: HTML 安全头与固定路由

- 主题 bootstrap 已外置为 `public/theme-bootstrap.js`，支持严格 `script-src 'self'`。
- Nginx 对首页、静态资源和主题脚本注入 CSP/HSTS/X-Frame/nosniff/Referrer/Permissions Policy。
- `/health`、`/openapi.json`、`/docs`、`/redoc` 已显式反代，不再被 SPA fallback 吞掉。
- 证据：`test_security_contract.py`、前端镜像构建、容器 header smoke。

### C5: 请求体上限

- ASGI 中间件同时检查声明长度和实际 streamed bytes。
- 上传接口改为 `read(limit + 1)`，避免检查前无限读取。
- 证据：`test_request_size_middleware.py`、上传相关既有测试。

## 缺陷列表

| # | 严重级 | 描述 | 证据 | 状态 |
|---|--------|------|------|------|
| 1 | P3 | 前端既有测试仍输出 act/NaN/Select warning，均为主干存量测试告警，与本批功能失败无关 | 前端全量测试 stderr | 记录，后续治理批次处理 |

## 发布建议

状态：READY（代码与本地 required 门禁通过）。  
合并前置：用户一次总确认；PR required checks 全绿；最终 `audit-ai-pr.ps1 -RequireSuccessfulChecks` 通过。

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 18h planned | 0/0/0/1 | 2 | 资源适配 + 测试契约从内联脚本迁移到外置脚本 | Batch 开工即固定环境、权限和测试路径基线 |

**技能使用**：`cameltv-agent-team`、`cameltv-bug-guard` → 六部门流水线、路由/副作用/安全契约核查。
