# Batch 50 — PRD Summary

> **Product (🟦)** | Date: 2026-07-28 | Status: Draft

## 1. 问题陈述

v49 交付了完整的 Obsidian Flow UI 主题系统（ThemeLab + 6 主题变体 + 语义组件库），但主应用页面**实际渲染效果与 ThemeLab 演示完全不同**。同时，后端数据库 schema 与 ORM 模型不同步，导致大量 API 500 错误。

### 证据

**UI 层面**（已通过代码走查确认）：
- ThemeLab 呈现完整暗色玻璃态 UI（`.theme-obsidian-flow` CSS 变量 + BEM 类 + `SpatialGlassPrototype` 交互原型）
- 主应用仅 7/23 页面使用了 Obsidian Flow 外层包装器（`ObsidianListPage`/`ObsidianWorkbench`），内部仍然渲染标准 shadcn/ui 组件
- `@/ui` 目录下的 Obsidian Flow 语义组件（`PageShell`, `SpatialChain`, `Inspector`, `MetricStrip`, `StatusBadge`）和基础组件（`Button`, `Badge`, `Input`, `Progress`）已完整实现但**零页面导入使用**
- `.ui-surface`、`.ui-glass`、`.ui-btn-primary` 等 Obsidian Flow CSS 类已定义但**零 DOM 元素应用**
- `Environment` 等页面完全没有接入 Obsidian Flow 系统

**后端层面**：
- SQLAlchemy Model 新增 13 列未同步到 SQLite 数据库
- `batch48_requirement_reconcile` Alembic 迁移因 SQLite `batch_alter_table` 非恒定默认值限制而失败
- 5 个关键 API 端点返回 500：`/environments`, `/test-cases`, `/requirements`, `/test-plans`

### 根因

| 问题 | 根因 |
|------|------|
| 主应用 UI ≠ ThemeLab | v49 组件已交付但从未接入页面。页面仍使用 shadcn 组件，Obsidian Flow 组件是**孤儿代码** |
| API 500 | DB Schema 不同步 — 迁移失败后未手动修复缺失列 |

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| Obsidian Flow 语义组件页面接入率 | 0/23 (0%) | ≥10/23 (43%) — 核心页面全覆盖 | 本 batch |
| Obsidian Flow 基础组件替换率 | 0%（全用 shadcn） | 核心页面内 Button/Badge/Input/Progress 全部替换为 `@/ui` 基元 | 本 batch |
| 主应用与 ThemeLab 视觉一致性 | 完全不同（两套 CSS 体系） | 主应用暗色玻璃态与 ThemeLab obsidian-flow 主题视觉一致 | 本 batch |
| API 500 错误数 | 5 端点 | 0 | 本 batch |
| ThemeLab 可访问性 | 无路由 | `/theme-lab` 可正常访问 | ✅ 已完成 |

## 3. 非目标（本次不做）

- **不修改 ThemeLab 自身的 BEM CSS 体系** — ThemeLab 作为主题实验室保持独立，本次目标是让主应用追上 ThemeLab 的视觉效果
- **不做跨主题适配** — 仅聚焦默认 `obsidian-flow` 主题，其他 5 个主题变体（cyberpunk, apple, clay, xlab, liquid-glass）维持现状
- **不重构后端 API 接口签名** — 仅修复数据库 schema 问题
- **不新增功能页面** — 不改动业务逻辑，纯 UI 层组件替换 + 布局调整
- **不引入新 UI 依赖** — 严格使用已有的 `@/ui` 组件和 Tailwind 类

## 4. 用户故事 + 验收标准

### US-1: 主应用全页 Obsidian Flow 暗色玻璃态

**As a** 测试平台用户
**I want** 所有页面在 obsidian-flow 主题下呈现统一的暗色玻璃态视觉（深色背景 + 玻璃面板 + 绿色强调色）
**So that** 主应用视觉效果与 ThemeLab 演示一致，不再出现白屏黑框的割裂感

验收标准：
- Given 用户在 obsidian-flow 主题下访问任意页面, When 页面加载完成, Then 页面整体背景为暗色（`#0b100d` 色系），面板/卡片为玻璃态（`backdrop-blur` + 半透明边框）
- Given 用户在 obsidian-flow 主题下, When 查看页面, Then 所有 Button 使用 `@/ui` 基元（`.ui-btn-primary` 等绿黑色系），非 shadcn 默认蓝色
- Given 用户在 obsidian-flow 主题下, When 查看页面, Then 所有 Badge 使用 `@/ui` 基元（`.ui-badge-success/warning/danger` 等），非 shadcn 默认色板
- Given 环境管理页面, When 页面加载, Then 使用 ObsidianListPage 布局（暗色标题 + 玻璃内容区），与其他已接入页面一致

### US-2: Semantic 组件接入核心页面

**As a** 测试工程师
**I want** 在关键页面看到 v49 的空间链（SpatialChain）和指标条（MetricStrip）
**So that** 质量数据可视化与 ThemeLab 原型一致

验收标准：
- Given 工作台页面, When 加载, Then 顶部显示 MetricStrip（合格率/覆盖率/缺陷数/通过率 等指标卡片）
- Given 追溯页面（/trace）, When 加载, Then 显示 SpatialChain（需求→用例→计划→执行→缺陷→报告 空间链）
- Given 缺陷页面, When 加载, Then 缺陷状态使用 StatusBadge（P0-P3 彩色标记）替代 shadcn Badge

### US-3: PageShell 统一页面框架

**As a** 测试工程师
**I want** 所有页面使用 PageShell 统一壳（含面包屑/操作区/状态线）
**So that** 页面布局一致，减少视觉跳变

验收标准：
- Given 任意列表页, When 加载, Then 页面使用 PageShell 包裹（替代各页面自行实现的 Header）
- Given PageShell, When 页面有数据, Then 面包屑和操作区正确渲染

### US-4: 后端 API 恢复

**As a** 前端用户
**I want** 所有 API 端点正常返回数据
**So that** 页面不再因 500 错误白屏

验收标准：
- Given 前端请求 `/api/v1/environments?project_id=1`, When 后端处理, Then 返回 200 + 环境列表数据
- Given 前端请求 `/api/v1/test-cases`, When 后端处理, Then 返回 200 + 用例列表数据  
- Given 前端请求 `/api/v1/requirements`, When 后端处理, Then 返回 200 + 需求列表数据
- Given 前端请求 `/api/v1/test-plans`, When 后端处理, Then 返回 200 + 计划列表数据

## 5. 技术考量

| 依赖 | 风险 | 缓解 |
|------|------|------|
| `@/ui` 基元组件需与 shadcn 组件 API 兼容 | 替换时 props 不匹配导致编译错误 | Design 阶段逐组件对比 API，Dev 阶段逐文件替换 + typecheck |
| 大量文件同时修改 | 合并冲突风险 | 按页面切片推进，每切片独立 commit |
| Obsidian Flow CSS 类需全局覆盖 | 可能影响未接入页面 | `data-ui-theme="obsidian-flow"` 属性作用域限制 |
| Alembic 迁移在 SQLite 上受限 | `batch_alter_table` 失败 | 直接 ALTER TABLE + stamp head（已验证可行） |

## 6. 上线计划

| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| Slice 1 — 后端修复 | 全部用户 | 5 个 API 端点 200 |
| Slice 2 — 基础组件替换 | 全部用户 | 核心页面 Button/Badge/Input 走 `@/ui` 基元 |
| Slice 3 — 语义组件接入 | 全部用户 | MetricStrip/SpatialChain/StatusBadge 在目标页面可见 |
| Slice 4 — PageShell 统一 | 全部用户 | 至少 5 个页面使用 PageShell |
| Slice 5 — QA + 构建验证 | 全部用户 | typecheck + build 全绿，视觉走查通过 |
