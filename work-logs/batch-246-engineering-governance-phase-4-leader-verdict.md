# Batch 246 — Leader Verdict

> **Leader (🎯)** | Date: 2026-09-15 | Decision: APPROVED（本地门禁通过；最终条件为用户总确认 + PR required checks）

## 评审摘要

| 维度 | 评分 | 备注 |
|------|:----:|------|
| 实现质量 | A | Ruff/mypy exact-count ratchet、provider audits、Dashboard group-by 均可复现 |
| 风险控制 | A- | 生产依赖 0；dev-only LHCI advisories 被 ratchet 和 C246-1 明确追踪 |
| 回归覆盖 | A | 双端全量、axe 28、Lighthouse、query budget、CI contract 全部通过 |
| 可维护性 | A- | 固定工具版本、无 `|| echo`、required context 未漂移 |

## 关键决策（已批准）

1. **Ruff/mypy 采用只减不增 ratchet**：不伪造历史债清零，但任何新增 finding 都阻断。
2. **required checks 复用既有 context**：治理步骤直接进入既有 backend/frontend job，避免新增未同步 branch protection 的 MISSING context。
3. **axe required suite 与真实后端 theme suite 分层**：`test:a11y:ci` 使用 fixture/guest 页面稳定运行；`test:a11y:full` 保留真实后端扩展验收。
4. **生产依赖 0 + 完整 npm audit ratchet**：生产依赖任一 high/critical 阻断；LHCI dev-chain 现有 advisories baseline 化，新增 advisory 阻断。
5. **Dashboard 批量化**：项目级统计固定 5 个 GROUP BY 查询，cross-project 总查询预算不随项目数增长。

## 抽检通过

- ✅ `scripts/ci/quality_ratchet.py` — Ruff 768/768、mypy 193/193、new=0。
- ✅ `scripts/ci/npm_audit_ratchet.mjs` — full audit baseline/current 16/16，new=0；生产审计 0 vulnerability。
- ✅ `.github/workflows/main-quality-gate.yml` — required backend/frontend 含 ratchet、pip/npm audit、axe、Lighthouse，无 `continue-on-error`/`|| echo`。
- ✅ `test-platform-v2/frontend/.lighthouserc.json` — accessibility >= 0.9 失败阻断，自动启动 preview。
- ✅ `test-platform-v2/backend/app/services/statistics_service.py` — 固定 5 个批量项目统计查询。
- ✅ `test-platform-v2/backend/tests/test_batch244_query_budget.py` — 20 项目固定查询数验证。
- ✅ 后端全量 — 2678 passed / 51 skipped / 1 xfailed。
- ✅ 前端全量 — 164 files / 710 tests；coverage 710 tests；Stmts 40.91%。
- ✅ axe — 28 passed；Lighthouse — 通过。
- ✅ CI 契约 — quality/range contracts 各 10 passed。

## 判决

C243-4 与 C244-1 的本地实现和 QA 均已完成。用户一次总确认后推送 `feature/engineering-governance-phase-4`、创建 Draft PR，并等待 required checks；全部通过且 `audit-ai-pr.ps1 -RequireSuccessfulChecks` 成功后，可转 Ready 并 squash 合入 `main`。

## 下一批次 Leader 条件

- `C246-1`：升级或替换 LHCI 开发依赖链，消除当前 7 high / 1 moderate / 2 low dev-only advisories；在此之前 full npm audit ratchet 必须保持 no-new。
- `C243-1`：Runner 单任务容器隔离、只读 rootfs 与更严格 egress policy。
- C243-4 / C244-1：本批实现与 required checks 通过后关闭。

## 流程回写（Batch 75 起强制）

| 发现 | 处理 | 落点 |
|------|------|------|
| required a11y 套件混入真实后端依赖 | 拆分稳定 required 与 full theme suite | `package.json`；QA/US-3 |
| static analysis 按行号比较造成假回归 | 改为 file/code/message + occurrence count | `scripts/ci/quality_ratchet.py` |
| LHCI 引入 dev-only advisories | 生产审计为硬 0，完整审计建立精确 ratchet | `npm_audit_ratchet.mjs`、`npm-audit-baseline.json`、C246-1 |
| 依赖审计与静态分析仍只在 observation workflow | 纳入既有 required backend/frontend context | `main-quality-gate.yml` |

## 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 8h 计划 / 约 7h 实际 | 0/0/1/2 | 2 | required 套件外部依赖；行号型基线脆弱 | required 测试只用可复现 fixture；ratchet key 永不含行号 |
