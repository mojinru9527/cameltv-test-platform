# Batch 106 — Design Spec（生产启用 + 组织权限映射 + 项目邀请链接）

> **Design (🎨)** | Date: 2026-08-06 | Status: 就绪

## 0. 技术体系确认

shadcn/ui + Tailwind 语义 Token；沿用 `cameltv-ui-conventions`（四态/中文/触控/ARIA）。
组织权限映射无新增 UI（按钮由 `hasPerm` 自动出现）。

## 1. 组件规格表（项目邀请链接）

| 组件 | 尺寸/间距 | 颜色语义 | 交互态 |
|------|-----------|---------|--------|
| 成员 Sheet「生成邀请链接」按钮 | `size="sm" variant="secondary"` | 现有 | 仅负责人可见 |
| 邀请链接 Dialog | `sm:max-w-[480px]` | 现有 Dialog | 次数 `Input number`（默认 1）、有效期 `datetime-local`（可选） |
| 链接展示区 | `rounded-lg border bg-muted p-3` + `code font-mono text-xs break-all` | muted | 复制按钮 `Loader2`/成功 toast |
| 注册页项目邀请提示 | 表单上方 `rounded-lg border p-3 text-sm` | `info` 语义（不硬编码蓝） | 随 `?invite=` 参数出现 |

## 2. 布局与响应式

| 断点 | 布局 | 变化 |
|------|------|------|
| ≥1024px | Dialog 居中，链接可横排复制 | — |
| <768px | 链接 `break-all` 换行，复制按钮全宽 | 表单纵向堆叠 |

## 3. 状态设计核对

| 组件 | Loading | Empty | Error | 未启用 |
|------|---------|-------|-------|--------|
| 邀请链接生成 | 按钮 `Loader2` | N/A | toast「生成失败」 | 非负责人不渲染 |
| 注册页 invite 参数 | 正常表单 | 链接失效 → 注册 400 提示 | 内联 `role="alert"` | 平台注册关闭仍按 403 |

## 4. API / 契约

### 项目邀请链接
- `POST /api/v1/projects/{project_id}/invites {usage_limit?:1, expires_at?:null}` → 负责人/超管；
  返回 `{id, token, url, usage_limit, used_count, expires_at, status}`
- `GET /api/v1/projects/{project_id}/invites` → 负责人/超管（列表，token 脱敏尾 4 位）
- `POST /api/v1/projects/{project_id}/invites/{invite_id}/disable` → 负责人/超管
- `RegisterIn.project_invite_token?: str` → 有效 token 免除平台邀请码；注册事务内
  加入项目成员 + 项目所属组织成员
- 错误：无效/过期/用尽 400；非负责人 403；项目不存在 404（envelope）

### 组织权限映射（无新端点）
- `permission_codes(db, user_id, project_id)`：当项目有 `organization_id` 且用户为组织
  owner(1)/admin(2) 时追加 `project:manage/project:update/project:delete/project:detail`
- 前端无需改动（`hasPerm` 自动生效）

## 5. 设计 QA 走查（预防性，P3）

### ⚪ P3-01 链接脱敏
列表页 token 只显示尾 4 位；完整链接仅生成时展示一次（同 Batch 104 邀请码契约）。

### ⚪ P3-02 注册页提示
带 `?invite=` 时显示「你正被邀请加入项目」，避免用户困惑；链接失效时由后端 400 文案提示。

### ⚪ P3-03 复制交互
复制成功 toast「链接已复制」，失败给手动选择提示；不静默失败。

## 6. 设计签核

结论：**通过**。P3 建议随实现落实；QA 按 Red Flags 复核。
