# Batch 278 — AIQE TA-001 代码基线审计：Leader Verdict

> **部门**：🎯 Leader
> **日期**：2026-11-09
> **输入**：PRD + PM + Design + Dev + QA + `docs/aiqe/baseline.md`
> **审计基线**：`origin/main @ 0af75a821`

---

## 1. 判决

# 🟡 APPROVED（附条件）

**理由**：

- TA-001 的 6 个审计产出（14 号 §4.1）全部交付：25 表对账 / 8 接入点 / 30 端点 / 前端 / Driver / 执行链；
- 所有数字来自代码实测（AST / OpenAPI / 目录），不是引用规格旧值；QA 独立重跑 10 项事实复核全通过；
- 关键冲突 **C-01..C-10** 全部显式登记，且有"事实 → 影响 → 建议"三段，不藏在正文；
- 正确守住了边界：**没有替用户做类型/迁移/目录决策**（D-278-1..3 单列），**没有改代码/迁移/CI**；
- 顺带修正了 4 个会误导排期的口径错误（表数、目标表数、服务文件数、路由数）。

**附条件（合入门禁）**：

1. 用户阅读 `docs/aiqe/baseline.md` §0 + §3 + §13，并对 **D-278-1..3** 给出选择；
2. 用户确认后，把三条决策写入 13 号 §4 / §18.2 的下一版补丁（batch-279 开工前）；
3. 本批 PR 可先合入（docs-only），但 **M1 的 `test_runs` 迁移脚本在 D-278-1 确认前不得合并**。

---

## 2. 本批修正的排期口径（必须回写 13/14 号）

| 原文 | 实测 | 影响 |
|------|------|------|
| 13 号 §0 / 14 号 §4.1："43 张真实表" | **43 文件 / 73 表** | batch-278 的覆盖目标应为 73 表；CI 守卫按 73 校验 |
| 13 号 §0："22 张目标表" | **25 张（22 净新建 + 3 扩展）** | 迁移清单与工时按 25 计 |
| 13 号 §18.5："60+ 服务文件" | **71 顶层 / 123 递归** | 服务层审计范围扩大 |
| 13 号 §15.2 隐含："20+ endpoint" | 现有 **265 paths / 323 ops**；规格 30 端点里 **29 净新增** | M3-M5 的 API 工作量需重估 |

---

## 3. 对 M1 的硬约束（batch-279..282）

1. **M1 只建 8 张表 + 1 个 ALTER**：`test_runs / node_runs / step_attempts / assertion_results / run_events / event_outbox / run_artifacts / execution_profiles` + `environments` 扩 4 字段；
2. 迁移顺序按 baseline §11（environment → execution_profiles → test_runs → node_runs → step_attempts/assertion_results → run_events/outbox → run_artifacts → 回填）；
3. **禁止**把 `execution_jobs` 改造成节点事实表；`node_runs.execution_job_id` 是 1:1 外键（BIGINT）；
4. **禁止**在 M1 建 M3+ 的表（contract/AC/scenario/workflow/triage/learning）；
5. `run_events` 的 seq 分配按 13 号 §8.3.1（SQLite 计数器 / PG advisory），TA-006 必过双端 1000 事件验收；
6. 节点侧直接复用 `execution_job_service` + `cameltv_node`，不新写节点协议。

---

## 4. 三条待用户决策（阻塞点）

| ID | 决策 | 不确认的影响 |
|----|------|-------------|
| **D-278-1** | ID 类型：新建 UUID + 现有表 FK BIGINT | 无法写 `test_runs`/`node_runs` 的 Alembic；会退化成 UUID↔INT 双列 |
| **D-278-2** | `version_task_run`：候选 B（保留 + `test_run_id` 回填，M2 只读，V1.1 删） | 若选 A（直接 ALTER 并入），M1 要同时动版本任务前端 + 3 个服务 |
| **D-278-3** | 前端目录：`pages/<domain>/`，不建 `features/` | TA-008 会在两套目录之间反复搬组件 |

---

## 5. 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| 规格里的"表数/文件数"是上一轮文档合并时估算的，未实测 | 规格中所有计数类断言必须标"实测 @ commit" | 13 号 §使用说明 增补一条（batch-279 执行） |
| 懒加载 `include_router` 导致静态 grep 路由不准 | 路由盘点统一用 `app.openapi()` | 已写入 baseline §1 + Dev plan §1 |
| 语义等价字段（改名）无法靠机器 diff 判断 | 关键表人工补"语义映射" | baseline §5 的 5 处 |

---

## 6. 知识审计

### 6.1 可入 KB

| 知识 | 类型 | 备注 |
|------|------|------|
| "规格计数断言必须实测 @ commit" | 流程规范 | 由本批 4 处口径错误反推 |
| "新实体 UUID + 旧表 FK BIGINT" | 架构模式 | 存量 INT 系统的渐进式 ID 治理 |
| "Run 是新事实层，不是旧执行链改名" | 架构决策 | 对应 C-04 |
| "节点协议已有，别重写" | 工程判断 | 对应 §9 |

### 6.2 矛盾检查

- ✅ 不与 11 号方案 §2 删除清单矛盾（本批不删任何表）；
- ✅ 不与 batch-276 的 D-5/D-7 结论矛盾（证据边界 / 资源锁）；
- ✅ 不与 §2 不做清单矛盾（未恢复 AITDE/DSH/报告中心）；
- ⚠️ 与 13 号 §4"所有 ID UUID v4"**部分矛盾**，已作为 C-01 + D-278-1 显式登记，不静默修改规格。

---

## 7. 本批新增条件（待用户确认后转正式 C 条件）

- **C-278-1**（若 D-278-1 确认）：13 号 §4 的 ID 规则改为"新建 UUID / 旧表 FK BIGINT"，并由 TA-004.2 的 JSON schema 守卫之外再加一条 **模型 ID 类型守卫**（新表禁 INT 主键）；
- **C-278-2**（若 D-278-2 确认）：`version_task_run` 在 M2 结束前必须完成 `test_run_id` 回填，回填率 < 100% 不得切只读。

> 本批**暂不写** `C-CONDITIONS.md`，等用户对 D-278-1..3 表态后由 batch-279 统一登记。

---

## 8. 复盘卡

| 字段 | 内容 |
|------|------|
| 计划耗时 | 5 人日 / 实际 ≈ 1.5h |
| 缺陷 | 新增 P0 × 0；本批修正 4 处排期口径 + 5 处审计自身问题 |
| 返工次数 | 2（多列字段拆名、附录标题层级） |
| 根因分类 | 需求侧（规格数字估算）+ 工具侧（懒加载路由） |
| 下次避免 | 计数类结论先实测；路由先 `openapi()` 再写文档 |

---

## 9. 合入路径

```text
feature/batch-278-aiqe-ta-001-baseline-audit
  → Draft PR → required checks（docs-only，三路返回结果）
  → audit-ai-pr -ExpectedWorkflow agent-team -ExpectedExecutor DeepSeek_Harness -RequireSuccessfulChecks
  → squash merge → main
  → 用户在 PR / baseline §13 上对 D-278-1..3 表态
  → batch-279 开工前把决策写入 13 号
```

---

## 10. 关联工件

- 审计正文：[docs/aiqe/baseline.md](../docs/aiqe/baseline.md)
- PRD：[batch-278-aiqe-ta-001-baseline-audit-prd.md](batch-278-aiqe-ta-001-baseline-audit-prd.md)
- PM：[batch-278-aiqe-ta-001-baseline-audit-pm-plan.md](batch-278-aiqe-ta-001-baseline-audit-pm-plan.md)
- Design：[batch-278-aiqe-ta-001-baseline-audit-design-spec.md](batch-278-aiqe-ta-001-baseline-audit-design-spec.md)
- Dev：[batch-278-aiqe-ta-001-baseline-audit-dev-plan.md](batch-278-aiqe-ta-001-baseline-audit-dev-plan.md)
- QA：[batch-278-aiqe-ta-001-baseline-audit-qa-report.md](batch-278-aiqe-ta-001-baseline-audit-qa-report.md)
- 看板：[kanbans/DEV-batch-278-aiqe-ta-001-baseline-audit.md](kanbans/DEV-batch-278-aiqe-ta-001-baseline-audit.md)
- 上游：[batch-274 Leader verdict](batch-274-aiqe-spec-review-leader-verdict.md) §5；[14 号排期](../docs/platform-refactor/14-aiqe-dev-schedule-and-dogfood-plan.md) §4.1
