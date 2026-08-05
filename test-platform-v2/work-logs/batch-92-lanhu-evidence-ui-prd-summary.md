# Batch 92 — PRD Summary（蓝湖证据包审核 UI 产品化）

> **Product (🟦)** | Date: 2026-08-05 | Status: Review

## 0. 批次模式判定（C75-1 强制）

```markdown
mode: full
判定理由: 新增前端页面/路由/菜单（新行为）与后端 seed 菜单变更 → 完整批次（六部门）。
```

## 1. 问题陈述

Batch 88 已闭环蓝湖证据包链路（项目级链接自动发现 → 截图+OCR → 质量门禁 → 导入需求/RAG/Wiki），但**只有 API**：
创建任务、查看进度、逐页审核（`lanhu_evidence:review`）、触发导入全部要手调接口。设计稿→需求的日常工作流缺少可视化操作面，
非技术用户无法完成「采集→审核→导入」闭环。

## 2. 成功指标

| 指标 | 基线 | 目标 |
|------|------|------|
| 任务管理 | 无 UI | `/lanhu-evidence` 列表：分页/状态/页面统计/新建（URL+选项） |
| 任务详情 | 无 UI | `/lanhu-evidence/:id`：摘要+质量卡+页面表+逐页查看/审核+导入 |
| 权限门控 | — | view/run/review/import 四档权限分别控制可见与操作 |
| 门禁 | — | typecheck/build/vitest 绿；后端 seed 变更 pytest 绿；Playwright 冒烟截图 |

## 3. 非目标（本次不做）

- **不做批量审核**：证据包页面审核为逐页人工审核（与 AI 产物批量采纳不同，后者归 batch-94）。
- **不改采集链路**：job_runner/lanhu_provider 保持 batch-88 交付。
- **不做移动端专项**：响应式沿用 batch-89 基线（列表/详情可用即可）。

### C 条件纳入/豁免

| C 条件 | 处理 |
|--------|------|
| C75-1/2/3、C76-2、C78-1、C86-1 | 本批遵守 |
| C26KB-C3 / C91-1 | 不纳入（AI 产物批量审核归 batch-94）；本批证据包页面为逐页审核，不属于 C7 检查点范围 |

## 4. 用户故事 + 验收标准

- As a **测试/产品人员**, I want 在网页上创建蓝湖证据包任务、看进度、审核页面并导入，so that 设计稿→需求工作流不依赖 API。
  - Given 我有 lanhu_evidence:view/run 权限，When 打开 /lanhu-evidence，Then 看到任务列表并可新建任务。
  - Given 任务已成功（import_ready），When 打开详情并逐页审核无 OCR 页，Then 审核通过后质量门禁放行并可一键导入需求/RAG/Wiki。
  - Given 我无 review/import 权限，When 打开详情，Then 审核与导入按钮不可见。

## 5. 技术考量

- 复用既有 `src/api/lanhuEvidence.ts`（完整客户端）与后端 `/api/v1/lanhu-evidence/*`。
- 后端 seed 增补 `menu:lanhu_evidence`（路径 /lanhu-evidence）并加入 tester 菜单；前端菜单由 menu_service 自动下发。
- 状态/阶段/审核全部中文映射（`labels.ts` 纯函数 + vitest），Badge 用语义 tone。
- 截图通过 cookie 同源 `<img src="/api/v1/lanhu-evidence/assets/{id}">` 展示（httpOnly cookie 自动携带）。
- 权限：`lanhu_evidence:view` 列表/详情；`:run` 新建/取消/重试/删除；`:review` 审核；`:import` 导入。
