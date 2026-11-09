# Batch 278 决策回写 — AIQE baseline 决策入规格：PRD-lite

> **部门**：🟦 Product（lite）
> **日期**：2026-11-09
> **Executor**：DeepSeek Harness（agent-team，worktree `DeepSeek_Harness-batch-278-aiqe-baseline-decisions`）
> **分支**：feature/batch-278-aiqe-baseline-decisions（从 `origin/main 7f205829c` 切出）
> **批次模式**：**light**（docs-only，PRD-lite + QA + Leader + 看板）
> **mode 理由**：不引入新行为/接口/配置/依赖；只把用户已确认的 3 条决策 + 4 处口径修正写回 13/14 号与 baseline。

---

## 1. 问题陈述

batch-278 产出 `docs/aiqe/baseline.md` 并列出 **D-278-1..3**；用户 2026-11-09 回复"按照你的建议来处理"，即确认：

1. **D-278-1**：新建实体 UUID v4，跨接现有表的外键用 BIGINT；
2. **D-278-2**：`version_task_run` 采用候选 B（保留 + `test_run_id` 回填，M2 只读，V1.1 删表）；
3. **D-278-3**：前端沿用 `pages/<domain>/`，不建 `features/`。

但 13 号当前仍是 **v1.2-p1-fixed**，且写着"所有 ID 使用 UUID v4"、`features/` 目录、"迁移策略待审计后定案"——不写回就会在 M1 与开发实际动作冲突。同时 Leader verdict 要求把 4 处口径（43 文件/73 表、25 目标表、71/123 服务、265 paths）同步到 13/14 号。

---

## 2. 成功指标

| 指标 | 阈值 | 结果 |
|------|------|:----:|
| D-278-1 入规格（§4 关键规则 + §4.7/§4.8 字段类型） | 1 | ✅ |
| D-278-2 入规格（§4.7 迁移策略改为候选 B） | 1 | ✅ |
| D-278-3 入规格（§18.2 目录树 + 目录决策） | 1 | ✅ |
| 4 处口径修正（13/14 号） | 4 | ✅ |
| 13 号 version → `v1.3-baseline-aligned` + banner | 1 | ✅ |
| baseline 记录"已确认" | 1 | ✅ |
| 表格 / 锚点 / 链接校验 | 0 问题 | ✅ |
| 不引入新矛盾 | 0 处 | ✅ |

---

## 3. 落地清单

### 3.1 13 号（v1.2 → v1.3-baseline-aligned）

| 位置 | 变更 |
|------|------|
| frontmatter | `version: v1.3-baseline-aligned`；`related` 加 `docs/aiqe/baseline.md` |
| 顶部 banner | 新增 v1.3 变更块（D-278-1..3 + 4 处口径） |
| §4 关键规则 | "所有时间字段 timestamptz" → **naive UTC**（C-02）；"所有 ID UUID v4" → **新建 UUID / 旧表 FK BIGINT**（D-278-1）；新增 JSON 类型（C-03）与规模口径（25 表 / 73 表） |
| §4.7 `test_runs` | 字段类型标注 BIGINT/UUID；迁移策略改为**候选 B 定案**（双写 + 回填 + M2 只读 + V1.1 删表；不采用候选 A） |
| §4.8 `node_runs` | `run_id UUID`、`execution_job_id BIGINT FK` |
| §15.2 | 新增"现状对齐"：265 paths / 323 ops，30 端点中 29 净新增 |
| §18.2 | 目录树改 `pages/`；新增"目录决策（D-278-3）" |
| 使用说明 / 结尾 | 改为"已完成 TA-001 审计，冲突以 baseline 为准；v1.3 active" |

### 3.2 14 号（排期口径）

| 位置 | 变更 |
|------|------|
| 批次表 | batch-278 标 `✅（PR #499）` |
| §4.1 batch-278 | 22→**25 张目标表**；43→**43 文件/73 表**；60+→**71/123**；20+→**30 端点 / 265 paths**；DoD 标完成 + 决策已确认 |
| M0 Gate | `13 号 v1.1` → `v1.3-baseline-aligned` |

### 3.3 baseline

| 位置 | 变更 |
|------|------|
| frontmatter | `version: v1.1-decisions-confirmed` |
| §13 | 三条决策从"建议/不确认后果"改为"**决定（已确认）/落地位置**"，并注明 C-278-1/2 随 batch-279 登记 |

---

## 4. 非目标

- 不写 C-CONDITIONS.md（按 Leader verdict：batch-279 统一登记）；
- 不改 13 号其它 P2；
- 不动代码 / 迁移 / CI；
- 不启动 M1 建表（batch-279）。

---

## 5. DoD

- [x] 3 条决策 + 4 处口径入 13/14 号；
- [x] 13 号 v1.3-baseline-aligned active；
- [x] baseline 记录决策已确认；
- [x] 表格 / 锚点 / 链接 0 问题；
- [ ] PR checks 全绿后合入 main。
