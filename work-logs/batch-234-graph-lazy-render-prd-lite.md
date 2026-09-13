# Batch 234 — GraphTab Lazy Render Fix（轻量）

> **Product (🟦)** | Date: 2026-09-13 | Status: Approved

mode: light  
豁免理由: 仅修复现有知识图谱 Tab 在隐藏挂载后未初始化 vis-network 的缺陷，不引入新行为、新接口、新配置或新依赖。  
非目标: 不改图谱 API/数据结构/权限/过滤语义；不新增依赖；不做视觉重设计；不在本批处理 C124-1 生产知识导入。

## 1. 问题陈述

真实浏览器复测发现：知识图谱接口已返回 200 个节点、199 条关系，页面统计也显示 `节点 200/200`，但图谱容器内没有 `.vis-network` 或 `canvas`，`networkRef.current` 始终为 `null`。根因是 GraphTab 可能先在隐藏的 `TabsContent` 中挂载；此时 vis-network 初始化没有可用尺寸，后续 Tab 可见时又没有重新初始化。结果是用户看到空白画布，`C27-C2` 无法验证“200 节点渲染 <3s”。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 200 节点图谱 canvas 初始化 | 0 canvas | ≥1 canvas，vis-network 实例存在 | 本批浏览器回归 |
| 图谱页面渲染耗时 | 无法测量 | < 3000 ms | 本批本地全栈 |
| GraphTab 相关回归 | 现状测试未覆盖隐藏→可见 | 新增 Vitest 覆盖并通过 | 本批 QA |

## 3. 非目标（本次不做）

- 不修改 `/knowledge/graph/view` API、实体/关系数据结构或权限。
- 不新增第三方依赖；继续使用现有 `vis-network` / `vis-data`。
- 不改变图谱 Tab 的整体视觉、筛选或 toolbar 交互。
- 不执行 C124-1 的 147 页/3526 图片生产导入。

## 4. 用户故事 + 验收标准

- As a 测试平台用户, I want 打开“图谱”Tab 时立即看到已加载的节点图, so that 我可以查看关系与执行后续分析。
- 验收：Given GraphTab 曾在隐藏容器中挂载且已有 200 节点数据 / When 图谱 Tab 变为可见 / Then 初始化 vis-network 并出现 canvas，控制台无错误，完整页面渲染 < 3s。

## 5. 技术考量

- 现有 effect 只在 `[graphData]` 变化时执行；容器从 0×0 变为可见不会触发。
- 修复应使用 `ResizeObserver` 在容器首次获得非零尺寸时初始化，并保留卸载清理与 StrictMode 安全。
- 需要补一个“先隐藏/零尺寸，后变可见”的组件测试，避免后续再次回归。