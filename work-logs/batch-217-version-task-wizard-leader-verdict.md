# Batch 217 — Leader Verdict：版本验收建任务向导（B7）
> **Leader (🎯)** | Date: 2026-09-03 | Decision: **APPROVED** | Executor: Codex | 完整批次

## 评审摘要
| 维度 | 评分 | 备注 |
|------|------|------|
| 实现质量 | 高 | 后端方案条目 + 审核 action，前端 3 步向导 + 审核面板；C216-1 满足（消费 version_task API，未另造容器） |
| 风险 | 低 | 纯新增表/路由/页面；未破坏既有 API/页面；前端全量 608 + 语义守卫绿 |
| 覆盖 | 完整 | B7 出口标准（拖入需求→可审方案→逐条确认，无引擎术语）已核对 |

## 关键决策（已批准）
1. **新向导独立 `/version-tasks`**：不改旧 `/missions`（旧引擎页仍经专家入口），避免 Beta 期破坏既有用户。
2. **审核动作**：adopt/modify/remove/ask/confirm；条目状态 draft→adopted/modified/asked/removed；置信度 0-100。
3. **方案生成**：本批用「条目写入 API」打通链路；真实 LLM 生成随 B11/DSH 接入。
4. **语义 token**：页面使用 `@/ui` + 语义类，满足 batch54 守卫。

## 抽检通过
- ✅ `app/api/v1/version_task.py` POST /plan/generate + /plan/{id}/review — HTTP 200，route-inventory 620 条
- ✅ `src/pages/version-tasks/index.tsx` — 3 步向导 + 审核面板；typecheck/build 绿；无固定色板
- ✅ 前端全量 129/608 绿；后端 2370 passed / 1 baseline fail（test_batch148_p0_fixes，batch-212 已确认）
- ✅ Alembic 单头 20260906_version_task_plan_item + 双向 drill 通过

## 判决
**APPROVED** —— 允许进入合入流程。创建 Draft PR，待 required checks 全绿 + `audit-ai-pr.ps1 -RequireSuccessfulChecks` 通过后 squash 合并到 main（用户已提前授权 B6-B15 推送+PR+合入）。

## 下一批次 Leader 条件
- C217-1: B8 执行与证据回放必须把执行记录挂到 VersionTask 的 `version_task_execution` 关联表并回写 `coverage`（pass/fail/skip/blocked 计数），保持单一事实源；不得在 VersionTask 之外再造执行容器。解除条件=B8 合入 + version_task_execution 关联与 coverage 回写落地。

## 流程回写（Batch 75 起强制）
| 发现 | 处理 | 落点 |
|------|------|------|
| `@/ui` Button variant 为 primary/secondary/ghost/danger（非 shadcn default/outline/destructive） | 前端按实际命名适配 | src/pages/version-tasks/index.tsx |
| PageShell 需要 title 必填 | 补充 title | src/pages/version-tasks/index.tsx |
| batch54 守卫拦截固定色板 `text-amber-600` | 换语义 token `text-muted-foreground` | src/pages/version-tasks/index.tsx |

## 复盘卡
| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| ~5h / ~5.5h | 0/0/0/0 | 3 | 组件约定 | 用 @/ui 前读 props/variant；熟记 batch54 语义守卫 |

**技能使用**: `cameltv-agent-team`、`cameltv-ui-conventions`、`cameltv-bug-guard`、`audit-ai-pr`
