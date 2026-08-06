# Batch 105 — Design Spec（租户模式）

> **Design (🎨)** | Date: 2026-08-06 | Status: 就绪

## 0. 技术体系确认

shadcn/ui（Radix + Tailwind + CVA）；语义 Token；主题由 `data-theme-id` + `.dark` 驱动；
沿用 `cameltv-ui-conventions`（四态、中文状态、触控目标、响应式、ARIA）。

## 1. 组件规格表

| 组件 | 尺寸/间距 | 颜色语义 | 交互态 |
|------|-----------|---------|--------|
| 组织管理页头 | `PageHeader` + 「新建组织」主按钮 `ml-auto` | 现有 | 权限不足隐藏按钮 |
| 组织表格 | `DataTable`：名称/类型/成员数/项目数/我的角色/操作 | 类型 Badge：个人 `neutral`/团队 `success`；角色 Badge `neutral` | 行内按钮 `h-8` |
| 新建/编辑组织 Dialog | `sm:max-w-[480px]` | 同项目 Dialog | 提交 `Loader2` |
| 成员管理 Sheet | `side="right" w-full sm:max-w-[600px]` | 同 Batch 104 项目成员 Sheet | 邀请成功 toast |
| 组织项目列表 | 内嵌 Card + 表格（进入按钮） | 状态 Badge 启用/停用 | 行点击进入 |
| 项目创建 Dialog | 增加「所属组织」Select（默认个人组织） | 现有 Select | 无组织时禁用并提示先创建 |
| 我的项目表格 | 增加「组织」列（`text-xs text-muted-foreground`） | 无 Badge，普通文字 | — |

## 2. 布局与响应式

| 断点 | 布局 | 变化 |
|------|------|------|
| ≥1024px | 组织表格全宽 + 成员 Sheet 右侧 | 操作行内 |
| 768–1023px | 表格隐藏「项目数」列 | 成员 Sheet 全宽 |
| <768px | 新建按钮全宽置顶 | 表格横向滚动；Sheet 全宽 |

## 3. 状态设计核对（四态）

| 组件 | Loading | Empty | Error | 未启用(503) |
|------|---------|-------|-------|-------------|
| 组织列表 | `Skeleton` ×4 | `EmptyState`「暂无组织」+ 新建 | `ErrorState` + 重试 | 同 ErrorState |
| 成员列表 | `Skeleton` ×3 | 「暂无成员，邀请你的同事吧」 | 提示 + 重试按钮 | 同 ErrorState |
| 组织项目 | `Skeleton` ×3 | 「该组织暂无项目」 | 提示 | 停用组织提示 |
| 项目创建（无组织） | N/A | 个人组织永远存在，正常 | 创建失败 toast | N/A |

## 4. API / 状态契约（后端）

### 组织
- `GET /api/v1/organizations` → `[{id,code,name,description,type: personal|team,
  owner_id,my_role: 1|2|3,status,member_count,project_count}]`
- `POST /api/v1/organizations {code,name,description}` → 团队组织（个人组织注册时自动创建）
- `PUT /api/v1/organizations/{id} {name?,description?,status?}` → 负责人/管理员
- `DELETE /api/v1/organizations/{id}` → 软停用（个人组织拒绝 400；仅负责人/管理员）
- `GET/POST /api/v1/organizations/{id}/members`、`DELETE .../members/{user_id}` → 负责人/管理员
- `GET /api/v1/organizations/{id}/projects` → 组织成员
- 错误：非负责人/管理员 403；组织不存在 404（envelope）；团队组织数超限 400

### 项目
- `POST /api/v1/projects {code,name,description,organization_id?}` → 默认创建者个人组织；
  非组织成员 403
- `GET /api/v1/projects` → 项目含 `organization_id`/`organization_name`
- 访问控制：项目成员 或 项目所属组织成员 或 超管

### 鉴权扩展
- `LoginOut`/`MeOut` 增加 `organizations: OrganizationBrief[]`（前端顶栏/项目页用）

### 配置
`max_team_organizations_per_user=5`（个人组织不计入）。

## 5. 设计 QA 走查发现（预防性，P3）

### ⚪ P3-01 个人组织不可停用/不可删除
个人组织是项目归属兜底，删除会导致项目无归属。→ 前端隐藏停用按钮，后端 400 拒绝。

### ⚪ P3-02 组织角色中文映射
`my_role` 用 1/2/3 返回，前端映射「负责人/管理员/成员」，不裸渲染数字。

### ⚪ P3-03 项目创建默认组织
创建项目 Dialog 默认选中「我的组织」（个人组织），避免用户误选或漏选。

### ⚪ P3-04 停用组织联动
停用团队组织后，组织项目仍可被项目成员/超管访问，但组织成员入口不可见（提示「组织已停用」）。

## 6. 设计签核

结论：**通过**。P3 建议随实现落实；QA 按 Red Flags 复核（Badge 可辨、深色、四态、触控、ARIA）。
