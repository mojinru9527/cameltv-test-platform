# Batch 217 — 版本验收建任务向导（B7）
> **Product (🟦)** | Date: 2026-09-05 | Status: Draft | Executor: Codex | 完整批次

## 0. 关联
- 路线图: `docs/superpowers/plans/2026-09-02-platform-refactor-rollout.md` §2 B7(batch-217) 完整·前后端
- 主链路: `docs/platform-refactor/01-platform-positioning-and-mainline.md` §4「建任务 → 审方案」
- 前置: B6(batch-216) 建成 VersionTask 统一事实源 + 状态机（C216-1：向导必须消费 version_task API，不另造容器）
- B7 出口标准: `拖入需求→可审方案→逐条确认，无引擎术语`

## 1. 问题陈述
B6 打通了后端 VersionTask 事实源，但测试员仍缺一个业务语言入口：既要能「一键把需求变成可审方案」，又要能「逐条采纳/修改/删除/追问」后再让 AI 执行。现网 `/missions` 是引擎术语（Mission/Scenario/Contract），不符合「无引擎术语」定位。

## 2. 成功指标
| 指标 | 基线 | 目标 | 测量窗口 |
|------|------|------|---------|
| 向导 3 步（填需求→审方案→确认） | 无 | 有，且消费 version_task API | 本批 |
| AI 方案条目（功能/接口/场景）可生成 | 无 | 有（写 version_task_plan_item） | 本批 |
| 审核面板（采纳/改/删/追问 + 置信度 + 待确认） | 无 | 有 | 本批 |
| 无引擎术语暴露 | 有 | 页面只出现「版本/模块/方案/结论」 | 本批 |
| 前后端 gate | — | typecheck/lint/build/vitest + 后端 F821/路由/pytest 无新增失败 | 本批 |

## 3. 非目标（本次不做）
- **不做执行与证据回放**（B8）、**放行页**（B9）——后续批次。
- **不改旧 /missions 页面**：新向导独立 `/version-tasks`，旧引擎页仍可经专家入口访问。
- **不做真实 LLM 方案生成**：本批用「方案条目写入 API」（AI 生成逻辑随 B11/DSH 接入），先打通数据+审核链路。
- **不引入新依赖**：复用现有 shadcn/ui + axios + sonner。

## 4. 用户故事 + 验收标准
- As a 测试员, I want 三步把「版本+需求」变成可审的验收方案, so that 不用看懂引擎术语就能开始验收。
  - 验收：Given 打开 /version-tasks / When 填标题/版本/模块→创建任务 / Then 状态 draft，可进入审方案。
- As a 测试员, I want 逐条采纳/修改/删除/追问方案条目, so that 方案在放行前被人审过。
  - 验收：Given 生成方案 / When 对某条发起采纳/修改/追问/删除 / Then 条目状态流转为 adopted/modified/asked/removed，前端刷新可见。
- As a 测试员, I want 确认后任务进入待审, so that 状态机继续走 B8 执行。
  - 验收：Given 方案非空 / When 点「确认并进入待审」 / Then task status → plan_review。

## 5. 技术考量
- 前端：`src/pages/version-tasks/index.tsx` + `src/api/versionTask.ts`；路由 `/version-tasks`（主显区）。
- 后端：`version_task_plan_item` 表 + `POST /version-tasks/{id}/plan/generate` + `GET /plan` + `POST /plan/{item_id}/review`。
- 审核动作：adopt / modify / remove / ask / confirm；条目状态 draft/pending/adopted/modified/asked/removed。
- 语义 token：新页面不得使用固定色板（batch54 守卫），用 `text-muted-foreground` 等语义类。

## 6. 上线计划
| 阶段 | 受众 | 成功门槛 |
|------|------|---------|
| 本分支合入 | 平台 | 前后端 gate 绿 + CI 全绿 |
| M1 里程碑 | 平台 | B6–B10 合入 → 黑盒跑通版本验收闭环 |

## 7. 技能使用
- `cameltv-agent-team` → 六部门工件
- `cameltv-ui-conventions` → shadcn/ui 语义组件与 token（PageShell/Card/Badge/Progress）
- `cameltv-bug-guard` → 路由/守卫/新增源文件语义色板（batch54）
