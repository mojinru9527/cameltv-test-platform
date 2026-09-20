# Batch 269 证据 — B1→B4 引用测试在今日主干上的复跑（2026-09-20）

> 为什么跑：验收报告第 ①–⑥ 条引用的一批测试计数，最后一次核对是 2026-09-19 在 `334748bf`。
> 此后 262–268 又合入了 7 个批次（含后端代码改动），所以这些数字**必须重新核对**，不能沿用。

## 命令

```bash
cd test-platform-v2/backend
python -m pytest \
  tests/test_batch258_node_cli.py \
  tests/test_batch258_execution_job_protocol.py \
  tests/test_url_guard.py \
  tests/test_batch258_requirement_source_guard.py \
  tests/test_batch258_token_whitelist.py \
  tests/test_batch259_spec_guard.py \
  tests/test_batch260_impact_query.py \
  tests/test_batch261_evidence_bundle.py \
  tests/test_batch259_object_storage_containment.py \
  tests/test_outbound_policy.py -q
```

环境：`F:\CamelTv-worktrees\CamelTv-worktrees\codex-batch-269-landing-closeout`（base = `origin/main` = `27c11e80`）

## 输出（尾部）

```
tests\test_batch259_object_storage_containment.py ................s      [ 98%]
tests\test_outbound_policy.py ...                                        [100%]
================= 154 passed, 1 skipped, 3 warnings in 12.50s =================
```

## 与验收报告引用数字的逐项对账

| 引用文件 | 报告写的 | 本次实测 | 结论 |
|---|---:|---:|---|
| `tests/test_batch258_node_cli.py` | 28 | 计入总数 | ✅ |
| `tests/test_batch258_execution_job_protocol.py` | 18 | 计入总数 | ✅ |
| `tests/test_url_guard.py` | 17 | 计入总数 | ✅ |
| `tests/test_batch258_requirement_source_guard.py` | 10 | 计入总数 | ✅ |
| `tests/test_batch258_token_whitelist.py` | 12 | 计入总数 | ✅ |
| `tests/test_batch259_spec_guard.py` | 20 | 计入总数 | ✅ |
| `tests/test_batch260_impact_query.py` | 13 | 计入总数 | ✅ |
| `tests/test_batch261_evidence_bundle.py` | 17 | 计入总数 | ✅ |
| `tests/test_batch259_object_storage_containment.py` | 16 passed + 1 skipped | 计入总数 | ✅ |
| `tests/test_outbound_policy.py` | 3 | 计入总数 | ✅ |

**算术核对**：28+18+17+10+12+20+13+17+16+3 = **154 passed**，另 1 skipped → 与实测 `154 passed, 1 skipped` **完全一致**。

即：**262–268 七个批次的代码改动没有让 B1–B4 的这批回归测试发生任何增删或漂移**。

## 未在本批复跑的（如实标注）

| 引用 | 状态 |
|---|---|
| 前端 `npx vitest run --maxWorkers=2`（168 文件 / 737 例） | **未复跑**：本 worktree 是新检出，没有 `node_modules`；需要先 `npm ci`。数字沿用 2026-09-19 在主干上的复跑记录，且本批（269）零前端改动 |
| 前端 `npm run test:a11y:ci`（28 passed） | **未复跑**：同上（需 Chromium + 装依赖） |
| `scripts/node/drill_b1_e2e.py` 25/25 | **未复跑**：本批已在真实演练中验证更强的路径（真节点 + 6 个 job），转录见 `evidence/batch-269/drill-attempt5-driver-stdout.txt` |
| 第 ⑥ 条时延（中位 4.0ms） | **未复跑**：临时 harness 未入库；确定性守卫（查询条数不随规模增长）包含在上表的 13 例里并通过 |

> 说明：本批是"文档/证据"批次，前端与本机 harness 的复跑不属于本批可执行范围；**没有**把"未复跑"写成"已通过"。
