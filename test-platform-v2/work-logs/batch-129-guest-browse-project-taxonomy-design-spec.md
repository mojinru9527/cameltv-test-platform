# Batch 129 — Design Spec（访客功能浏览、项目引导与用例重分类）
> **Design (🎨)** | Date: 2026-08-09 | Status: 就绪

## 0. 技术体系确认

shadcn/ui + Radix + Tailwind + CVA；颜色只使用 `bg-background`、`bg-card`、`bg-muted`、`text-foreground`、`text-muted-foreground`、`border`、`primary` 等语义类。主图标使用 Lucide，不改 `components/ui/*` 生成物。

## 1. 信息架构

```text
访客首页
└─ 点击模块 → 模块说明页（公开）
   ├─ 模块用途
   ├─ 3–5 个核心能力
   ├─ “仅在登录并选择项目后读取业务数据”提示
   ├─ 登录后使用 → Login Dialog → 原路径
   └─ 免费注册 → /register

已登录、无项目
└─ 任一项目域路由 → 创建项目空状态（不挂载业务页）
   ├─ 1 注册账号（已完成）
   ├─ 2 创建项目（当前）
   └─ 3 进入功能
```

## 2. 组件规格表

| 组件 | 尺寸/间距 | 颜色语义 | 交互态 |
|------|-----------|----------|--------|
| GuestModulePreview 页头卡 | `max-w-5xl`, `p-6 sm:p-8`, `rounded-2xl` | `bg-card border-border/70` | CTA 默认/hover/focus；无 disabled 伪态 |
| 能力项卡片 | `grid md:grid-cols-2`, `p-4`, `min-h-[120px]` | `bg-muted/30`, 图标 `text-primary` | 纯信息，不伪装按钮 |
| 登录边界提示 | `rounded-xl p-4`, 图标+正文 | `bg-muted/50 text-muted-foreground` | 无交互 |
| ProjectRequiredState | `max-w-2xl`, 居中空状态，`p-6 sm:p-10` | `bg-card border`, 状态图标 `bg-primary/10` | 主 CTA `/my-projects`，次 CTA 返回公开目录不需要 |
| 动态 surface Select | `h-9 w-[150px]` | 标准 Select token | 只渲染实际存在的端别 |

## 3. 布局与响应式

| 断点 | 模块说明页 | 无项目状态 |
|------|------------|------------|
| `<768px` | 单列；CTA 纵向/可换行；主触控目标 ≥44px | 步骤纵向排列，按钮全宽 |
| `md 768–1023px` | 能力卡 2 列 | 内容最大宽度 640px |
| `lg ≥1024px` | 内容最大宽度 960px；说明与边界信息并排可读 | 保持单一焦点，不扩成仪表盘 |

## 4. 状态设计核对（四态）

| 场景 | Loading | Empty | Error | 未启用/受限 |
|------|---------|-------|-------|-------------|
| 公开目录 | 导航请求期间保留壳 | 无模块时显示平台介绍与登录/注册 | 导航区现有可重试错误态 | 不适用 |
| 模块说明 | 静态目录，无二次加载 | 未知路径显示安全兜底说明 | 不触发业务 API，无业务错误态 | 明示“登录并选择项目后使用” |
| 无项目 | 无二次加载 | 即本组件，明确创建项目 CTA | 项目列表页负责自身 ErrorState | 无创建权限时改为联系管理员文案 |
| 用例 surface | 随用例页现有 loading | 无用例沿用 AsyncState | 沿用现有 ErrorState/重试 | “其他”仅在真实未知数据存在时出现 |

## 5. 行为规则

1. 导航行为和使用行为必须分离：侧栏/首页卡片只 `navigate`，模块说明主 CTA 才打开 `LoginGateDialog`。
2. 访客模块说明页不得 import 或 mount 对应业务页面，避免匿名 API 请求和 bundle 副作用。
3. 无项目边界必须位于 `<Outlet />` 外层；只隐藏错误 toast 不算修复。
4. `/my-projects` 与 `/organizations` 是起步白名单，不能被项目边界挡住。
5. “其他”不是可随意隐藏的数据；只有映射后数据集中确实没有未知项时，筛选项才消失。

## 6. 无障碍与文案

- 页面唯一 `h1` 为模块名或“先创建一个项目”。
- 图标 `aria-hidden=true`；纯图标动作保留 `aria-label`。
- CTA 文案使用“登录后使用 {模块名}”“创建第一个项目”，不写模糊的“确定/继续”。
- 当前步骤用文本和图标双重表达，不仅靠颜色。
- 页面路径变化后沿用 `MainLayout` 对 `#main-content` 的焦点管理。

## 7. 设计 QA 走查发现

### 🟠 P1-01 访客入口把浏览误当成使用

`frontend/src/layouts/GuestPlatformHome.tsx` 模块按钮调用 `onRequireLogin`，`MainLayout.tsx` 又在访客直达非根路径时自动打开登录。→ **建议**：新增模块说明页，取消直达自动登录，仅 CTA 触发门禁。

### 🟠 P1-02 无项目仍挂载业务页

`frontend/src/layouts/MainLayout.tsx` 的认证分支无条件渲染 `ProjectScopeBoundary > Outlet`；`ProjectScopeBoundary.tsx` 只重置 key，不阻断。→ **建议**：在 Outlet 上层添加 no-project 空状态与白名单。

### 🟡 P2-01 脑图固定展示“其他”

`frontend/src/pages/mindmap/index.tsx` 固定枚举四个界面，即使数据已全部归类仍显示“其他”。→ **建议**：筛选项由响应 surface 集合按固定顺序生成。

## 8. 设计签核

结论：**通过**。实现必须保持公开元数据与业务数据的安全边界，并用 Network 证据验证。

