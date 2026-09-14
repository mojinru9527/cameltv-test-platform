# Batch 243 — Platform Security Hardening（第一阶段）

> **Product (🟦)** | Date: 2026-09-14 | Status: Approved

## 0. 批次模式

`mode: full`。本批引入新的权限、配置、网络策略、请求体限制和运行器安全边界，命中「新行为/新配置/新接口约束」判定。

## 1. 问题陈述

最新主干的审计与生产响应验证暴露出以下风险：

1. Playground/UI Runner 可在后端执行用户提供的 Playwright TypeScript；子进程继承完整环境变量，存在 RCE、凭据窃取和横向移动风险。
2. OpenAPI URL 导入对用户输入执行 `httpx.get(..., follow_redirects=True)`，没有 SSRF、私网、重定向或响应体上限校验。
3. 密码重置 Token 声称 30 分钟且一次性，实际沿用 24 小时 access-token 生命周期，成功后仍可重放。
4. 生产 HTML 缺少 CSP/X-Frame/HSTS 等浏览器安全头，后端 CSP 只覆盖 API 响应。
5. `/health`、`/openapi.json`、`/docs` 被 SPA fallback 吞掉并返回 `200 text/html`。
6. 请求体上限只信任 `Content-Length`，缺少长度头或分块请求可绕过。
7. 反向代理后的客户端 IP 可能全部成为 Nginx 容器地址，使登录/注册限流和审计失真。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 用户代码执行默认暴露面 | tester 可触发，继承完整 env | 仅 code-execution 权限可触发；子进程 env 最小化 | 本批 |
| OpenAPI URL SSRF 回归 | 私网/元数据/重定向未拦截 | P0 单测覆盖私网、重定向和超大响应 | 本批 |
| reset token 重放 | 成功后仍可继续使用 | 并发/串行重放均失败；30 分钟真实过期 | 本批 |
| 生产 HTML 安全头 | CSP/X-Frame/HSTS 缺失 | 首页、登录页、静态资源均存在规定响应头 | 本批 |
| 固定后端路径 | SPA 200 假健康 | `/health` 返回 JSON；OpenAPI/docs 可按配置访问 | 本批 |
| 请求体绕过 | 无长度头可绕过全局上限 | 实际接收字节计数，超限 413 | 本批 |
| 代理 IP | 可能全部为容器地址 | Uvicorn 信任明确代理网段；真实 IP 进入限流/审计 | 本批 |

## 3. 非目标

- 不在本批完成前端双组件体系迁移（第二阶段/第三阶段）。
- 不在本批完成 OpenAPI typed client 全量替换（第二阶段）。
- 不在本批完成首页信息架构和登录体验重设计（第三阶段）。
- 不在本批把所有 UI/API Runner 拆成独立镜像；本批先完成代码级最小权限、env 清洗、资源限制和默认暴露面收口，容器拆分作为后续条件。
- 不改变业务测试用例执行语义；安全限制失败必须明确报错，不静默降级。

## 4. 用户故事 + 验收标准

- As a 平台所有者, I want 外部注册用户不能直接在后端执行任意 TypeScript, so that 凭据和基础设施不被窃取。
  - Given 默认 tester 角色 / When 调用 Playground execute 或提交自定义 test spec / Then 返回 403。
  - Given 有 code-execution 权限 / When 合法执行 / Then 子进程只收到白名单 env，不包含 `SECRET_KEY` 等敏感变量。
- As a 安全工程师, I want OpenAPI URL 导入受统一出站策略保护, so that SSRF 无法攻击内网和云元数据。
  - Given `http://127.0.0.1`、RFC1918、链路本地或公网重定向到私网 / Then 明确拒绝。
  - Given 合法公网 OpenAPI / Then 正常解析且响应体不超过配置上限。
- As a 忘记密码的用户, I want reset token 只能使用一次且按时失效, so that 邮件泄露后风险可控。
  - Given 成功重置 / When 再次使用同一 token / Then 失败。
  - Given 超过 30 分钟 / Then 失败。
- As a 生产运维人员, I want 固定健康/文档路由和安全头, so that 监控、契约工具和浏览器安全策略真实生效。
- As a 平台用户, I want 反向代理后限流按真实客户端工作, so that 一个用户不会锁死全体用户。
- As a 平台所有者, I want chunked/无长度请求也受实际字节上限约束, so that 内存 DoS 无法绕过。

## 5. 技术考量

- Playwright/UI Runner 仍属于高权限执行面；本批采用“默认拒绝 + 权限隔离 + env 清洗 + 资源限制”的纵深防御，并以测试证明。
- Nginx 的 `add_header` 继承规则要求安全头文件在拥有自有 `add_header` 的 location 中显式 include。
- 外部地址策略必须覆盖 DNS 全量解析和每次重定向，不能只检查首次 URL。
- reset token 用密码版本实现一次性语义需要行锁，避免并发双写。
- 代理信任必须限定到可信 Docker 网段；不能盲目信任任意 `X-Forwarded-For`。

## 6. 上线计划

| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| S1-S2 | 后端/管理员 | 安全定向测试全绿，旧公开执行路径默认拒绝 |
| S3-S4 | 全部用户/运维 | reset、代理、安全和请求体回归全绿 |
| S5-S6 | 前端/部署 | Nginx 契约测试 + 生产响应头/固定路径验证 |
| QA/Leader | 发布决策 | 硬门禁全绿、无 P0/P1、用户总确认后合入 |

## 7. 技能使用

- `cameltv-agent-team` → 六部门工件与看板。
- `cameltv-bug-guard` → 副作用、路由、迁移和契约避坑。
- `cameltv-ui-conventions` → Nginx/HTML 变更不影响既有视觉和无障碍。
- `impeccable audit` → 本批仅做 HTML 安全层，不改变产品视觉。
