# Leader Verdict — Legacy delete final (PR-09)

status: IN REVIEW
date: 2026-09-16

## Review

The batch follows the approved PR-09 boundary: it removes executable Legacy
paths, keeps historical data readable, and never introduces a second execution
model. The explicit user waiver and three signoffs are recorded in the PRD.

## Verdict

Local engineering evidence is sufficient for Draft PR creation. Final
`APPROVED` requires:

1. User-visible PR checks passing.
2. `audit-ai-pr.ps1 -RequireSuccessfulChecks` passing.
3. Post-merge production health/login and read-only Legacy verification.

## 流程回写

| 发现 | 处理 | 落点 |
|---|---|---|
| 删除 route 内联 ORM 查询会触发既有 route-layer guard | 把历史读取收敛到只读 service | `backend/app/services/plan_execution_history.py` |
| 迁移脚本依赖隐式 bridge run 会违反 PR-09 | 迁移命令显式创建 canonical `LEGACY_BRIDGE` run | `backend/scripts/backfill_legacy_execution_links.py` |
