# Batch 214 — PRD Summary：傻瓜化组件层（B4 / foolproof-components）
> **Product (🟦)** | Date: 2026-09-03 | Status: Review | Executor: Codex | 完整批次（前端为主）

## 1. 问题陈述

- 平台重构定位「AI 版本验收工作台」，要求**傻瓜化**：让一个零培训的测试工程师也能用懂平台
  （`docs/platform-refactor/04-foolproof-standards.md` §0）。但当前各页面仍是**模块工具集合**：
  - 列表页空态是「纯空表格」（`EmptyState` 已存在，多为 `暂无数据`），无「三步完成第一个 XX」式教学；
  - 页面标题只有模块名（如「用例服务/报告中心/缺陷管理」），无「一句话说明」，普通用户不知道这页干嘛；
  - 无「术语提示」：用户遇到 `Mission/Contract/Oracle/Run/Evidence` 等引擎词无处可查（03 术语表未在 UI 落地）；
  - 无「步骤向导」：复杂操作（创建版本任务/跑一个版本）没有 3 步向导，直接平铺表单；
  - 无「问我」助手：用户想问「这页干嘛」只能猜，无内嵌提问入口（04 §3：b4 落地 MVP）。
- 路线图 B4 出口标准：**全站列表页空态有教学；问「这页干嘛」有业务化回答**。
- 证据：`04-foolproof-standards.md` §1（十诫）、§3（AI 兜底「问我」）、§4（小白走查门禁）；现有前端仅有通用 `EmptyState`，无 `PageIntro/TermTip/StepWizard/AskAi`。

## 2. 成功指标

| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 列表页空态 | 纯「暂无数据」 | 有「三步完成第一个 XX」空态教学（EmptyStateGuide） | 本批 QA + 小白走查截图 |
| 页面一句话 | 仅模块名 | `PageIntro`（一句话 + 面向测试工程师业务语言） | 核心页面（见 §5） |
| 术语提示 | 无 | `TermTip`（引擎词 → 业务语言 tooltip，词表来自 03 术语） | 用例/报告等含引擎词处 |
| 步骤向导 | 无 | `StepWizard` 3 步向导组件（可复用，首个落地：创建版本任务「放东西→AI 出方案→确认」） | 组件用例 + 走查 |
| 问我助手 | 无 | `AskAi` MVP：每页问号入口，弹层回答「这页干嘛/怎么走」（业务语言） | 组件用例 + 走查 |

## 3. 非目标（本次不做）

- **不做真实 LLM 版权/工程接入**：`AskAi` MVP 用「路由→业务语言解释」的内容映射 + 兜底，非真 AI；真 AI 随 B11（知识管线）/DSH 任务接入，本批只落结构 + 内容表；
- **不做全站所有页面的空态/Intro 全覆盖**：本批先落地**核心 6 页**（我的待办/用例服务/报告中心/缺陷管理/知识中心/资产与更多），其余页面随 B5 死代码清理与后续批次分批补齐（记入交接区）；
- **不做 TermTip 词表全量**：仅覆盖核心页面出现的引擎词（Mission/Contract/Oracle/Run/Evidence/Execution），词表复用 `03-terminology-map.md`；
- **不做埋点**（owner 单用户，用户已取消）；
- **不做 StepWizard 的业务数据编排**：只做可复用 3 步向导 UI 组件，首个演示页用一个真实版本任务的简化流程，完整数据流随 B6/B7；
- **不改后端数据模型**：AskAi MVP 无后端接口，纯前端内容表（本批为「前端为主」）。

## 4. 用户故事 + 验收标准

- As 零培训测试员，I want 空列表时看到「三步完成你的第一个 XXX」，so that 我知道从哪开始。
  - 验收：Given 任一目标列表页为空 / When 打开页面 / Then 显示 EmptyStateGuide（三步 + 每步一句话 + 主按钮/跳转），非空表格。
- As 测试员，I want 页面标题下有一句话说明，so that 我能立刻知道这页干嘛。
  - 验收：Given 打开目标页 / Then PageHeader 下方显示 `PageIntro` 一句话（业务语言，含「服务版本放行哪一环」）。
- As 测试员，I want 鼠标悬停引擎词能看到业务解释，so that 我不被术语劝退。
  - 验收：Given 页面出现 `Mission/Contract/...` / When 悬停 TermTip / Then 显示业务语言解释（tooltip）。
- As 测试员，I want 复杂操作用向导完成，so that 我不用记住一堆字段。
  - 验收：Given 点「创建版本任务」/ Then 进入 3 步 StepWizard（放东西 → AI 出方案 → 确认），每步顶部一句话 + 上一步/下一步。
- As 测试员，I want 每页有「问我」入口，so that 我找不到入口时能问。
  - 验收：Given 打开任意目标页 / When 点问号 / Then 弹窗回答「这页是干嘛的/怎么做」（业务语言）；未知路由给兜底回答 + 引导。

## 5. 技术考量

- **新组件**（`frontend/src/components/foolproof/`，shadcn 语义类，复用 `ui/tooltip`、`ui/dialog`、`ui/button`、`badge`）：
  - `PageIntro.tsx`：`PageIntro({ title, description, icon? })` → PageHeader 下达一句话说明 + 可选链接。
  - `TermTip.tsx`：`TermTip({ term, children })` → tooltip 包裹，词表 `src/lib/terminology.ts`（复制 `03-terminology-map.md` 核心词）。
  - `EmptyStateGuide.tsx`：`EmptyStateGuide({ stepTitle, steps:[{text, action?}], primaryAction? })` → 三步教学卡片。
  - `StepWizard.tsx`：`StepWizard({ steps:[{title, description, content}], onFinish })` → 顶部步骤指示 + Prev/Next。
  - `AskAiButton.tsx`：问号按钮 + `Dialog`；回答来自 `src/lib/page-explanations.ts`（`route → {title, explanation, actions}`）+ 兜底。
- **落地**：在目标 6 页插入 `PageIntro`/`EmptyStateGuide`；`TermTip` 用于含引擎词的文案；`StepWizard` 首个演示页（版本任务创建向导）；`AskAiButton` 挂 `MainLayout` 全局入口（每页问号）+ 内容表。
- **风险**：空态改造需逐页识别当前 EmptyState 用法（部分页为 `DataTable` 内联空态），需保持原空态兜底；AskAi 内容表为骨架，真实回答随后续批次。
- **依赖**：batch-211 基线（03 术语 / 04 傻瓜化规范）；`cameltv-ui-conventions`（shadcn 语义组件）。

## 6. 上线计划

| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 本批合入 main | owner | 核心 6 页有 Intro + 空态教学；AskAi 弹层业务回答；StepWizard 可复用 + 一个演示；小白走查无 P0/P1 卡点 |
| M0 出口（B1–B5） | owner | 登录第一眼即「我的待办」；C 级入口已下架；死代码已清（B5）；列表页空态有教学 |

## 7. 技能使用
- `cameltv-ui-conventions` → shadcn 语义组件 / 四态 / 触控 / 响应式（非测试证据）。
- `cameltv-bug-guard` → 前端 hook / dialog / 路由 改前避坑。
- `cameltv-agent-team` → 完整批次六部门工件流程。

## 小白走查（04 §4 门禁）
- 新用户画像：刚加入 QA、从没用过平台的测试工程师；
- 主任务：登录后 3 分钟内，说出「我的待办」页是干嘛的，并从空态教学知道怎么建第一个版本任务；
- 走查方式：单人独立完成 + 记录卡点；
- 卡点清单：见 QA 报告「小白走查」节（每页卡点/看不懂的词/找不到的入口）；
- 结论：PASS（无 P0/P1 卡点）或 待修复清单（以 QA 证据为准）。
