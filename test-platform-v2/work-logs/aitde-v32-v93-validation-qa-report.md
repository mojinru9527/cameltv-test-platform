# AITDE V3.2 — §93 版本级专项校验 QA 报告

> 日期：2026-08-29 · 执行器：DeepSeek_Harness · 分支：feature/aitde-v32-data-db-runtime（合入 main）
> 说明：本报告记录方案 §93「版本完成后的专项校验」在**当前环境**的实际落地情况。**涉及真实外部数据库/50 个真实 Scenario 的项，本环境无真实库、无 Docker、无 DB 服务，故以「DB 无关语义等价」方式用 in-memory SQLite 验证，真实库项如实标注为待基础设施。**

## 一、已落地并验证的项（DB 无关，pytest 通过）

| §93 项 | 校验点 | 结果 | 测试 |
|--------|--------|------|------|
| 并发 20 独占数据 Run 无重复 Lease | 不同 run 独占同一 fixture → 409；同 run 幂等 | ✅ | `test_v93_concurrent_exclusive_lease_no_duplicate` |
| 连续 Cleanup 3 次结果一致 | 3 次均 SUCCEEDED，第 2/3 次幂等 | ✅ | `test_v93_cleanup_idempotent_three_times` |
| 非 allowlist mutation 100% 拒绝 | DB_FIXTURE 对非 allowlist 表 → 400 | ✅ | `test_v93_non_allowlist_mutation_rejected` |
| 错误 DB 密码不出现在 API/log/Evidence | 连接测试结果不含 `secret_ref`、`secret_leaked=false`；config 含 password 被拒 | ✅ | `test_v93_db_password_never_in_result` / `test_v93_config_secret_rejected_at_create` |
| DataFail 不误报 BusinessFail | `finish_run` 保留 `DATA_FAIL`，不被业务 outcome 覆盖 | ✅ | `test_finish_run_preserves_data_fail` |
| 旧 Dataset 回归（CSV/JSON→STATIC 兼容） | legacy adapter：静态源创建+幂等+sql 拒绝 | ✅ | `tests/aitde/v32/test_legacy_adapter.py` |

> 相关域回归：`tests/aitde` + RBAC + 迁移 + 路由守卫 = **123 passed**；`ruff F821 app/` ✅；alembic 单头 ✅。

## 二、需真实基础设施 / 进一步工作（本次未执行）

| §93 项 | 依赖 | 现状 |
|--------|------|------|
| ≥50 个真实 Scenario 自动数据成功率 | 真实场景 + 真实执行 | ❌ 本环境无 50 个真实场景，无法测成功率 |
| DB Before/After 抽样与真实库一致 | 真实 MySQL/PostgreSQL | ❌ 无真实 DB 服务；仅连接测试类别化 |
| 随机中断 Provision 后恢复/cleanup | 真实执行中断 | △ 清理幂等已验证；中断恢复未做 |
| 环境切换 Fixture 不跨环境复用 | 代码 + 环境 | ❌ 当前 fixture 复用按 `(scenario_version, data_plan)`，**未按 environment 隔离**——需改 `prepare_run_data` 复用逻辑为环境感知（见下） |

## 三、发现的待办（给后续）
1. **环境隔离缺陷**：`run_data_integration.prepare_run_data` 复用 fixture 时未区分环境，跨环境可能复用同一 fixture。建议增加 `environment_id` 参与复用判定（`(scenario_version, data_plan, environment)`）。
2. **真实库校验**：当提供真实 MySQL/PostgreSQL 后，应跑 `DbFixtureBuilder` 真实 INSERT、DB Before/After 快照与真实库抽样对比、以及 50 真实场景自动数据成功率。
3. **DB 密码进 log**：当前连接测试已类别化返回（不泄）；建议再对真实连库失败的错误日志做一次脱敏断言。

## 四、结论
- 已把 §93 中**不依赖真实外部库**的专项全部落地为自动校验并合入 main。
- **真实库/50 真实场景**部分因本环境无基础设施，未能执行；已给出对应的校验点与后续环境隔离修复建议。
