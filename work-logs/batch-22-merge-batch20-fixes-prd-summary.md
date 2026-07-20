# Batch 22 — 合并 Batch-20 七个缺陷修复 — PRD Summary

## 问题陈述

Batch-20（`feature/batch-20-fix-seven-gaps`）对 batch-19 审计发现的 7 个缺陷已完成 Agent Team 六部门流水线（含 QA 8/8 PASS + Leader APPROVED），commit `4606e85` + `2a12804` 已推送至远程分支，但 **PR 未创建、代码未合入 develop**。

当前 `feature/batch-21-unimplemented-gaps` 分支基于 develop（不含 batch-20 修复），导致：

1. **AssetTab.test.tsx 测试断裂**：测试引用 `aria-label="向左查看更多服务"`、`data-testid="service-tabs-viewport"` 等属性，但 `AssetTab.tsx` 源码未添加这些属性，`getByRole`/`getByTestId` 全部抛异常
2. **ApiCaseTab.tsx 网络错误静默**：catch 块只 toast 不弹 Modal，用户看不到错误详情
3. **可访问性缺口**：`prefers-reduced-transparency` 完全缺失，`prefers-reduced-motion` 全局 CSS 块缺失
4. **视觉不一致**：sonner toast 无 per-theme 覆盖
5. **CaseDrawer label-id 断裂**：`<label htmlFor="case-steps">` 在 formatted 模式下无匹配 `id`
6. **用例列表高度不适应分页**：`min-h-[600px]` 静态值，20/50/100 条切换时出现大片空白或溢出

## 成功指标

- [ ] `AssetTab.test.tsx` 2 个测试全部通过（无 `getByRole`/`getByTestId` 异常）
- [ ] `ApiCaseTab.tsx` 网络错误时弹出 Response Modal 显示错误信息
- [ ] `theme-provider.tsx` 检测 `prefers-reduced-transparency` 并设置 `data-reduced-transparency`
- [ ] `globals.css` 含 `@media (prefers-reduced-motion: reduce)` 全局块
- [ ] `globals.css` 含 `[data-sonner-toaster]` per-theme 覆盖
- [ ] `CaseDrawer.tsx` formatted 模式 `<pre>` 有 `id="case-steps"`
- [ ] `testcase/index.tsx` 表格高度随 pageSize 动态变化

## 非目标

- 不新增功能
- 不改变 batch-20 已审批的修复方案
- 不修改后端代码

## 用户故事 + 验收标准

### US-G1 — 透明偏好适应
**Given** 用户在操作系统启用了"减少透明度"  
**When** 页面加载或系统偏好变化  
**Then** 所有玻璃态组件（card-lift, sidebar, dialog, sheet, select, dropdown, badge, tooltip, sidebar-footer）降级为不透明 `background: var(--card)` + `backdrop-filter: none`

### US-G2 — 动画偏好适应
**Given** 用户在操作系统启用了"减少动画"  
**When** 页面加载  
**Then** 全局禁用 CSS 动画/过渡（`.shimmer` 遮罩改为静态）

### US-G3 — Toast 主题适配
**Given** 用户切换了主题（晶穹/黑域/列阵/软体/液境）  
**When** 系统弹出 toast 通知  
**Then** toast 背景/边框/文字颜色与当前主题一致，液境主题使用毛玻璃效果

### US-G4 — 服务 Tab 无障碍滚动
**Given** API 测试页面加载了多个服务  
**When** 服务 Tab 超出可视区域  
**Then** 左右滚动按钮有明确 `aria-label`（"向左查看更多服务"/"向右查看更多服务"），视口容器有 `data-testid="service-tabs-viewport"`，测试可正确定位元素

### US-G5 — 测试步骤 label-id 关联
**Given** 用户在用例编辑抽屉查看 formatted 模式的步骤  
**When** 点击 `<label htmlFor="case-steps">` 标签  
**Then** 焦点正确转移到对应的 `<pre>` 元素（formatted 模式）或 `<Textarea>`（JSON 模式）

### US-G6 — 网络错误弹窗
**Given** 用户在接口用例 Tab 执行单条用例  
**When** 请求因网络错误失败  
**Then** 自动弹出 Response Modal 显示错误详情（而不仅是 toast）

### US-G7 — 列表高度自适应分页
**Given** 用户在用例列表页切换 pageSize  
**When** 选择 20/50/100 条每页  
**Then** 表格容器高度自动调整（~650px/~1550px/~3050px），避免大片空白或溢出

## 涉及文件

| 文件 | 修复内容 |
|------|---------|
| `frontend/src/components/theme-provider.tsx` | G1: reduced-transparency 检测+监听 |
| `frontend/src/globals.css` | G2: reduced-motion 块; G3: sonner toast 覆盖 |
| `frontend/src/pages/apitest/components/AssetTab.tsx` | G4: aria-label + data-testid |
| `frontend/src/pages/apitest/components/AssetTab.test.tsx` | G4: scrollBy 240→200 |
| `frontend/src/pages/testcase/CaseDrawer.tsx` | G5: pre id="case-steps" |
| `frontend/src/pages/apitest/components/ApiCaseTab.tsx` | G6: catch 块开 Modal |
| `frontend/src/pages/testcase/index.tsx` | G7: 动态 min-h |
