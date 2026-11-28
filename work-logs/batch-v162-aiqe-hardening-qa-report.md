# Batch AIQE-V162 — QA 报告（V1.6.2 Hardening 整改）

> 分支：`feature/aiqe-v162-hardening` | 基线：`2d2f508d5d1fd452972e7af49d9b4f3bde2e7b01`
> 测试日期：2026-11-28 | 环境：Windows / Python 3.12.10 / SQLite

## 1. 结论

**发布判定：`RELEASE_CANDIDATE_BLOCKED`（GA 未签署）。**

代码级整改与测试已完成；外部条件（隔离 Test 环境/Secret、生产灰度/回滚演练、
真实 GitHub Reviewer、Ruleset 线上更新）未满足，按手册 fail-closed 不得签 GA。
不存在通过降低断言、删除失败用例或伪造证据获得的绿色。

## 2. 执行命令与结果

| 检查 | 命令 | 结果 |
|---|---|---|
| AIQE 全量测试 | `pytest tests -q -k aiqe` | **1516 passed / 0 failed**（281s） |
| 后端全量回归 | `pytest -q` | 见 §3（基线 2854 passed / 43 skipped；修复 1 个顺序依赖后复跑） |
| 追踪矩阵 | `python scripts/aiqe/check_traceability.py --strict-warnings --check-baseline` | 74 条，0 error / 0 warning |
| 发布审计 | `python scripts/aiqe/check_release_audit.py` | 0 error |
| 审计关闭 | `python scripts/aiqe/check_audit_closure.py --check` | 0 CLOSED / 19 EXTERNAL / 0 error |
| 产品配置 | `python scripts/aiqe/run_product_tc.py --check-config` | `CONFIG_VALID`（10 条，baseline v1.6.2-hardening） |
| 产品结果 | `python scripts/aiqe/verify_product_tc_results.py --require-pass` | **非零**（10/10 BLOCKED，预期） |
| GA 判定 | `python scripts/aiqe/release_verdict.py --require-ga` | **退出 1**，Gate E/F/G NOT_PROVEN（预期） |
| 凭据扫描 | `python scripts/aiqe/scan_credentials.py` | `CLEAN`，potential=0 / weak=0 / known-test=51，scan SHA=当前 HEAD |
| Branch Ruleset | `python scripts/aiqe/check_branch_protection.py --check` | **退出 1**（线上仍缺 AIQE Aggregate check，合并后更新） |
| 静态 fail-open | `python scripts/ci/check_aiqe_v16_static_gates.py` | 0 error |
| Ruff F821 | `ruff check app/ --select F821` | 通过 |
| Quality Ratchet | `python scripts/ci/quality_ratchet.py` | PASS（ruff/mypy increased=0） |
| Alembic | `python -m alembic heads` | 单头 `20261122_v16_catalog_post_merge` |

## 3. 全量回归与基线对比

- 第一次全量：`1 failed, 2854 passed, 43 skipped`。唯一失败为
  `test_aiqe_aud003_secret_protection.py::test_canary_token_never_persisted`，
  单文件运行 44/44 通过，判定为**测试顺序依赖**：原测试用
  `where(ExecutionJob.status == "pending")` 取全局第一个 pending Job，可能拿到其他用例的 Job。
- 修复：把查询限定为 `ExecutionJob.run_id == run.id`（不降低断言），随后复跑全量。
- 无删除用例、无跳过新增、无断言弱化。

## 4. 正向证据

| FIX | 证据 |
|---|---|
| FIX-001 | RV-001～012 + repo 级 `--require-ga` 负例；Gate E 不再接受静态满分 |
| FIX-002 | 配置 schema 2.0；`--check-config/--plan/--run/--verify-results`；伪造 PASS/hash/SHA/环境被拒绝 |
| FIX-003 | ADR 0032 十条映射 + 4 条 BLOCKED Requirement（V16-017-R3～R6） |
| FIX-005 | AgentTask API→approve→run→claim→run_job→终态；A5 read_git_diff 审计含真实 SHA |
| FIX-006 | 逐样本指标复算、篡改拒绝、Dataset 绑定、双人审批/发布拒绝 |
| FIX-007 | `SEMI_AUTOMATIC`→PARTIAL；mandatory 平台最弱聚合 |
| FIX-008 | WWY-V5-001 保持 FAIL/OPEN；正式 Regression runner 缺 SHA/scope/comparison 即 NOT_PROVEN |
| FIX-009 | 明文移除、CI PG Secret、scanner `.fill()`/markdown/Bearer/DSN 覆盖、当前 SHA CLEAN |
| FIX-010 | 阶段跳过 → NOT_RUN/NOT_PROVEN；Gate F 语义校验 |
| FIX-011 | Builder 以 artifact tested SHA 为事实源；冲突/本地环境/duration=0 fail-closed |
| FIX-012 | closure_rule_id + 语义验证器；0 CLOSED/19 EXTERNAL |
| FIX-013 | 4 个精确 required contexts + `AIQE V1.6 Governance Gate` Aggregate Job |
| FIX-014 | GitHub login/user id/PR/review id/APPROVED/SHA 校验与在线回查 |
| FIX-015 | Evidence Manifest + Final Acceptance 生成器；决策 RELEASE_CANDIDATE_BLOCKED |

## 5. 负向测试

- runtime `ga_ready=false` + 产品 10/10 → Gate E 非 PASS，CLI 退出 1（RV-001）。
- runner null/缺 run/断言/artifact/hash/SHA/环境/digest → 非 PASS（RV-002～010）。
- 伪造 `ga_ready=true` 但内部 BLOCKED → 拒绝（RV-011）。
- 产品 BLOCKED 改 PASS、artifact hash 篡改、旧 SHA、local 环境 → verify 拒绝。
- `SEMI_AUTOMATIC`/WAIVED 计 PASS → 拒绝。
- 同 user id 双人审批、stale review、缺 review id、非 APPROVED → 拒绝。
- 生产阶段跳过后写 PASS、只有回滚命令、WAIVED 缺批准人/到期 → Gate F 非 PASS。
- 审计 CLOSED 仅路径存在 → 语义验证失败。

## 6. 未覆盖 / 阻塞（不是测试通过项）

1. 产品 TC 001–010 无隔离 Test Runner/Secret → 10/10 BLOCKED。
2. 生产 stage3/4 与 rollback drill 未执行；stage1/2 只有 health/openapi。
3. 70 条 acceptance 记录缺真实 GitHub Reviewer 身份；GA 模式全 PENDING。
4. 生产测试账号/Kibana 早期密码轮换需账号 owner 执行。
5. Main Ruleset 需合并后 apply `AIQE V1.6 Governance Gate` 并 capture。
6. A2/A3/A6 写工具仍 UNAVAILABLE；产品级 Benchmark/审批/发布未执行。

## 7. 环境与可复现性

- 所有测试为本地确定性/受控 LLM 测试；不含真实生产调用（外部未来娃屿脚本已改为缺 Secret 即 BLOCKED）。
- 证据文件 SHA 在提交后由 `scan_credentials.py` / `release_verdict.py` 重新生成绑定新 SHA。
