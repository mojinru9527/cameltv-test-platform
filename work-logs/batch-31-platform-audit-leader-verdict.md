# Batch 31 — Leader Verdict

> **Leader (🎯)** | Date: 2026-07-22 | Decision: **有条件通过 — 允许 Draft PR，禁止自动合并**

## 评审摘要

| 维度 | 判定 | 备注 |
|---|---|---|
| 基线隔离 | PASS | 从最新 origin/develop 建独立 worktree，主工作区未动 |
| 实现质量 | PASS | 修复构建、路由、契约、软删除、质量门禁和响应式 |
| 自动化证据 | PASS | 后端 653、前端 96、typecheck/build 全绿 |
| 流程整改 | PASS | 显式暂存、可执行 QA、CI 和 Leader 证据要求 |
| 生产需求验收 | FAIL/BLOCKED | 赛事回放未在用户生产首页出现；后台生产地址缺失 |
| 远端保护 | NEEDS WORK | develop required checks/审批数仍为 0 |

## 关键决策

1. 本地全量回归全绿，批准 push 功能分支并创建 Draft PR。
2. PR 保持 Draft，直到 GitHub checks 可见且通过；不由 Agent 自动合并。
3. 体育项目“赛事回放”按蓝湖最新版本判定未上线，不与测试平台代码修复混写为通过。
4. 依赖漏洞和 Ruff 全规则债务拆分后续批次，避免本次审查夹带高风险大版本升级。

## 合并前条件

- C31-1：Draft PR 的 develop CI 全部通过。
- C31-2：至少一名人工审查者确认变更范围与生产验收结论。
- C31-3：如要验收运营后台，补充后台生产地址和只读测试账号。
