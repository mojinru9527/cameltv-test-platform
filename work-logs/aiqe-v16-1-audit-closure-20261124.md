# AIQE V1.6.1 审计整改（2026-11-24）

- 输入：`C:\Users\26029\Downloads\CamelTv_AIQE_V1.6_Main_9bbbdbb_Code_Audit.md`
- 基线：`main@9bbbdbb2026bada5c016d663780e03d62fca940d`（与审计 ZIP SHA 一致；
  2026-11-24 环境无法访问 GitHub，`origin/main` 本地即为该提交）
- worktree / 分支：`F:\CamelTv-worktrees\DeepSeek_Harness-aiqe-v161-audit-closure`
  / `fix/aiqe-v161-audit-closure`（direct 任务，executor=DeepSeek_Harness）
- 本地提交：`045b0002`、`7bd3e158`、`0e7cdccb`、`063d30ef`、`b075ddf9`
  （**未 push**：GitHub 443 不可达；按 AGENTS.md §2.4 需用户逐次授权）

## 1. 审计结论与整改映射

| 审计项 | 原结论 | 本次处理 | 证据 |
|---|---|---|---|
| P0-1 追踪矩阵 70 VERIFIED / 60 pending reviewer / V16-025 自审 | 状态不可信 | 矩阵升 v2.0：status 与 acceptance 分离；全量 NOT_REVIEWED；V16-025-R1 reviewer 改 pending；12 条仅现场记录条目降 PARTIAL | `docs/aiqe/v1.6/traceability/requirements.yaml`、`check_traceability.py --strict-warnings` |
| P0-2 Branch Protection 无证据 | Gate G 未证明 | 新增采集/校验脚本与证据文件（当前 `verified=false`）；`--require-ga` 会阻断 | `scripts/aiqe/check_branch_protection.py`、`governance/branch-protection.json` |
| P0-3 PR 字段只查关键词 | 校验不严 | PR 模式改为字段级校验：占位符/过短/作者自审/证据类型全部拒绝 | `check_traceability.py::_validate_pr_fields` + 35 条单测 |
| P0-4 SHA/migration head 过期 | 基线不唯一 | 基线统一 `release_commit=9bbbdbb…`、`migration_head=20261122_v16_catalog_post_merge`；`--check-baseline` 校验 git + Alembic 单头 | `check_traceability.py --check-baseline` |
| P1-1 Evidence Index 是 YAML 派生 | 假运行证据 | CI 改为平台 E2E 产物 → `build_evidence_index.py`；矩阵快照显式 `not_runtime_evidence=true` | `docs/aiqe/v1.6/e2e/platform-results.json`、`evidence/evidence-index.json`、workflow |
| P1-2 strict warnings 未进 CI | 102 warning 放行 | 证据类型化（9 类）后 strict = 0 error/0 warning；CI 启用 `--strict-warnings` | traceability 输出 |
| P1-3 10 个 TC 未真实验收 | 10/10 不可信 | 产品 TC 与平台 `TC-PLATFORM-*` 双命名空间；产品 TC 0/10 归档证据 → PARTIAL；平台链路 10 项产出 Run/Job/Assertion/Artifact ID | `E2E-Coverage-and-Blockers.md`（生成） |
| P1-4 Agent 不消费 tools / 关键工具 UNAVAILABLE / A5 未接线 | Agent 闭环缺失 | 新增 ToolExecutor + AgentContext.tool_executor；A1–A5 真实取证；补齐 read_requirements / read_git_diff；写工具保持 UNAVAILABLE | `agents/tool_executor.py`、`tool_impls.py`、`tests/test_aiqe_v16_019_agent_tool_loop.py` |
| P1-5 `_drain()` 人工 fallback / TC-008 断言过宽 / TC-010 自定义 executor | E2E 保真度不足 | 删除 fallback（保留 pending 断言）；TC-008 必须 PASS；TC-010 走真实 Adapter（stub LLM 仅模型边界）；TC-003 改走 node_executor | `test_v16_017_platform_chain.py` |
| P1-6 生产镜像依赖运行时补丁 | 不可干净重建 | `sqlglot==30.33.0` 进入 api/runner lock（含 hash）；新增镜像依赖回归测试 | `requirements.api.txt`、两个 lock、`tests/test_aiqe_v16_024_image_dependencies.py` |
| P1-7 生产文档互相矛盾 | 生产状态不可信 | `production-evidence.json` 成为唯一定性来源（11 阶段 NOT_PROVEN + 原因）；GA/Production/E2E 文档重写，旧执行记录标 STATUS: HISTORICAL | `governance/production-evidence.json`、`V1.6-GA-Release-Report.md` |
| P1-8 `check_release_audit` 语义盲区 | 0 error 却矛盾 | 新增跨文档断言校验：Gate `[x]`、TC 状态、10/10、GA 状态、PRODUCTION_DEPLOYED、生成文档新鲜度 | `check_release_audit.py` + 单测 |

## 2. 当前机器判定

`python scripts/aiqe/release_verdict.py --write` →

- `ga_status=GA_NOT_READY`；Gate A PASS；Gate B–G NOT_PROVEN
- requirements 70：VERIFIED 58 / PARTIAL 12 / 独立验收 0 / runtime NOT_PROVEN 16
- 产品级 TC PASS 0/10；平台链路 5 PASS / 2 BLOCKED / 3 NOT_RUN

## 3. 已验证门禁

| 门禁 | 命令 | 结果 |
|---|---|---|
| 追踪矩阵 | `check_traceability.py --strict-warnings --check-baseline` | 0 error / 0 warning |
| 发布审计 | `check_release_audit.py` | 0 error |
| 质量棘轮 | `scripts/ci/quality_ratchet.py` | PASS（ruff 395 / mypy 89，increased=0） |
| Ruff F821 | `ruff check app/ --select F821` | PASS |
| AIQE V16 回归 | `pytest -k "aiqe_v16 or aiqe_release_audit or agent_protocol or tool_registry"` | 326 passed |
| 平台链路 E2E | `pytest tests/e2e/aiqe/test_v16_017_*.py` | 10 passed（结果已归档） |
| Branch Protection | `check_branch_protection.py --check` | **预期失败**（需 GitHub 权限采集） |

## 4. 第二轮补充（2026-11-24 晚）

| 审计项 | 处理 | 验证 |
|---|---|---|
| 19/17：A5 必须服务端重算，不能只收调用方 impact_analysis | `create_regression_request(impact_base_sha=...)`：服务端 `compute_impact_analysis` 从真实 Git diff 重算；调用方 checksum 不一致 → `IMPACT_ANALYSIS_MISMATCH`；非法 base SHA → `IMPACT_ANALYSIS_UNCOMPUTABLE`；`environment_snapshot.impact_analysis.source` 记录 server/caller | `tests/test_aiqe_v16_014_catalog_scope.py` 9 passed（含 4 条新增） |
| TC-005 危险请求必须证明“目标 0 请求” | 增加可到达但不在 allowlist 的受控目标（localhost），断言节点 BLOCKED 且目标计数器 0 | 平台 E2E 10 passed |
| TC-009 E1–E6 故障归类可追溯 | 增加 `sync_experiment_result` 终态收敛、`changed_dimension` 对照、仅 COMPLETED 可记录 SUPPORTED/REFUTED；UNKNOWN 记录结论抛错 | 平台 E2E 10 passed |
| TC-006 已知 flaky | 去掉对 `handles[0]` 插入顺序的依赖（按 created_at/id 排序 + scope 匹配）；`_launch` 改为 3 轮真实 claim 轮询（仍禁止人工 fallback） | 连续 3 次 10 passed |

## 5. 第三轮补充（2026-11-24 深夜）

| 审计项 | 处理 | 验证 |
|---|---|---|
| P0-1 独立 Reviewer 无法证明 | 新增 `acceptance/records/*.json` 机制 + `governance/review-roles.yaml` 角色域矩阵 + `record_acceptance.py` CLI；矩阵不能自证 REVIEWED，同角色域/pending/缺 artifact 全部拒绝；PR 模板增加 `Reviewer 角色域` 字段并强制校验 | 10 条 acceptance 测试 + PR 模式 3 条新测试 |
| TC-007 Worker crash（claim/execute/persist/ack） | 新增崩溃恢复 E2E：claim 后租约过期 → reconciler 重排 → 真实 dispatch/Worker 完成 → 迟到结果 fencing 拒绝 → 重复投递不新增 Assertion | 平台链路 6 PASS / 2 BLOCKED / 2 NOT_RUN |
| V16-004 真实 PG 只读 role | 新增 `check_pg_readonly_role.py`（角色属性/写拒绝/read-only/timeout 检查，DSN 脱敏）+ `evidence/pg-readonly-role.json=NOT_PROVEN`；Gate B evidence 因此为 NOT_PROVEN | 5 条 PG 测试（含“仓库证据不得伪称 PASS”） |
| TC-AIQE-007 平台映射 | 映射到 TC-PLATFORM-004（Worker 崩溃恢复） | 矩阵 strict 校验 0 error |

## 6. 第四轮补充（2026-11-24 夜）

| 审计项 | 处理 | 验证 |
|---|---|---|
| §6.3/§10.13 A0–A6 未真正端到端 | TC-010 改为 **A1–A6 全链路真实 Adapter**（A0 编排由 run_plan 承担）：6 个 AgentExecution、每 Agent 真实工具调用与审计对账、A4/A6 证据经服务端 Resolver | 平台链路 7 PASS / 2 BLOCKED / 1 NOT_RUN |
| 生产缺陷：A3 无法通过 AgentTask 运行 | `WorkflowPlannerAgent.__init__` 不接受 `model`，`get_agent` 传参即 TypeError。已修复并加回归测试覆盖 A0–A6 全部构造 | `test_get_agent_accepts_model_for_every_agent` |
| §10.21 证据字段统一 Schema | 新增 `traceability/runtime-evidence.schema.json`（PROVEN 必须含 artifacts + run_id/run_ids；refs 键白名单），checker 接入 jsonschema，CI traceability job 安装 jsonschema | 新增 2 条 schema 测试 |

## 7. 未完成（后续批次）

1. **产品级 TC-AIQE-001..010**：需隔离 Test 环境按 merged spec §20 重跑并归档产物。
2. **独立验收签署**：机制已就绪，70 条需求仍需真实 Reviewer 逐条生成
   `acceptance/records/*.json`（当前 0 条）。
3. **Gate G**：需要 GitHub 仓库权限执行
   `check_branch_protection.py --capture`，再重算 verdict。
4. **Gate F**：镜像重建 digest/SBOM、干净节点部署、PG 备份恢复/PG 只读 role/
   Vault 生产/告警原始日志。
5. **A5 剩余**：`create_regression_plan` 写工具仍 UNAVAILABLE（需审批与副作用门禁），
   A5 自动生成回归计划并调用 Regression API 的端到端链路尚未打通。
6. **TC-006 flaky 观察**：已消除已知顺序/时序假设，连续多次通过；若再次出现需抓取
   失败时的 handle/scope/事件快照，不得以重跑掩盖。
