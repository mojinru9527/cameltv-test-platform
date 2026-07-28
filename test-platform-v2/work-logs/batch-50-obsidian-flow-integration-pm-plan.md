# Batch 50 — PM Plan

> **PM (🟨)** | Date: 2026-07-28

## 规格摘要

**原始需求**: 
- 主应用 UI 追上 ThemeLab Obsidian Flow 视觉效果（PRD US-1/2/3）
- 修复后端 API 500 错误（PRD US-4）
- 5 个 Slice，覆盖 10+ 核心页面

**目标时间**: 本 batch 内完成（4-6 个 30-60 分钟切片）

---

## 开发任务

### [x] Task 0: 后端 DB Schema 修复（前置任务—已完成）
**描述**: 修复 SQLAlchemy Model 与 SQLite 数据库列不同步导致的 API 500 错误
**验收标准**:
- `/api/v1/environments` 返回 200
- `/api/v1/test-cases` 返回 200
- `/api/v1/requirements` 返回 200
- `/api/v1/test-plans` 返回 200
- `alembic heads` 单头，无冲突
**涉及文件**:
- `backend/alembic/versions/*.py` — 迁移执行 + stamp
- SQLite DB — ALTER TABLE 补列
**状态**: ✅ 已完成（上一 session 紧急修复）

### [ ] Task 1: 基础组件替换 — 页面内 shadcn → @/ui 基元
**描述**: 将已接入 Obsidian Flow 的 7 个页面的内部 shadcn 组件替换为 `@/ui` 基元组件
**验收标准**:
- 页面内所有 `<Button>` 从 `@/components/ui/button` 改为 `@/ui` Button
- 页面内所有 `<Badge>` 从 `@/components/ui/badge` 改为 `@/ui` StatusBadge
- 页面内 `<Input>` 从 `@/components/ui/input` 改为 `@/ui` Input
- 卡片/面板添加 `.ui-surface` 或 `.ui-glass` 类
- `npm run typecheck` 零错误
**涉及文件**:
- `frontend/src/pages/workbench/index.tsx` — Button/Badge 替换
- `frontend/src/pages/testcase/index.tsx` — Button/Badge/Input 替换
- `frontend/src/pages/testplan/index.tsx` — Button/Badge 替换
- `frontend/src/pages/requirement/index.tsx` — Button/Badge 替换
- `frontend/src/pages/defect/index.tsx` — Button/Badge 替换 + StatusBadge 用于缺陷等级
- `frontend/src/pages/report/index.tsx` — Button/Badge 替换
- `frontend/src/pages/trace/index.tsx` — Button/Badge/Input 替换
**参考**: PRD US-1 / Design Spec §1

### [ ] Task 2: 语义组件接入
**描述**: 在核心页面接入 MetricStrip、SpatialChain、StatusBadge 等 v49 语义组件
**验收标准**:
- 工作台页面顶部显示 MetricStrip（合格率/覆盖率/缺陷数/通过率）
- 追溯页面使用 SpatialChain（需求→用例→计划→执行→缺陷→报告链）
- 缺陷页面使用 StatusBadge（P0/P1/P2/P3 彩色缺陷等级标记）
- Inspector 面板集成到详情页（测试计划详情 / 需求详情）
**涉及文件**:
- `frontend/src/pages/workbench/index.tsx` — MetricStrip
- `frontend/src/pages/trace/index.tsx` — SpatialChain
- `frontend/src/pages/defect/index.tsx` — StatusBadge
- `frontend/src/pages/testplan/PlanDetail.tsx` — Inspector（可选）
- `frontend/src/pages/requirement/ReviewPage.tsx` — Inspector（可选）
**参考**: PRD US-2

### [ ] Task 3: 未接入页面 Obsidian Flow 化
**描述**: 当前 0 Obsidian Flow 接入的页面添加 ObsidianListPage 布局和基础组件替换
**验收标准**:
- Environment 页面使用 `useObsidianPage` + ObsidianListPage 布局
- 其他未接入页面（apitest, uitest, special, schedule, system, project, notify, dataset, integration, knowledge, agent-workbench, perftest, release-bundles, mindmap）中至少 5 个核心页面接入 ObsidianListPage
- 接入页面内部 Button/Badge 替换为 `@/ui` 基元
- `npm run build` 成功
**涉及文件**:
- `frontend/src/pages/environment/index.tsx` — 优先（之前完全未接入）
- `frontend/src/pages/apitest/index.tsx` — 高优先级
- `frontend/src/pages/uitest/index.tsx`
- `frontend/src/pages/schedule/index.tsx`
- `frontend/src/pages/system/index.tsx`
- `frontend/src/pages/project/index.tsx`
**参考**: PRD US-1 / US-3

### [ ] Task 4: PageShell 统一页面框架
**描述**: 将页面自定义 Header 替换为 PageShell 统一壳
**验收标准**:
- 至少 5 个列表页使用 PageShell 替代自建 Header
- PageShell 提供面包屑、标题、操作区、状态线
- 与 ObsidianListPage 视觉一致
**涉及文件**:
- `frontend/src/pages/testcase/index.tsx` — 替换 PageHeader
- `frontend/src/pages/testplan/index.tsx` — 替换 PageHeader
- `frontend/src/pages/requirement/index.tsx` — 替换 PageHeader
- `frontend/src/pages/defect/index.tsx` — 替换 PageHeader
- `frontend/src/pages/environment/index.tsx` — 替换 PageHeader
**参考**: PRD US-3

### [ ] Task 5: ThemeLab 路由入口（前置任务—已完成）
**描述**: 确保 ThemeLab 可从主应用导航访问
**验收标准**:
- `/theme-lab` 路由可访问
- theme-lab.css 已在 main.tsx 导入
- Vite build 包含 ThemeLab chunk
**涉及文件**:
- `frontend/src/router/index.tsx` — 路由
- `frontend/src/main.tsx` — CSS 导入
**状态**: ✅ 已完成

---

## 质量要求

- [ ] 响应式（Desktop + Tablet）
- [ ] `npm run typecheck` 零错误
- [ ] `npm run build` 成功
- [ ] 无 console 报错/告警
- [ ] `ruff check app --select F821` 零错误
- [ ] Alembic 单头验证
- [ ] 关键用户路径可走通（Workbench → TestCase → TestPlan → Report）
