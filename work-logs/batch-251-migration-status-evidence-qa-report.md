# Batch 251 — QA Report（C250-1 迁移状态证据取源修复）

> **🔍 QA** | Date: 2026-09-17 | 立场：默认「需要改进」
> 分支：`fix/batch-251-migration-status-evidence`（base `6e8cf624`）| worktree：`F:\CamelTv-worktrees\CamelTv-worktrees\codex-batch-251-migration-status-evidence`
> 变更范围：`deploy/release-console/**`、`work-logs/**`、`C-CONDITIONS.md`（**未触碰** `test-platform-v2/`）

## 1. 结论

**PASS**。C250-1 已修复，并在生产用一次真实发布验证：
`release-20260917-0007` 的 `PROD_OBSERVING` 事件 reason = 
`publish succeeded; migration target=20260922_ai_agent_token actual=20260922_ai_agent_token`。

| 指标 | 状态 |
|------|------|
| M1 成功发布事件带迁移落点 | ✅ 生产实测（§3） |
| M2 不依赖日志窗口 | ✅ 单测（§2） |
| M3 无状态行不臆造 | ✅ 单测 |
| M4 失败路径语义不变 | ✅ Batch 250 用例继续全绿 |

## 2. 硬门禁证据

| 门禁 | 命令 | 结果 |
|---|---|---|
| 控制面全量测试 | `cd deploy/release-console && python -m pytest tests -q` | **54 passed, 2 subtests passed**（Batch 250 基线 51 → +3） |
| 本批新增测试 | `pytest tests/test_tencent_executor.py tests/test_console_manifest.py -q` | 执行器 2 例 + 事件 1 例；**先红（3 failed）后绿** |
| 控制面 lint（全目录） | `python -m ruff check .` | All checks passed |
| 镜像内冒烟 | `docker run --rm --entrypoint python cameltv-release-console:release-20260917-3 -c "import app, tencent_executor, migrations; …"` | `image smoke ok migration_status=None` |
| 生产发布 | `release-20260917-0007`（split） | `PROD_OBSERVING → PRODUCTION_VERIFIED` |

> 本批无后端/前端代码改动；按 AGENTS.md §4.2 分类为重测试跳过，required contexts 仍须返回结果（合入前以 CI 实际分类记录）。

### TDD 记录（红 → 绿）

```
# 红（实现前）
tests/test_tencent_executor.py::...test_deploy_reads_migration_status_from_full_output FAILED
tests/test_tencent_executor.py::...test_deploy_without_migration_status_stays_none FAILED
tests/test_console_manifest.py::...test_migration_status_from_full_output_lands_in_event_reason FAILED
3 failed, 8 passed

# 绿（实现后）
54 passed, 2 subtests passed
```

回归断言要点：用例显式断言 `result.logs` **不含** `CAMELTV_MIGRATION`（复现截断），
同时断言 `result.migration_status` 仍取到 `migration target=… actual=…`——
即"证据不再依赖日志窗口"。

## 3. M1 — 生产实测（成败判据）

| 项 | 修复前（-0006，Batch 250） | 修复后（-0007，本批） |
|---|---|---|
| `PROD_OBSERVING.reason` | `publish succeeded` | `publish succeeded; migration target=20260922_ai_agent_token actual=20260922_ai_agent_token` |
| 上线确认 | `PRODUCTION_VERIFIED` | `PRODUCTION_VERIFIED` |
| 容器 | 6 healthy | 6 healthy |
| DB revision | `20260922_ai_agent_token` | `20260922_ai_agent_token` |

证据全文：[batch-251-migration-status-evidence-production-evidence-20260917.md](batch-251-migration-status-evidence-production-evidence-20260917.md)

## 4. 缺陷清单

本批为**修复批**，未引入新缺陷：

- **C250-1（P2）→ 已修复**：迁移状态改由执行器从完整远端输出解析（`ExecutorResult.migration_status`），
  事件 reason 优先使用该字段，`logs` 仅作兜底。
- **遗留（保持 Open，非本批）**：C248-8（runner target 本机不可构建）、C249-5、C249-6、C249-7。
- **P3 观察**：失败路径的异常文本仍只带 `output[-2000:]`；因失败点紧邻状态行，实际不受影响（单测覆盖），
  若后续出现"多步失败后状态行漂远"的场景，可考虑把完整输出随异常传递（未登记为条件）。

## 5. 复盘卡

| 计划耗时 | 缺陷(P0/P1/P2/P3) | 返工次数 | 根因分类 | 下次避免 |
|----------|-------------------|----------|----------|----------|
| 计划 1.5h / 实际约 1.5h | 0/0/1/1 | 0 | 流程（上游批次遗留） | 任何时候把诊断写进事件/返回体，都先问"这段输出会不会被截断"——取值源必须是完整数据，而不是展示用的窗口 |
