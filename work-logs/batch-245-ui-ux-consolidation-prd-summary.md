# Batch 245 — UI/UX Consolidation & Task-First Onboarding

> **Product (🟦)** | Date: 2026-09-14 | Status: Approved for planning

## 1. 问题陈述

当前平台具备完整的测试能力，但首次使用心智仍以“平台模块目录”为中心：

1. 公开首页把后端返回的模块树按 22 个等权入口平铺，用户先看到的是“功能清单”而不是“我要完成什么任务”。证据：`test-platform-v2/frontend/src/layouts/GuestPlatformHome.tsx:53-83`。
2. 前端同时存在 `@/ui` 与 `@/components/ui` 两个组件入口。`src/ui/index.ts:4` 宣称 `@/ui` 是业务页面唯一入口，但当前有 169 个源码/测试文件直接导入 `@/components/ui/*`，组件 API、样式基线和后续升级路径持续漂移。
3. 登录表单缺少密码显示/隐藏、Caps Lock 提示和密码找回入口。后端已有 `/auth/forgot-password` 与 `/auth/reset-password`，前端没有对应页面和 API 封装，用户可以注册却没有自助恢复路径。
4. 公开页、登录页和恢复页缺少同一批桌面/平板/移动端视觉与溢出回归证据。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 首页首屏任务入口 | 0 个 | 4 个任务入口 + 1 个模块浏览入口 | 本批 Vitest + Playwright |
| `@/components/ui` 业务导入 | 169 个文件 | 0 个（仅 `src/ui` 适配层可引用 canonical 实现） | ESLint + governance test |
| 登录恢复路径 | 无前端页面 | 忘记密码 + token 重置 + 返回登录完整闭环 | Vitest + Playwright |
| 登录辅助能力 | 无 | 密码显隐、Caps Lock 提示、SMTP/管理员兜底说明 | Vitest + Playwright |
| 响应式回归 | 零散截图 | desktop/tablet/mobile 无横向溢出 + 截图证据 | Playwright |
| 现有 a11y | WCAG AA 基线 | 关键新页面无 axe serious/critical | Vitest/Playwright a11y |

## 3. 非目标（本次不做）

- 不重写全部业务页面视觉；本批只收敛组件出口和代表性交互。
- 不引入新的 UI 框架或组件库。
- 不改动 Phase 1 已完成的 CSP/HSTS、安全头、theme bootstrap 与 Nginx 反代契约。
- 不新增密码复杂度策略；沿用后端最少 6 位约束，避免扩大后端安全行为范围。
- 不把自动截图基线作为易误报的像素门禁；本批做稳定 DOM、响应式、无溢出和人工可复核截图。

## 4. 用户故事 + 验收标准

### US-1 任务入口优先
As a 首次访问的访客, I want 直接看到“开始需求测试 / 做接口回归 / 创建 UI 自动化 / 查看测试报告”, so that 我从任务目标进入而不是先学习模块树。
- 验收：Given 未登录访客打开 `/` / When 首页加载 / Then 首屏出现 4 个任务入口；“浏览全部模块”可展开/收起完整目录。
- 验收：点击任务入口时走登录门禁，登录成功后回到目标路径，不泄露业务数据。

### US-2 单一 UI 入口
As a 前端开发者, I want 业务代码只从 `@/ui` 导入组件, so that 组件升级、主题 token 和交互修复只需处理一套入口。
- 验收：业务源码、单元测试和新增页面不再直接导入 `@/components/ui/*`。
- 验收：canonical shadcn 实现仍是底层实现；`src/ui/primitives` 只保留兼容适配和领域专属组件。
- 验收：ESLint 对新增绕过入口的导入失败；治理测试纳入默认 Vitest。

### US-3 登录恢复
As a 忘记密码的用户, I want 从登录页请求重置并在新页面设置新密码, so that 我不依赖管理员人工交接 token。
- 验收：登录页有“忘记密码”链接，`/forgot-password` 提交用户名后显示防枚举统一提示。
- 验收：邮件配置可用时提示已发送；未配置 SMTP 时明确提示联系管理员，不伪造成功。
- 验收：`/reset-password?token=...` 可提交新密码与确认密码；成功后回到登录页。

### US-4 登录可操作性
As a 登录用户, I want 查看密码和 Caps Lock 状态提示, so that 我能发现输入错误而不是反复失败。
- 验收：密码显隐按钮有可访问名称，键盘可操作，切换不会清空表单。
- 验收：Caps Lock 开启时显示非阻断提醒；提交按钮和错误信息保持清晰。

### US-5 多端稳定
As a 平板/手机用户, I want 首页和认证页没有横向滚动或遮挡, so that 我可以在移动网络下完成入口和恢复操作。
- 验收：375px、768px、1440px 视口无水平溢出；触控目标不小于 44px（认证 CTA/显隐按钮）。

## 5. 技术考量

- 组件出口采用 `@/ui` 聚合层，canonical 实现仍位于 `components/ui`；兼容适配只覆盖历史 `primary/danger/tone` 语义，避免一次性重写业务组件。
- 登录恢复复用现有后端接口和 30 分钟一次性 token 机制；新增邮件发送必须使用 `frontend_url` 生成重置链接，并通过 `BackgroundTasks` 避免阻塞请求。
- 新增 `password_reset_email_enabled` 到公开访问配置，仅暴露布尔值，不暴露 SMTP 主机、用户或凭据。
- 视觉测试使用 Playwright route stub，避免依赖真实 SMTP 或生产数据。

## 6. 上线计划

| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 开发+单测 | 前端维护者 | typecheck/lint/build + Vitest 全量通过 |
| QA 浏览器走查 | QA/产品 | 3 视口截图、无控制台错误、关键路径通过 |
| 合入前审计 | 发布负责人 | required checks 全绿、Leader verdict APPROVED |

## 7. 技能使用

`cameltv-agent-team` → 六部门工件与本批看板；`cameltv-ui-conventions` → 双轨入口/响应式/token 红线；`cameltv-bug-guard` → React effect、空态、错误链和依赖检查；`playwright-cli` → 多视口验证与截图证据。
