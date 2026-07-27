# Batch 43 — Design Spec
> **Design (🎨)** | Date: 2026-07-25 | Status: 走查就绪

## 0. 技术体系确认

本平台采用: **shadcn/ui + Radix + Tailwind + CVA**
Token 走语义类: `bg-muted` / `text-muted-foreground` / `border` / `variant`
主题: 5 套 — default / dark / blue / green / purple (ThemeLab)
⚠️ **不是 Ant Design** — 所有组件/Token 规格走 Tailwind 语义类。

## 1. 本次 Design 角色

batch-43 是功能验收 batch，Design 部门职责为：
1. **反向回填** — 对 Tier 1 核心模块的现有 UI 做设计走查
2. **Red Flags 比对** — 逐条检查 `cameltv-ui-conventions` 红旗清单
3. **设计债记录** — 发现的 UI 问题按 P0–P3 定级，不阻塞功能验收

## 2. Tier 1 核心模块设计走查纲要

### 2.1 测试用例 (testcase) 页面

| 组件 | 预期行为 | 走查点 |
|------|---------|--------|
| 用例列表 | 表格 + 分页 + 搜索栏 | 空态文案、加载骨架屏、分页组件一致性 |
| 用例表单 | Dialog/Sheet 弹窗 | 标题必填校验、富文本编辑器工具栏、图片上传 |
| 批量操作 | 多选 + 工具栏 | 未选中时按钮 disabled、批量删除确认弹窗 |
| 导入导出 | 文件上传 + 下载 | 上传进度、格式错误提示、导出 loading |

### 2.2 测试计划 (testplan) 页面

| 组件 | 预期行为 | 走查点 |
|------|---------|--------|
| 计划列表 | 卡片/表格 | 进度百分比颜色映射、执行状态徽标 |
| 用例选择 | 树 + 搜索 + 多选 | 已选用例高亮、去重提示 |
| 执行进度 | 进度条 + 统计 | 数据与后端一致、刷新按钮 |

### 2.3 API 测试 (apitest) 页面

| 组件 | 预期行为 | 走查点 |
|------|---------|--------|
| API 资产列表 | 表格 + Swagger 导入按钮 | 方法徽标颜色 (GET=green/POST=blue/...)、URL 截断 |
| 请求编辑器 | 参数/Header/Body 三 Tab | JSON 格式化、语法高亮、响应展示 |
| 执行结果 | 状态码 + 耗时 + 断言 | PASS/FAIL 颜色区分、错误信息可读性 |

### 2.4 UI 测试 (uitest) 页面

| 组件 | 预期行为 | 走查点 |
|------|---------|--------|
| 用例列表 | 关联功能用例 | 截图预览缩略图、状态徽标 |
| 执行日志 | Terminal 风格 | 自动滚动、关键字高亮 (ERROR/PASS) |

### 2.5 测试报告 (report) 页面

| 组件 | 预期行为 | 走查点 |
|------|---------|--------|
| 报告详情 | 统计卡片 + 图表 + 明细 | 通过率环形图、趋势折线图、失败用例列表 |
| 导出 | PDF/HTML | 导出按钮 loading、文件下载 |

### 2.6 缺陷管理 (defect) 页面

| 组件 | 预期行为 | 走查点 |
|------|---------|--------|
| 缺陷列表 | 表格 + 筛选 | 严重级颜色映射 (P0=red/P1=orange/...)、状态流转按钮 |
| 缺陷详情 | 描述 + 关联用例/报告 | 关联跳转链接、附件预览 |

## 3. Red Flags 清单比对（来源: cameltv-ui-conventions）

| # | Red Flag | 本次走查 |
|---|----------|---------|
| RF1 | 硬编码色值代替 Tailwind 语义类 | 搜索 `#[0-9a-fA-F]{6}` 在组件中 |
| RF2 | 缺少 dark: 变体导致深色模式异常 | 检查 `dark:` 前缀覆盖 |
| RF3 | 状态标签颜色非四级可辨 (P0/P1/P2/P3) | 检查 SeverityBadge 组件 |
| RF4 | 弹窗/Sheet 在移动端占满屏 | 检查 responsive Dialog |
| RF5 | 加载态只有 spinner 缺少骨架屏 | 检查 Table/List loading |
| RF6 | 空态缺少引导文案 | 检查 Empty state 组件 |
| RF7 | 表单校验仅后端（前端无即时反馈） | 检查表单组件 zod/react-hook-form |
| RF8 | 按钮无 loading 态导致重复提交 | 检查提交按钮 `isLoading` prop |
| RF9 | 图片无 alt / 交互元素无 aria-label | 检查 a11y |
| RF10 | Tailwind class 顺序不一致 | 检查 className 组织 |

## 4. 设计签核

本次 Design 部门走查结论将在 QA 阶段逐页执行时与截图证据一起记录。当前阶段产出走查纲要，具体发现问题记录在 QA 报告中。

结论: **有条件通过** — 功能验收为主的 batch，UI 问题按 P2/P3 记录不阻塞；P0/P1 UI 缺陷（白屏/崩溃/无法操作）必须修复。
