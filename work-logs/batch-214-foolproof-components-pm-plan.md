# Batch 214 — PM Plan (foolproof-components)
> **PM (🟨)** | Date: 2026-09-03

## 规格摘要
**原始需求**: PRD §2/§4 —— 傻瓜化组件层（PageIntro/TermTip/EmptyStateGuide/StepWizard/AskAi MVP）+ 核心 6 页落地；小白走查。
**目标时间**: 本批（前端为主）。**范围**: `test-platform-v2/frontend`（后端无改动，AskAi 为前端内容表 MVP）。

## 开发任务
### [ ] Task 1: 傻瓜化组件库 `components/foolproof/`
**描述**: 新建 `PageIntro` / `TermTip` / `EmptyStateGuide` / `StepWizard` / `AskAiButton` 五个可复用组件（shadcn 语义类 + `ui/tooltip` + `ui/dialog` + `ui/button`）。
**验收**: typecheck/lint 绿；每个组件有 Vitest（渲染 + 交互）。
**涉及文件**: `src/components/foolproof/*.tsx`、`src/lib/terminology.ts`、`src/lib/page-explanations.ts`

### [ ] Task 2: 核心页面落地
**描述**: 在 我的待办 / 用例服务 / 报告中心 / 缺陷管理 / 知识中心 / 资产与更多 六页插入 `PageIntro` + `EmptyStateGuide`（保持原 `EmptyState` 兜底）；含引擎词文案加 `TermTip`。
**验收**: 每页一句话；空列表显示三步教学；`npm test` 绿。
**涉及文件**: 各页面 `index.tsx`、`components/foolproof/*`

### [ ] Task 3: AskAi 助手 MVP + 全局入口
**描述**: `AskAiButton`（问号）挂 `MainLayout`，弹层按路由返回 `page-explanations.ts` 内容；未知路由兜底。
**验收**: 任意页点问号有业务回答；无路由 404。
**涉及文件**: `MainLayout.tsx`、`AskAiButton.tsx`、`page-explanations.ts`

### [ ] Task 4: StepWizard + 首个演示
**描述**: `StepWizard` 3 步组件 + 一个演示入口（版本任务创建：放东西→AI 出方案→确认，简化版）。
**验收**: 3 步可前进/后退；完成回调。
**涉及文件**: `StepWizard.tsx`、一个演示页/组件

### [ ] Task 5: QA + 工件 + 路线图 §5
**描述**: 硬门禁 + 小白走查 + QA 报告/Leader/看板 + roadmap §5 B4 行 + C-CONDITIONS + B3 状态改 ✅。
**验收**: 门禁全绿；roadmap B3→✅、B4 状态更新。

## 质量要求
- [x] 响应式  - [ ] OpenAPI 同步（无后端接口）  - [x] 单元测试覆盖
- [ ] 无障碍（ARIA/键盘/焦点）  - [ ] 无 console 报错  - [ ] 小白走查卡点记录
