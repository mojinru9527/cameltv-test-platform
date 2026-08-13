# DEV 看板 — Batch 168

> Workflow: agent-team | Executor: codex | Branch: fix/batch-168-coverage-pipeline-fixes | Base: main

## 批次目标
修复 C167-2 真实复测 D1–D8，使 16.0.0 三类型覆盖 ≥60%。

## Slices
- [x] S1 上游工件（PRD/PM/Design）
- [x] S2 后端 D1/D2 覆盖矩阵（commit d1b8ea6）
- [x] S3 后端 D3/D4/D8 接口生成与 UI 回填（commit 5150530）
- [x] S4 后端 D6/D7 分环境与失败透出（commit d1b8ea6）
- [x] S5 前端 D5/D7（commit 2f690ca）
- [x] S6 硬门禁全绿（1427 pass / 458 pass）
- [x] S7 真实数据复测 14/18=77.8% 门禁通过
- [ ] S8 用户总确认 → push → PR → merge

## 批次记录
| 项 | 值 |
|----|----|
| 产出 | PRD/PM/Design/QA/Leader + 代码 + 证据 |
| 审批 | Leader APPROVED（待总确认） |
| 耗时 | 计划 6h / 实际约 5h |
