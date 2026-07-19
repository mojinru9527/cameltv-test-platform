# QA Report — 三个浏览器报错修复验证

**批次**: `bugfix-three-errors`  
**日期**: 2026-07-20  
**测试方式**: HTTP 层端到端验证（前端 5173 + 后端 8001）  
**QA 结论**: ✅ **PASS** — 三个修复均已生效，可交付

---

## 测试环境

| 服务 | 地址 | 状态 |
|------|------|------|
| 后端 FastAPI | `localhost:8001` | ✅ Live |
| 前端 Vite Dev | `localhost:5173` | ✅ Live |
| Vite Proxy | `/api` → `localhost:8001` | ✅ 正常代理 |

---

## 修复验证

### Bug 1: `/api/v1/system/menus` 500 错误

| 检查项 | 结果 | 证据 |
|--------|------|------|
| HTTP 状态码 | ✅ 200（曾 500） | `curl` 直接调用返回 `{"code":0,"msg":"ok"}` |
| 菜单数量 | ✅ 20 条菜单 | 完整菜单树返回 |
| sort 字段类型 | ✅ 全部 int（曾 float 10.5） | `sort=1,2,2,3,4,...` 全为整数 |
| 无 ValidationError | ✅ 无异常 | `MenuOut.coerce_sort` 正确将 float→int |

**验证命令**: `curl -s http://localhost:8001/api/v1/system/menus -H "Authorization: Bearer $TOKEN"`  
**根因**: Pydantic v2 严格类型校验，SQLite REAL 列存 float 10.5 → `field_validator("sort", mode="before")` 强制 `int(v)`  
**修复文件**: `backend/app/schemas/system.py:24-28`

---

### Bug 2: CSS 侧边栏选择器不匹配

| 检查项 | 结果 | 证据 |
|--------|------|------|
| `data-sidebar="root"` 残留 | ✅ 0 处 | `grep -c "data-sidebar=\"root\"" globals.css` → 无匹配 |
| `data-sidebar="sidebar"` 正确 | ✅ 5 处主题选择器 + 18 处其他 | 632/661/694/720/750 行 |
| Vite dev server 正常提供 CSS | ✅ HTTP 200 | curl 验证通过 |

**修复文件**: `frontend/src/globals.css`（5 处替换：`root` → `sidebar`）  
**影响主题**: blue / dark-minimal / warm / nature / liquid（五套主题侧边栏渐变/玻璃效果现在生效）

---

### Bug 3: favicon.ico 404

| 检查项 | 结果 | 证据 |
|--------|------|------|
| HTTP 状态码 | ✅ 200（曾 404） | `curl -s -o /dev/null -w "%{http_code}" localhost:5173/favicon.svg` |
| Content-Type | ✅ `image/svg+xml` | 正确的 MIME 类型 |
| 文件大小 | ✅ 504 bytes | 有效 SVG |
| HTML `<link>` 标签 | ✅ 存在 | `<link rel="icon" type="image/svg+xml" href="/favicon.svg" />` |
| SVG 内容 | ✅ CT 品牌图标 | 渐变色背景 + "CT" 文字 |

**修复文件**: `frontend/public/favicon.svg`（新建） + `frontend/index.html`（添加 link）

---

## 额外发现

### ⚠️ TypeScript 构建错误（3 个未跟踪文件）

`npm run build` 存在 TypeScript 编译错误，来自以下**未跟踪的新文件**（WIP 功能，非本次修复引入）：

| 文件 | 问题 |
|------|------|
| `src/components/TriagePanel.tsx` | 引用 `triagePlanFailures`/`triageDraftDefect`（API 不存在） |
| `src/pages/requirement/ReviewPage.tsx` | 引用 `Filter` 图标、`fetchReviewState`/`reviewCase`/`reviewImportCases`（不存在） |
| `src/pages/testcase/CategoryManagerDialog.tsx` | 引用 `createDomain`/`createModule` 等 API + 类型（不存在） |

**影响**: Dev server 不受影响（Vite 使用 esbuild，不做类型检查），但 `npm run build` 生产构建会失败。  
**建议**: 这些文件属于其他 feature 分支的 WIP，应在其对应批次中补全 API 和类型定义后再合入。

---

## 综合评估

| 维度 | 评分 | 说明 |
|------|------|------|
| Bug 1（500 错误） | ✅ 已修复 | API 正常返回，类型转换正确 |
| Bug 2（CSS 选择器） | ✅ 已修复 | 五套主题侧边栏样式生效 |
| Bug 3（favicon 404） | ✅ 已修复 | favicon 正常提供，HTML 正确引入 |
| API 全量冒烟 | ✅ 通过 | users/roles/permissions 均正常 |
| 前端页面加载 | ✅ 通过 | HTML 结构正确，模块正常服务 |

**QA 判决**: ✅ **PASS** — 三个修复均经过端到端 HTTP 验证，可以交付用户进行浏览器验收。

---

## 修复文件清单

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `backend/app/schemas/system.py` | 修改 | MenuOut 添加 sort 字段 float→int 强制转换 |
| `frontend/src/globals.css` | 修改 | 5 处 data-sidebar="root" → "sidebar" |
| `frontend/index.html` | 修改 | 添加 favicon.svg link |
| `frontend/public/favicon.svg` | 新建 | CT 品牌 SVG favicon |
| `frontend/vite.config.ts` | 临时修改 | proxy target 8000→8001（8000 端口僵尸进程需重启清除） |
