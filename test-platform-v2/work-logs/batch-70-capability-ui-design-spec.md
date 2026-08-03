# Batch 70 — Design Spec（能力产品化 UI 补齐）

> **Design (🎨)** | Date: 2026-08-03

## 1. 通用约定

- 组件：shadcn/ui（Dialog/Table/Button/Input/Select）+ Radix + Tailwind；新增页与现有系统页风格一致。
- API client：`src/api/*.ts` 复用 `client.ts` 请求封装；响应统一 `{code,msg,data}`。
- 三处同步：`backend/app/db/seed.py _MENUS`、`frontend CommandPalette ALL_COMMAND_ROUTES`、权限点。

## 2. Slice 1 — API Token 管理

### API（后端已存在）
```
GET    /api/v1/tokens            → list
POST   /api/v1/tokens            → create（返回明文 token 一次）
PUT    /api/v1/tokens/{id}       → update（enabled/name/expire）
DELETE /api/v1/tokens/{id}       → delete
```

### 前端
- `src/api/token.ts`：`listTokens/createToken/updateToken/deleteToken`。
- `src/pages/system/TokensTab.tsx`：Table + 「新建 Token」Dialog（名称/过期/权限范围）→ 创建后一次性展示明文
  （复制按钮 + 提示不再显示）；行内启用/停用开关、删除（二次确认）。
- `system/index.tsx` 注册 Tabs 项「API Token」；`seed.py _MENUS` 挂 `system:tokens` 路由；
  CommandPalette 增加 `token` 命令。

### 权限
- `token:list` 读、`token:manage` 写；无权限按钮禁用 + 403 提示。

## 3. Slice 2 — 用例导入导出

### API
```
POST /api/v1/test-cases/import/excel   （multipart file）
POST /api/v1/test-cases/import/xmind
GET  /api/v1/test-cases/export         （xlsx，参数 domain/module/ids）
```

### 前端
- `testcase.ts`：`importCases(file, type)`、`exportCases(params)`（blob 下载）、`downloadImportTemplate()`。
- testcase 页工具栏：导入（file input，Excel/XMind 切换）、导出（当前筛选）、模板下载。
- 导入完成 → 结果 Toast（imported/total）+ 列表刷新。

## 4. Slice 3 — 追溯下钻

- trace 页：覆盖率卡片（总/计划/执行/通过/缺陷）点击 → 需求文档列表（`/trace/requirement/{doc_id}` 摘要）
  → 用例明细（`/trace/case/{id}`：计划/执行/缺陷链）。
- 用现有 `trace.ts` 的 coverage/requirement/case 三个查询；新增 `requirement/{doc_id}` 与 `case/{id}` client。

## 5. Slice 4 — 报告模板管理

- 报告页模板选择区增加「管理模板」入口 → Dialog 内列表 + 新建/编辑/删除；
  `reportTemplate.ts` 增加 create/update/delete。

## 6. Playground 评估（非目标）

- 复核 C22-C2/C3 执行器链路证据（batch-66/67 登记）；若 `playground.py` runner 尚未经真实编译+执行验证，
  维持 API-only 并在 OpenAPI/README 标注，不展示前端入口。
