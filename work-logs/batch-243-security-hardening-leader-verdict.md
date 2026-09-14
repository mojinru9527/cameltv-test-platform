# Batch 243 — Leader Verdict
> **Leader (🎯)** | Date: 2026-09-14 | Decision: 有条件通过（待用户一次总确认与 required checks）

## 评审摘要

| 维度 | 评分 | 备注 |
|------|------|------|
| 实现质量 | 4/5 | 安全边界分层清晰，权限、env、SSRF、reset、安全头和流式 body cap 均有回归证据 |
| 风险控制 | 4/5 | P0 默认暴露面已收口；容器级单任务隔离仍作为后续增强 |
| 覆盖 | 4/5 | backend 全量 2670 passed；frontend 全量 698 passed；新增安全测试覆盖关键攻击路径 |
| 流程 | 4/5 | 六部门工件、看板、切片提交齐全；本批为四阶段计划的第一阶段 |

## 关键决策（已批准）

1. 用户提供的 Playwright spec 视为高权限代码执行，默认 tester 不再拥有 `uitest:code_execute`。
2. Playwright 子进程不再继承后端完整环境；只允许平台白名单变量和显式运行参数。
3. OpenAPI URL 导入默认禁止私网、回环、链路本地、保留地址，并限制重定向和响应体。
4. reset token 必须显式 30 分钟过期，绑定密码版本并在成功后失效。
5. HTML 安全头由 Nginx 统一注入；主题 bootstrap 外置，避免依赖 CSP inline 豁免。
6. `/health`、`/openapi.json`、`/docs`、`/redoc` 必须显式反代，禁止 SPA fallback 伪装健康。
7. 全局请求体上限必须按实际接收字节执行，不能信任 `Content-Length`。

## 抽检通过

- ✅ `app/core/execution_sandbox.py` — 不复制 `os.environ`；敏感变量测试通过。
- ✅ `app/api/v1/apitest_assets.py` — 所有 URL 和候选/重定向请求经 `safe_get_text`。
- ✅ `app/api/v1/auth.py` + `core/security.py` — 30 分钟显式 expiry；成功后旧 token 返回 envelope 400。
- ✅ `frontend/nginx.conf` + `security-headers.conf` — 容器 smoke 返回 CSP/HSTS/X-Frame；外置 bootstrap 200。
- ✅ `app/main.py` — chunked/无 Content-Length 超限测试返回 413。
- ✅ Backend full — `2670 passed, 51 skipped, 1 xfailed`。
- ✅ Frontend full — `159 files, 698 tests passed`。
- ✅ G0 — HARD=0；G1 F821=通过。

## 判决

有条件通过。代码、QA 和本地硬门禁已达到合入前标准；在当前用户一次总确认前不得 push/PR。
用户确认后需完成：

1. push `feature/platform-hardening-phases-1-4`；
2. 创建 Draft PR 指向 `main`；
3. 运行 `audit-ai-pr.ps1 -ExpectedWorkflow agent-team -ExpectedExecutor codex`；
4. required checks 全绿后运行 `audit-ai-pr.ps1 -RequireSuccessfulChecks`；
5. 审计通过后 Leader 才可最终 APPROVED、转 Ready 并 squash 合入 main。

## 下一批次 Leader 条件

- C243-1（P2）：在代码级最小权限/env/资源限制之外，完成单任务 Runner 容器隔离、只读 rootfs 和更严格的 egress policy。
- C243-2（P1）：第二阶段使用生成式 OpenAPI typed client，消除核心 API 的手写 `any` 与响应契约漂移。
- C243-3（P1）：第三阶段收敛两套 UI 组件体系，按任务入口重做公开首页/登录恢复路径，并保留视觉回归。
- C243-4（P1）：第四阶段把完整 Ruff/mypy、axe/Lighthouse 和依赖审计纳入 required checks，禁止失败后 `echo` 成功。

## 流程回写（Batch 75 起强制）

| 发现 | 处理 | 落点 |
|------|------|------|
| 现有安全中间件只保护 API JSON，HTML 静态资源没有等价响应头 | 本批补齐 Nginx include 与外置 bootstrap；后续所有静态入口必须做 header smoke | `frontend/nginx.conf`、`frontend/security-headers.conf` |
| 用户代码执行能力此前与普通 tester 权限混用 | 新权限 `uitest:code_execute` 并同步后端、前端和 RBAC 矩阵 | `seed.py`、`playground.py`、`ui_test.py`、`uitest/index.tsx` |
| 出站 URL 校验曾在不同服务重复或缺失 | 新增统一 `outbound_policy`，后续外部 URL 接入必须复用 | `app/core/outbound_policy.py` |
| 暂无技能/模板缺陷需要回写 | 无需处理 | - |

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 18h planned | 0/0/0/1 | 2 | 权限模型适配 + 主题脚本测试契约迁移 | 开批先锁定权限矩阵、静态入口和测试读取路径 |

**技能使用**：`cameltv-agent-team` → 六部门与 C 条件闭环；`cameltv-bug-guard` → 路由/副作用/安全回归；`cameltv-ui-conventions` → CSP 外置脚本不改变视觉与无障碍。
