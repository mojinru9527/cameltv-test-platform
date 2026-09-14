# Batch 243 — Design Spec

> **Design (🎨)** | Date: 2026-09-14 | Status: 就绪

## 0. 技术体系确认

shadcn/ui + Radix + Tailwind + CVA；本批不引入新业务组件，不改变主题 token。变更属于 HTML 文档安全层、请求边界和 Runner 权限，视觉必须保持现状。

## 1. 组件规格表

| 组件 | 尺寸/间距 | 颜色语义 | 交互态 |
|------|-----------|----------|--------|
| 登录按钮 | 保持现有 `w-full` | 使用统一 `primary` 语义，但仅在明确触达时调整 | default/hover/focus/disabled 不变 |
| 权限拒绝反馈 | 沿用全局 toast/错误页 | `text-destructive` / status danger token | 明确说明需要管理员权限 |
| 主题 bootstrap | 外置后无视觉变化 | 继续读写 `cameltv-theme-*`、`data-theme` | 首屏防闪保持不变 |

## 2. 布局与响应式

| 断点 | 布局 | 变化 |
|------|------|------|
| <768px | 现有单列/抽屉 | 不变 |
| >=768px | 现有桌面布局 | 不变 |
| >=1024px | 现有侧边栏 + 内容 | 不变 |

## 3. 状态设计核对（四态）

| 组件 | Loading | Empty | Error | 未启用/无权限 |
|------|---------|-------|-------|---------------|
| Playground 执行 | 既有 loading | N/A | 明确安全拒绝原因 | 403 权限不足 |
| OpenAPI URL 导入 | 既有 loading | 无接口 | SSRF/大小/解析错误可读 | 无权限 403 |
| 生产健康/文档页 | N/A | N/A | 后端错误 JSON | 未配置时明确 404/关闭 |
| 全局 HTML | 浏览器正常加载 | N/A | 安全头不改变页面 | N/A |

## 4. 设计 QA 走查发现

### 🟠 P1-01 登录主 CTA 层级弱
`src/components/auth/LoginForm.tsx:97` 使用 `@/ui` Button 默认 `secondary`。本批允许作为安全批次的最小 UI 收敛项，改为显式主按钮，不进行整套组件迁移。

### 🟡 P2-01 忘记密码入口缺失
后端已有 `/auth/forgot-password`，但登录页没有入口。本批只记录为第三阶段 UX 任务，避免安全批次范围膨胀。

### 🟡 P2-02 内联主题脚本与严格 CSP 冲突
`src/index.html:7` 的内联脚本必须外置，才能对 HTML 应用不含 `unsafe-inline` 的 script-src。外置后需验证首屏主题、深色模式和首屏无闪烁行为保持一致。

### ⚪ P3-01 安全错误文案
SSRF、私网、响应过大和权限不足不能统一成“网络错误”；必须返回具体可执行提示，但不泄漏内网探测结果细节。

## 5. 设计签核

结论：有条件通过。条件是外置 bootstrap 后桌面/移动首屏主题无回归；本批次不把登录 UX 重构纳入实现。
