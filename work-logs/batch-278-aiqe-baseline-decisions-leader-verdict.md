# Batch 278 决策回写 — AIQE baseline 决策入规格：Leader Verdict

> **部门**：🎯 Leader
> **日期**：2026-11-09
> **输入**：PRD-lite + QA + 13 号 v1.3 / 14 号 / baseline v1.1
> **上游**：[batch-278 Leader verdict](batch-278-aiqe-ta-001-baseline-audit-leader-verdict.md) §4（三条决策）

---

## 1. 判决

# ✅ APPROVED

**理由**：

- 用户 2026-11-09 已确认 **D-278-1..3**（"按照你的建议来处理"），本批把三条决策 **1:1** 写入 13 号（不是只改一句总结）；
- §4 的类型规则从"所有 ID UUID"收窄为"新建 UUID / 旧表 FK BIGINT"，并在 §4.7 字段表逐行标注，**可被 TA-005 直接执行**；
- §4.7 的 `version_task_run` 迁移从"待定"改为 **候选 B 定案**，含双写、回填、只读、删表四个阶段；
- §18.2 目录树改为 `pages/`，并写明"不新建 `features/`"，与现有 153 个页面组件一致；
- 4 处口径修正（73 表 / 25 目标表 / 71-123 服务 / 265 paths）同时写入 13/14 号，排期不再引用旧数字；
- QA 门禁全绿：旧 ID 规则 0 残留、`BIGINT FK` 4 处、表格 92 张 0 问题、链接 40 条 0 断链。

---

## 2. 对 M0 / M1 的影响

```text
M0 Gate（14 号 §4.1）
  ✅ 13 号 v1.3-baseline-aligned active
  ✅ docs/aiqe/baseline.md 产出（PR #499）
  ✅ TA-001 代码审计 + 决策回写（本批）
  ⬜ §0 P0-1..5 真实证据（batch-277）
  ⬜ TA-001.5 CI 守卫（batch-277 产出）

→ M0 仍有 2 项，batch-279（M1 建表）不得启动，直到 batch-277 完成。
```

---

## 3. 对下一批次的约束

| 批次 | 约束 |
|------|------|
| **batch-277** | §0 P0-1..5 清零；同时把 **C-278-1 / C-278-2** 登记进 `C-CONDITIONS.md`；TA-001.5 的守卫脚本要加一条"新表主键不得为 INT"（C-278-1 的机械检查） |
| **batch-279** | 只建 baseline §11 的 8 张表 + `environments` 扩字段；`test_runs` 的 `project_id/environment_id/trigger_user_id` 用 BIGINT；`node_runs.execution_job_id` BIGINT；版本任务双写与 `test_run_id` 回填在本批或紧随批次实现 |

---

## 4. 例外与风险

| 风险 | 说明 | 缓解 |
|------|------|------|
| 旧表 `id INT` 与新表 `UUID` 混用，容易在 join 处写错类型 | 新表字段已逐行标注 BIGINT/UUID | C-278-1 守卫 + TA-005 单测覆盖"类型不匹配即报错" |
| `source_id` 字段同时承载 UUID 与旧 INT | §4.7 已注明"`version_task` 来源存字符串或加 `legacy_task_id BIGINT`" | 编码时优先加 `legacy_task_id`，`source_id` 只放 UUID |
| 14 号仍保留历史批次（275/276/277）的旧描述 | 只改了 batch-278 与 M0 Gate | 不影响排期执行，历史记录保留原样 |

---

## 5. 流程回写

| 发现 | 处理 | 落点 |
|------|------|------|
| 决策"确认"不等于"回写"，两次 PR 之间容易漂移 | 决策类 verdict 之后固定跟一个回写批次（本批即模板） | 本 verdict + QA 复盘卡 |
| 字段类型只写 `FK` 无法执行 | 规格字段表必须写 UUID/BIGINT 与目标表 | 13 号 §4.7/§4.8 已示范 |

---

## 6. 本批无新增 C 条件

C-278-1/2 按约定由 **batch-277** 统一登记，本批只记录在 verdict 与 PRD-lite。

---

## 7. 复盘卡

| 字段 | 内容 |
|------|------|
| 计划耗时 | 0.5 人日 / 实际 ≈ 25min |
| 缺陷 | 0 新增；自修 4 处（字段类型、时间规则、使用说明、结尾状态） |
| 返工次数 | 0 |
| 根因分类 | 流程（决策批次与规格批次分离） |
| 下次避免 | 决策回写批次必须带"1:1 落点表"（PRD-lite §3 即模板） |

---

## 8. 关联工件

- PRD-lite：[batch-278-aiqe-baseline-decisions-prd-lite.md](batch-278-aiqe-baseline-decisions-prd-lite.md)
- QA：[batch-278-aiqe-baseline-decisions-qa-report.md](batch-278-aiqe-baseline-decisions-qa-report.md)
- 看板：[kanbans/DEV-batch-278-aiqe-baseline-decisions.md](kanbans/DEV-batch-278-aiqe-baseline-decisions.md)
- 修改对象：[13 号 v1.3](../docs/platform-refactor/13-ai-quality-agent-merged-spec.md)、[14 号](../docs/platform-refactor/14-aiqe-dev-schedule-and-dogfood-plan.md)、[baseline v1.1](../docs/aiqe/baseline.md)
- 上游：[batch-278 Leader verdict](batch-278-aiqe-ta-001-baseline-audit-leader-verdict.md) §4
