# Batch 243 — PM Plan

> **PM (🟨)** | Date: 2026-09-14

## 规格摘要

**原始需求**：执行完整平台审计后的第一阶段安全边界修复，覆盖 P0 RCE/SSRF 以及 P1 reset token、HTML 安全头、固定后端路由、代理 IP、请求体上限。  
**目标时间**：一个完整 Agent Team 批次；按可独立验证的安全切片推进。

## 开发任务

### [ ] Task 1: 执行器权限与子进程环境隔离
**描述**：新增 `uitest:code_execute` 权限；Playground 直接执行和自定义 spec 的创建/更新/触发改为该权限；新增执行器 env 清洗与 POSIX 资源限制辅助模块，替换 `os.environ.copy()`。
**验收标准**：
- 默认 tester 访问 `/api/v1/playground/execute` 被拒绝。
- 子进程 env 不含 `SECRET_KEY`、数据库密码、AI/LANHU 凭据。
- 现有合法 runner 测试保持通过。
**涉及文件**：
- `test-platform-v2/backend/app/core/config.py`
- `test-platform-v2/backend/app/core/deps.py`
- `test-platform-v2/backend/app/core/execution_sandbox.py`（新增）
- `test-platform-v2/backend/app/api/v1/playground.py`
- `test-platform-v2/backend/app/api/v1/ui_test.py`
- `test-platform-v2/backend/app/services/playground_service.py`
- `test-platform-v2/backend/app/services/playwright_executor.py`
- `test-platform-v2/backend/app/seed.py`

### [ ] Task 2: 统一出站 URL 策略并修复 OpenAPI 导入 SSRF
**描述**：新增出站策略模块，校验 scheme、host、DNS 全量地址、私网/保留地址、重定向和响应体上限；OpenAPI 导入改用该模块。
**验收标准**：
- 私网、loopback、链路本地、保留地址和重定向到私网均拒绝。
- 合法公网 URL 正常读取。
- 超限响应返回可读业务错误，不无限读取。
**涉及文件**：
- `test-platform-v2/backend/app/core/config.py`
- `test-platform-v2/backend/app/core/outbound_policy.py`（新增）
- `test-platform-v2/backend/app/api/v1/apitest_assets.py`
- `test-platform-v2/backend/tests/test_outbound_policy.py`（新增）
- `test-platform-v2/backend/tests/test_apitest_assets_security.py`（新增）

### [ ] Task 3: reset token 真实过期与一次性语义
**描述**：让 token 创建支持独立 expiry；reset token 绑定 `pwdv` 和 `jti`；重置时行锁校验并在改密后使 token 失效。
**验收标准**：
- token 寿命为 30 分钟。
- 同一 token 第二次重置失败。
- password-reset token 仍不能访问业务 API。
**涉及文件**：
- `test-platform-v2/backend/app/core/security.py`
- `test-platform-v2/backend/app/api/v1/auth.py`
- `test-platform-v2/backend/tests/test_auth_reset_security.py`（新增）

### [ ] Task 4: 代理 IP、请求体上限与安全头
**描述**：明确 Uvicorn 可信代理配置；全局中间件按实际接收字节做上限；Nginx 增加安全头、固定后端路径并外置主题 bootstrap。
**验收标准**：
- 无 `Content-Length` 的 chunked 超限请求返回 413。
- Nginx 静态 HTML/资源有 CSP、HSTS、X-Frame 等头。
- `/health` 返回 JSON，`/openapi.json`、`/docs`、`/redoc` 正常代理或明确关闭。
**涉及文件**：
- `test-platform-v2/backend/app/main.py`
- `test-platform-v2/backend/app/core/config.py`
- `test-platform-v2/backend/Dockerfile`
- `test-platform-v2/deploy/docker-compose.yml`
- `test-platform-v2/frontend/index.html`
- `test-platform-v2/frontend/public/theme-bootstrap.js`（新增）
- `test-platform-v2/frontend/nginx.conf`
- `test-platform-v2/frontend/security-headers.conf`（新增）
- `test-platform-v2/frontend/Dockerfile`
- 对应测试

## 质量要求

- [x] 响应式（本批不改变业务布局）
- [x] OpenAPI 同步（用户可见权限/错误不破坏 schema）
- [x] 单元测试覆盖（安全策略、reset、middleware、Nginx 契约）
- [x] 无障碍（主题脚本外置不改变 DOM 语义）
- [x] 无 console 报错/告警
- [x] 不夹带第二阶段 typed client / 第三阶段 UI 重构
