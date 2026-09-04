# Batch 229 — Worker Token Onboarding PRD Summary
> **Product** | Date: 2026-09-04 | Status: Approved | mode: full

## 1. 问题陈述

Batch 228 的真实 Runbook 启动验证发现，黑盒管理员无法从 Durable Runtime 页面或部署文档获得 Worker 注册凭据。现有 API Token 页面默认创建 `trigger` 作用域，而 `/api/v2/workers/heartbeat` 只接受网页登录 JWT；因此即使管理员自行创建 `tpat_` Token，Worker 也不能按文档完成注册。无 Token 启动会持续收到 HTTP 401，页面只能显示“尚未发现 Worker”。

用户关心的是一条可由普通平台管理员独立完成、可撤销且不泄露秘密的前端操作链路，而不是数据库夹具或接口模拟出来的在线状态。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量方式 |
|------|------|------|----------|
| Worker 凭据可发现性 | Runtime 仅指向 Runbook | Runtime 一步进入 Worker Token 生成入口 | 浏览器关键路径 |
| Worker Token 可用性 | `tpat_` Token 无法鉴权 heartbeat | `workers:register` Token 注册成功，错误作用域被拒绝 | 后端集成测试 |
| 秘密暴露面 | 创建弹窗只展示裸 Token | Worker 配置仅创建后展示一次，关闭即清空，不写日志/截图/仓库 | 组件测试 + 证据扫描 |
| 撤销与轮换 | 用户不知道去哪里操作 | 创建结果可进入 Token 管理；停用/删除沿用现有生命周期 | 浏览器关键路径 |
| 启动失败反馈 | 空 Token 进入重试循环并收到 401 | 启动器在拉起进程前明确拒绝空 Token | 启动器契约测试 |

## 3. 非目标（本次不做）

- 不在网页中远程启动、停止或部署 Worker 进程。
- 不新建第二套机器凭据表、明文 Token 存储或自动下载秘密文件。
- 不改变 Worker drain/disable、Temporal、网络分区或任务路由语义。
- 不把本地 Worker 注册通过表述为生产 Worker 已上线；生产仍需发布后执行真实进程耐久复验。
- `C227-2` 仅承接 Worker 凭据这一项；健康 AI Provider、真实体育 OpenAPI、被测地址和生产部署继续 Deferred。
- C203/C204/C205 等其他 Open 条件与本批无关，保持原状态，不扩张处理。

## 4. 用户故事 + 验收标准

- As a 平台管理员, I want 在 Runtime Worker 页面看到明确的接入凭据入口, so that 我不需要猜测 `runner_key` 从哪里获取。
  - Given 我有 `token:manage` 权限 / When 打开 Worker 页 / Then 页面提供“生成 Worker Token”入口，并进入已选 Worker 用途的 Token 表单。
  - Given 我没有 `token:manage` 权限 / When 打开 Worker 页 / Then 页面说明需要联系管理员，不展示越权创建按钮。
- As a 平台管理员, I want 创建专用 Worker Token, so that Worker 能以最小权限发送心跳。
  - Given 创建用途为 Worker / When 创建成功 / Then 后端保存 `workers:register` 作用域，明文只在成功弹窗展示一次。
  - Given Token 缺少 `workers:register` / When 调用 heartbeat / Then HTTP 403 且不注册 Worker。
- As a 运维人员, I want 复制可直接使用的环境配置, so that 我能按 Runbook 启动真实 Worker。
  - Given Worker Token 创建成功 / When 复制启动配置 / Then 包含当前 Control Plane 地址、Token 和启动命令；关闭弹窗后不能再次读取明文。
- As a 安全管理员, I want 能撤销或轮换 Worker Token, so that 泄露或人员变更后能立即失效旧凭据。
  - Given 已有 Worker Token / When 在 API Token 列表停用或删除 / Then 后续 heartbeat 被拒绝；新 Token 可替换旧 Token。

## 5. 技术考量

- 复用 `ApiToken` 哈希存储、一次回显、启停和删除生命周期；不引入 Schema 或迁移。
- heartbeat 改用 API Token 专用鉴权，并强制 `workers:register` scope；Worker 列表和管理操作继续使用网页登录 RBAC。
- `last_used_at` 在成功 heartbeat 时更新，帮助管理员识别正在使用的凭据。
- 前端遵循 shadcn/ui + Tailwind 语义 Token、44px 触控目标、中文状态和三视口响应式规范。
- 知识库 MCP 在当前会话未暴露可调用检索工具；替代核查已覆盖 C 条件、Batch 228 新鲜缺陷、Git 历史、现有 Token/Runtime 实现与 Bug Guard。旧体育验收报告不作为本批验收证据。

## 6. 上线计划

| 阶段 | 受众 | 成功门槛 |
|------|------|----------|
| 本地 | Dev/QA | 定向测试、双端门禁、真实浏览器三视口全绿 |
| PR | Reviewer | required checks 全绿 + 最终审计通过 |
| 发布后 | 生产管理员 | 前端生成 Token，真实 Worker 连续心跳超过 180 秒仍 ONLINE |

## 7. 技能使用

- `cameltv-agent-team`：完整六部门工件、独立 worktree、QA/PR 门禁。
- `cameltv-bug-guard`：鉴权分层、路由薄层、测试 Cookie 清理和前端副作用检查。
- `cameltv-ui-conventions`：语义样式、权限态、触控目标和响应式规范。
- `writing-plans`：按 TDD 切片生成可执行实施计划。
- `karpathy-guidelines`：复用既有 Token 生命周期，限制变更面。
- `playwright-cli`：本地真实浏览器关键路径和三视口验收。
