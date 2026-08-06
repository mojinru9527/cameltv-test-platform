# Batch 104 — Design Spec（外放轻量模式）

> **Design (🎨)** | Date: 2026-08-06 | Status: 就绪

## 0. 技术体系确认

shadcn/ui（Radix + Tailwind + CVA），非 Ant Design；Token 走语义类
（`bg-background`/`bg-card`/`bg-muted`/`text-foreground`/`text-muted-foreground`/
`border`/`text-destructive` + Button/Badge `variant`）；主题由 `data-theme-id` + `.dark`
驱动（`src/globals.css`），组件内不写死颜色。规范来源：`cameltv-ui-conventions` skill。

## 1. 组件规格表

| 组件 | 尺寸/间距 | 颜色语义 | 交互态 |
|------|-----------|---------|--------|
| 注册页 Card | `max-w-[400px]`，`p-6`，居中 `min-h-[100dvh]` | `bg-card text-card-foreground border` | 提交 loading 禁用；字段错误 `border-destructive` + `text-destructive` |
| 注册表单 | `space-y-4`，Input `h-10` | 同 LoginPage | 每字段 `<label htmlFor>`；错误 `<span role="alert">` |
| 登录页「注册」链接 | `text-xs text-muted-foreground` + 链接色 | `text-primary` | hover 下划线；触控区 ≥ 44px |
| 我的项目列表 | `DataTable` + `PageHeader` | 状态 Badge：启用 `success`/停用 `neutral` | 行内按钮 `h-8`；行点击区 `min-h-[36px]` |
| 新建/编辑项目 Dialog | `sm:max-w-[480px]` | 同现有 ProjectPage | `Loader2` 提交中 |
| 成员管理 Sheet | `side="right" w-full sm:max-w-[600px]` | 同现有 ProjectPage | 同现有 |
| 邀请码管理 Tab | `DataTable` + 新建 Dialog | 状态：启用 `success`/已停用 `neutral`/已用尽 `neutral` | 停用 AlertDialog 确认 |
| 空态（无项目） | `EmptyState`：标题「暂无项目」+ 副文案 + 主按钮 | 现有 EmptyState token | 主按钮「新建项目」 |
| 顶栏项目切换器 | 现有 Select 组件 | 现有 | 无项目时 placeholder「请先创建项目」，不可切换 |

## 2. 布局与响应式

| 断点 | 布局 | 变化 |
|------|------|------|
| ≥1024px | 注册页单卡居中；我的项目表格全宽 | 操作按钮行内 |
| 768–1023px | 同单列；成员 Sheet 全宽 | 表格列隐藏描述列 |
| <768px | 注册页 `p-4`；按钮全宽 `w-full` | 新建按钮置顶；表格横向滚动 |

## 3. 状态设计核对（四态）

| 组件 | Loading | Empty | Error | 未启用(503) |
|------|---------|-------|-------|-------------|
| 我的项目 | `Skeleton` 行 ×4 / DataTable loading | `EmptyState`「暂无项目」+ 新建按钮 | `ErrorState` + 重试 | 页面正常渲染，接口 403/503 走 ErrorState |
| 邀请码管理 | `Skeleton` 行 ×4 | `EmptyState`「暂无邀请码」 | `ErrorState` + 重试 | 同 ErrorState |
| 注册提交 | 按钮内 `Loader2 animate-spin` + 禁用 | N/A | 字段级错误 + 顶部 `role="alert"` 汇总 | `registration_enabled=false` → 403 文案「注册未开放」 |

## 4. API / 状态契约（后端）

### 注册
`POST /api/v1/auth/register`

```json
{ "username": "alice", "nickname": "爱丽丝", "email": "a@x.com",
  "password": "secret1", "invite_code": "AB12CD34" }
```

成功 `200 { code:0, data: { access_token, user, projects: [], permissions, must_change_password:false } }`，
写 httpOnly cookie（同登录）。失败：400（邀请码无效/过期/用尽、用户名或邮箱已存在）、
403（注册未开放）、429（频率限制）。

### 邀请码管理（管理员）
- `GET /api/v1/system/invite-codes` → `{ items:[{id,code,usage_limit,used_count,expires_at,status,created_by_name,created_at}] }`
- `POST /api/v1/system/invite-codes { usage_limit?:1, expires_at?:null }` → 生成 `code`（secrets，10 位大写）
- `POST /api/v1/system/invite-codes/{id}/disable` → `{ disabled:true }`

### 项目（自助）
- `POST /api/v1/projects`：放行条件 = 全局 `project:create` 或 `project:self_create`；
  服务层自动 `ProjectMember(owner, project_admin)`；超限 400「项目数量已达上限」。
- `PUT/DELETE /api/v1/projects/{id}`、`POST /members`、`DELETE /members/{user_id}`：
  放行条件 = 全局对应权限 **或** 当前用户为该项目 `owner_id`。

### 配置
`registration_enabled=false`（默认关闭）、`invite_code_required=true`、
`default_registration_role="tester"`、`max_projects_per_user=5`、注册限流独立桶。

## 5. 设计 QA 走查发现（预防性，P3）

### ⚪ P3-01 菜单入口
现状 `menu:project` 不在 tester 菜单，普通用户无入口。→ 新增 `menu:myproject`
（路径 `/my-projects`）加入 tester/viewer 菜单，避免外放用户找不到项目入口。

### ⚪ P3-02 项目为空时顶栏切换器
注册用户无项目时切换器无选项。→ placeholder「请先创建项目」，并在工作台引导空态；
不隐藏整个顶栏，避免布局跳变。

### ⚪ P3-03 邀请码展示
邀请码生成后只在 Dialog 中展示一次（`code` 明文），关闭后不再提供查看原文，
避免明文常驻列表。列表仅显示脱敏尾 4 位 + 状态。

### ⚪ P3-04 状态中文映射
邀请码状态用中文（启用/已停用/已用尽），不裸渲染后端枚举。

## 6. 设计签核

结论：**通过**。以上 4 项 P3 建议随实现一并落实（不设阻断项）；实现后由 QA 按
`cameltv-ui-conventions` Red Flags 逐条复核（Badge 可辨、深色变体、四态、触控目标、
响应式、ARIA）。
