# Batch 89 — Design Spec（响应式回归契约 + 仓库边界同步）

> **Design (🎨)** | Date: 2026-08-05 | Status: 就绪

## 0. 技术体系确认

- 前端：React 18 + TS + Tailwind + shadcn/ui（Radix）；响应式基线以 Tailwind 断点（md 768 / lg 1024）为准。
- E2E：Playwright（`e2e/`，chromium，BASE_URL=dev server）；本批新增响应式 spec。
- 仓库边界：`repo-boundaries.json` 为唯一事实源；`validate_repo_boundaries.py --check` 门禁。

## 1. 响应式回归契约（C55-5-P2）

### 1.1 视口与页面矩阵

| 视口 | 覆盖页面 | 断言 |
|------|---------|------|
| tablet 768×1024 | 登录 / 工作台 / 用例列表 / 测试计划 / 报告 / 缺陷 / 定时任务 / 知识中心 | 无水平溢出；主操作可点；导航可见 |
| mobile 390×844 | 同上 | 无水平溢出；侧边栏/弹窗可开合；表单可输入 |

### 1.2 判定规则

- 水平溢出：`document.documentElement.scrollWidth <= window.innerWidth + 1`（±1px 容差）
- 可操作性：主按钮（如“新建用例”“执行计划”）在视口内且 `isVisible && isEnabled`；点击后无 JS 报错
- 遮挡：关键元素 boundingBox 不超出视口且不被固定层遮挡（抽查）
- console error 计数 = 0（回归断言）

### 1.3 缺陷定级

| 级别 | 定义 | 处理 |
|------|------|------|
| P1 | 核心页面无法操作（按钮不可点/表单不可用） | 本批必修 |
| P2 | 明显溢出/遮挡，有替代路径 | 本批修复 |
| P3 | 轻微间距/裁剪，不影响操作 | 记录或顺手修 |

## 2. 仓库边界同步（C64-2）

- 删除：根目录 `pective pipeline — Agent Team work-logs + 10 TypeScript fixes + domain CRUD API`（及尾字符 `\uF022` 变体）
- `repo-boundaries.json` shared 段：移除这两条路径；保留规则说明的「历史误提交已删除（batch-89）」注释更新
- 门禁：`validate_repo_boundaries.py --check` 退出码 0

## 3. WARN 审计契约（C81-1）

- 执行：`run-warn-audit.ps1 -BatchLabel "batch-89"`
- 期望：HARD=0、WARN=209（持平）或更少、新增类别=0
- 若新增类别/文件：归因说明 + Leader 复核后刷新基线（禁止静默刷新）

## 4. 设计 QA 走查发现

### ⚪ P3-01 既有 e2e 仅 Desktop 视口
`playwright.config.ts` 只有一个 chromium desktop project。→ 响应式 spec 内按测试设置 viewport（不改全局配置，避免破坏既有用例）。

## 5. 设计签核

结论：**通过** — 无新组件/布局设计，仅回归契约与边界同步；P3-01 按 spec 内 viewport 处理。
