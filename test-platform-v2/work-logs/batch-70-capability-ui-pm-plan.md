# Batch 70 — PM Plan（能力产品化 UI 补齐）

> **PM (🟨)** | Date: 2026-08-03

## 开发任务

### [ ] Task 1: API Token 管理 UI（Slice 1）
**描述**: 新增 `frontend/src/api/token.ts`（list/create/update/delete）；系统管理页新增 `TokensTab.tsx`
（列表/新建对话框/编辑/删除 + 确认）；注册菜单与命令面板；权限不足 403 提示。
**验收标准**: 浏览器操作全流程；Vitest（组件 + client）；`seed.py _MENUS` 与 `CommandPalette` 同步。
**涉及文件**: `frontend/src/api/token.ts`、`frontend/src/pages/system/TokensTab.tsx`、`system/index.tsx`、`seed.py`、`CommandPalette`

### [ ] Task 2: 用例导入导出 UI（Slice 2）
**描述**: `testcase.ts` 增加 import/export 函数；testcase 页面工具栏加「导入（Excel/XMind）」「导出」入口；
CaseDrawer 集成导入结果反馈；导入模板下载链接。
**验收标准**: Excel 导入入库、导出 xlsx 下载；Vitest mock 覆盖。
**涉及文件**: `frontend/src/api/testcase.ts`、`frontend/src/pages/testcase/**`

### [ ] Task 3: 质量追溯下钻 UI（Slice 3）
**描述**: trace 页覆盖率卡片/列表可点击下钻：需求文档 → 用例列表 → 用例详情（执行/缺陷链）；复用
`trace.ts`（coverage/requirement/case）。
**验收标准**: 下钻链路浏览器证据；Vitest。
**涉及文件**: `frontend/src/pages/trace/index.tsx`、`frontend/src/api/trace.ts`

### [ ] Task 4: 报告模板管理 UI（Slice 4）
**描述**: 报告页模板区新增「模板管理」：新建/编辑/删除模板对话框，联动 `reportTemplate.ts`。
**验收标准**: CRUD 浏览器 + API 证据；Vitest。
**涉及文件**: `frontend/src/pages/report/**`、`frontend/src/api/reportTemplate.ts`

### [ ] Task 5: QA + Leader + 看板 + PR
**描述**: 汇总证据；前端 typecheck/build、受影响 Vitest、后端受影响 pytest；走 push 授权 → PR → 二次确认 → 合入。
**验收标准**: QA PASS + Leader APPROVED。
**涉及文件**: `work-logs/batch-70-capability-ui-{qa-report,leader-verdict}.md`、`kanbans/DEV-batch-70-capability-ui.md`

## 质量要求
- [ ] `npm run typecheck && npm run build`、受影响 Vitest、后端受影响 pytest 全绿
- [ ] 无调试遗留、无硬编码密钥；UI 遵循 cameltv-ui-conventions
- [ ] 菜单/命令面板/权限三处同步；每个 PASS 带浏览器/API 证据
