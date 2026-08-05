# Batch 92 — PM Plan（蓝湖证据包审核 UI）

> **PM (🟨)** | Date: 2026-08-05

## 规格摘要

**原始需求**: 证据包任务/详情/审核/导入前端页面（PRD §1–§5）。**目标时间**: 2 个工作日。

## 开发任务

### Slice 1: 后端 seed 菜单（15min）
- `seed.py` 增补 `menu:lanhu_evidence`（/lanhu-evidence，FileTextOutlined，sort 23）+ `_TESTER_MENUS`
- 验收：重启后端后 `/system/menus` 返回该菜单（admin/tester）

### Slice 2: 状态标签纯函数（TDD）
- `pages/lanhu-evidence/labels.ts`：JOB_STATUS/STAGE/CAPTURE/OCR/REVIEW 中文映射 + tone
- `pages/lanhu-evidence/labels.test.ts`：全映射断言
- 验收：vitest 通过

### Slice 3: 任务列表页（index.tsx）
- PageHeader + 新建任务 Dialog（URL + 采集选项 + 导入选项）+ AsyncState 表格（ID/文档/状态/阶段/页面/时间/操作）
- 操作：详情跳转、取消/重试/删除（run 权限，AlertDialog 确认）
- 验收：typecheck；Playwright 截图

### Slice 4: 任务详情页（JobDetail.tsx）
- 摘要卡（状态/阶段/页面统计/import_ready）+ 页面表（名称/文件夹/捕获/OCR/审核/操作）
- 页面详情 Dialog（merged_text + 截图）+ 审核 Dialog（通过/驳回+原因）
- 导入按钮（success 且 import_ready，import 权限）→ 导入 Dialog（三目标勾选）
- 验收：typecheck；Playwright 截图

### Slice 5: 路由注册 + QA 门禁
- router 增 `/lanhu-evidence` 与 `/lanhu-evidence/:id`
- typecheck/build/vitest/后端 pytest/Playwright 冒烟 + 截图

## 质量要求

- [x] 响应式（列表/详情可用，沿用 batch-89 基线）
- [x] 无障碍：表单 label、图标按钮 aria-label、弹窗焦点
- [x] 单元测试：labels 映射 + 组件冒烟
- [x] 无 console 报错
- [x] 中文状态标签（不裸英文枚举）
