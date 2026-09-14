# Batch 245 — Design Spec

> **Design (🎨)** | Date: 2026-09-14 | Status: 就绪

## 0. 技术体系确认

shadcn/ui + Radix + Tailwind + CVA；颜色、边框、焦点和状态走语义 token。`components/ui` 是 canonical 实现，`@/ui` 是业务唯一公共出口。

## 1. 组件规格表

| 组件 | 尺寸/间距 | 颜色语义 | 交互态 |
|------|-----------|----------|--------|
| TaskCard | `min-h-32`, `gap-3`, `p-5`, `rounded-xl` | `bg-card`, `border-border`, `text-foreground` | hover `bg-muted/40`；focus ring；整个卡片可键盘触发 |
| Primary CTA | `min-h-11`, `px-4` | `bg-primary text-primary-foreground` | hover primary/90；focus ring；disabled opacity |
| Secondary CTA | `min-h-11`, `px-4` | `bg-secondary text-secondary-foreground` | hover secondary/80 |
| ModuleDisclosure | 容器 `space-y-4`；按钮 `min-h-11` | 语义背景/边框 | `aria-expanded`；chevron 旋转仅 transform |
| PasswordField | `h-8` 输入，右侧 toggle `size-11` 命中区 | `border-input`, `text-muted-foreground` | focus ring；toggle 不触发 submit；Caps 提示 warning 语义 |
| AuthCard | `max-w-[420px]`, padding 24 | `bg-card`, `ring-foreground/10` | 无硬编码色值 |

## 2. 布局与响应式

| 断点 | 布局 | 变化 |
|------|------|------|
| <768px | 单列 | Hero 文案紧凑；任务卡单列；模块目录单列；CTA 全宽或换行 |
| 768–1023px | 2 列 | 任务卡 2×2；认证卡居中 |
| ≥1024px | 4 列+双区 | 任务入口突出；模块目录按 2–3 列展示 |

统一保守断点：`grid-cols-1 md:grid-cols-2 xl:grid-cols-4`，避免从单列直接跳四列。

## 3. 状态设计核对（四态）

| 组件 | Loading | Empty | Error | 未启用(503) |
|------|---------|-------|-------|-------------|
| Homepage access | 保留当前骨架/空白降级 | 显示任务入口，模块目录显示“暂无可浏览模块” | 显示重试提示，不把失败当空目录 | N/A |
| Forgot password | 提交按钮 spinner + disabled | N/A | 不暴露账号存在性；显示提交失败 | SMTP 未配置显示管理员兜底 |
| Reset password | 提交按钮 spinner + disabled | 缺 token 显示可恢复说明 | 显示 token 过期/无效并回登录 | N/A |
| Login | 提交按钮 spinner | N/A | 字段错误 + 表单错误 | N/A |

## 4. 设计 QA 走查发现

### 🟠 P1-1 双 UI 公共入口冲突
事实：`src/ui/index.ts:4` 声明单一入口，但 `pages/layouts/components` 有 169 个文件直接引用 `@/components/ui/*`。  
**建议**：以 `@/ui` 聚合 canonical 导出，先用兼容适配保留历史调用，再迁移导入并加 ESLint 门禁。

### 🟠 P1-2 首页信息架构倒置
事实：`GuestPlatformHome.tsx:53-83` 直接渲染完整模块树，主任务入口只有一个通用“登录并开始使用”。  
**建议**：增加需求、接口、UI、报告四类任务卡；模块目录折叠到“浏览全部模块”。

### 🟠 P1-3 登录恢复链路缺失
事实：后端具有 `/auth/forgot-password` 与 `/auth/reset-password`，前端 `api/auth.ts` 和路由都无对应实现。  
**建议**：新增两个 auth 页面和 typed API；缺失 SMTP 时显示管理员兜底，不伪报邮件发送。

### 🟡 P2-1 密码可操作性不足
事实：`LoginForm.tsx:80-91` 只有固定 `type=password`，无显隐和 Caps Lock 提示。  
**建议**：加可访问的显隐按钮与 Caps Lock 非阻断提示。

### 🟡 P2-2 移动端触控目标风险
事实：新首页主要卡片/按钮可能使用默认 `h-8`；登录 CTA 为 `h-9`。  
**建议**：主要入口统一 `min-h-11`，显隐按钮用 44px 命中区，输入保持紧凑但触控区域足够。

## 5. 设计签核

结论：有条件通过；P1-1/P1-2/P1-3 为本批必须闭环项，P2-1/P2-2 一并修复。现有点击/焦点/主题 token 不得回退，完成后以 Playwright 截图复核桌面、平板和移动端。
