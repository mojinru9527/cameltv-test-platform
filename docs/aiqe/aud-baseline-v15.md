# AIQE v1.5 AUD 整改基线映射（PR-AUD-00）

> 基线：`origin/main` = `b0f6cdd4ccc3f54dc762873a5d01ab7c9e07f1a3`（2026-11-14，"docs(aiqe): 使用与项目接入指南 + 引导脚本 (#596)"）。
> 分支：`feature/aiqe-v15-aud-remediation`（独立 worktree，DeepSeek_Harness / direct）。
> 依据：`CamelTv_AIQE_AUD_Remediation_v1.5_Full.md`（v1.5，2026-11-18）+ `docs/platform-refactor/13-ai-quality-agent-merged-spec.md`。
> 本文是 v1.5 §07 `PR-AUD-00` 要求的"基线刷新 + 代码映射"交付物：**只记录可复核事实**，每条结论都可由文件路径 / 命令复现。

## 0. 结论摘要

| 批次 | AUD | 现状 | 本轮是否已整改 |
|---|---|---|---|
| 第一批 | AUD-001 SSRF/Redirect/DNS | 缺失（HTTP Driver 自动跟随跳转、无目标策略） | ✅ 已交付 |
| 第一批 | AUD-002 DB Query Registry | 部分（只读 SQL 校验存在，无登记/项目注入/超时） | ⬜ |
| 第一批 | AUD-003 Secret 全链路 | 部分（headers 脱敏，输出/持久化无分类器） | ⬜ |
| 第一批 | AUD-004 实验→真 Run | **违规**（`uuid4()` 伪造 verification_run_id + 直接 completed） | ⬜ |
| 第一批 | AUD-005 Capability/Preflight | 部分（boolean available，无 VERIFIED 状态、无 Preflight） | ⬜ |
| 第一批 | AUD-006 状态一致性/恢复 | 部分（lease/fencing 无、事件无生产者、Reconciler 无） | ⬜ |
| 第二批 | AUD-007 Assertion Engine | **缺失**（断言写死在 node_executor，`run_assertion_results` 零写入） | ⬜ |
| 第二批 | AUD-008 Artifact 生命周期 | 部分（模型+存储+GC 有，无 Upload/Download API、无 Viewer、GC 硬删） | ⬜ |
| 第二批 | AUD-009 Regression 幂等/SHA | **缺失**（`min_length=7`、无 fingerprint、无 deployed SHA） | ⬜ |
| 第二批 | AUD-010 Regression 终态/对比 | **缺失** | ⬜ |
| 第二批 | AUD-011 Mixed Workflow Dogfood | **缺失**（占位 E2E 只断言 body.count()==1） | ⬜ |
| 第二批 | AUD-012 Defect Draft 可复现 | 部分（草稿服务存在，evidence 仅前缀字符串校验） | ⬜ |
| 第三批 | AUD-013 A0–A6 Registry/Orchestrator | **缺失**（无 AgentProtocol/AgentResult/Registry/DAG） | ⬜ |
| 第三批 | AUD-014 Requirement Contract | **缺失**（无 Contract 表/状态机/source ref 解析） | ⬜ |
| 第三批 | AUD-015 结构化 Case | **缺失**（无 automation_grade/covers_ac_ids/oracle_ref） | ⬜ |
| 第三批 | AUD-016 A4 Evidence-grounded | 部分（schema 校验有，evidence 不做服务端解析） | ⬜ |
| 第三批 | AUD-017 A5 影响图 | 部分（文件名子串规则，无 git diff/symbol/trace path） | ⬜ |
| 第三批 | AUD-018 A6 Benchmark | **违规**（接受前端自报 false_positive_rate） | ⬜ |
| 第三批 | AUD-019 Noise Intelligence | 部分（10 个资源 Detector ≠ 12 类目；无 Observation 表） | ⬜ |
| 第三批 | AUD-020 多端真实 Driver | 部分（boolean available；iOS 硬关闭；无 PlatformBinding） | ⬜ |

## 1. 基线事实

| 项 | 事实 |
|---|---|
| Commit | `b0f6cdd4ccc3f54dc762873a5d01ab7c9e07f1a3` |
| Alembic head | `20261123_ta033_mutation_ledger`（单 head；本轮新增 `20261124_aud001_target_policy`） |
| 后端入口 | `test-platform-v2/backend/app/main.py`；AIQE 路由 `app/api/v1/aiqe_*.py`（前缀 `/api/v1/aiqe`） |
| AIQE 目录 | `app/aiqe/{models,services,drivers,agents,adapters,security}` |
| AIQE 测试 | `tests/test_aiqe_*.py`（45 个模块）+ `tests/e2e/aiqe/` |
| 远端可达性 | 2026-11-18 本机 `git fetch` 无法连接 github.com:443（代理不可用），基线取本地 `origin/main`；如远端有新提交需重新 fetch 后复核 |

### 1.1 复现命令

```powershell
cd test-platform-v2/backend
python -m alembic heads
python -m pytest tests/ -q -k "aiqe" --ignore=tests/e2e   # 基线 461 passed
rg "append_event\(" app/                                  # 仅 event_service 定义
rg "RunAssertionResult\(" app/                            # 仅模型
rg "put_artifact\(" app/                                  # 仅定义
rg "verification_run_id=.*uuid" app/aiqe                  # triage_service.py:73 伪造
```

## 2. AUD-001（已交付）

**问题**：`HttpDriver` 使用 `httpx.Client(follow_redirects=True)`，目标 URL 完全由 Workflow 节点输入决定，无 host/端口/方法/私网策略，不校验 DNS 实际地址，跨主机跳转无条件跟随。

**交付**：

| 文件 | 作用 |
|---|---|
| `app/aiqe/models/security.py` | `TargetPolicyRecord`（`aiqe_target_policies`，项目/环境级、带 version、active） |
| `alembic/versions/20261124_aud001_target_policy.py` | 迁移（幂等：已存在表则跳过，可 downgrade） |
| `app/aiqe/security/target_policy.py` | `TargetPolicy`（不可变快照）、`TargetPolicyResolver.resolve(project_id, environment_id)`（只读服务端配置，拒绝调用方覆盖）、`upsert_target_policy`（版本乐观锁） |
| `app/aiqe/security/safe_target.py` | `SafeTargetValidator`：scheme/userinfo/端口/方法/主机白名单（`*.suffix`）/DNS 全地址校验/私网与保留段/混淆数字写法/zone id/IDNA；`validate_redirect` 逐跳重校验 |
| `app/aiqe/security/dns_pin.py` | `pinned_dns`：请求期间把主机固定到已验证 IP（DNS Rebinding 防护） |
| `app/aiqe/security/safe_http.py` | `SafeHttpExecutor.request()`：校验先行、`follow_redirects=False` 手动逐跳、请求/响应限额、`policy_version` + `target_resolution_snapshot` 证据、拒绝返回 `blocked` |
| `app/aiqe/services/node_executor.py` | http 节点统一走 `SafeHttpExecutor`；节点输入的 `allow_private/allowed_hosts/...` 被忽略并留痕；策略拒绝 → `BLOCKED`；playwright 导航同样先校验 |
| `tests/test_aiqe_aud001_target_policy.py` | 46 条：13 类私网/混淆地址、8 类非法 URL、白名单/端口/方法、DNS 多地址、DNS rebinding、Redirect 私网/跨主机/上限/307/302、响应截断、请求体上限、真实本地 HTTP 服务端到端、节点级与安全事件可追踪 |

**默认值**：未配置策略 = `deny_all`；私网/回环需 `allow_private_cidrs` 显式授权；`blocked_cidrs`（169.254/16、100.64/10、0/8、240/4、fe80::/10、64:ff9b::/96 等）任何策略都不能放行；默认 `max_redirects=0`。

**未覆盖（后续）**：Runner 侧 egress 防火墙与容器网络 deny-by-default 属于 DevOps 交付；`proxy_profile_id` 字段尚未接入（当前策略强制直连）。

## 3. 第一批剩余缺口（按代码事实）

### AUD-002 DB Read-only / Query Registry

- 现状：`app/aiqe/drivers/db_readonly_driver.py` 只有 `assert_readonly`（单条 SELECT/WITH/EXPLAIN、禁写关键字）+ SQLite `PRAGMA query_only` / PG `SET TRANSACTION READ ONLY`。
- 缺口：无 Query Registry（`query_key + version + statement + allowed_params + max_rows + max_execution_ms + result_schema`）；无 `project_id` 服务端注入；无 `statement_timeout`/`lock_timeout`；无 `query_hash`；无行/列脱敏；`node_executor` 未接入 db driver（`driver="db"` → `UNSUPPORTED_DRIVER`）。

### AUD-003 Secret 全链路

- 现状：`httpx_driver.redact_headers` / `safe_http.redact_headers` 只脱敏请求/响应头；`run_context.set_output` 拒绝写入 `${secrets.*}` 字面量。
- 缺口：无 `SensitiveDataClassifier` / `EvidenceRedactor`；`job_consumer` 把 `result.detail`（含完整请求头与响应体）写入 `node_runs.output_ref` 与 `step_attempts.output_summary_json` —— 登录节点的 `access_token` 会明文落库；无 Secret Handle 表/服务；无 canary 扫描测试。

### AUD-004 反事实实验

- 现状：`app/aiqe/services/triage_service.py:73` `verification_run_id=verification_run_id or str(uuid.uuid4())`，`:75` `status="completed"`；无 `TestRun`/`NodeRun`/Assertion/Artifact 绑定。
- 缺口：E1–E6 语义与 v1.5 §04 表格不一致（E2/E4 互换、E3 改 Profile、E4 重置数据）；`validate_change` 不校验变量名；无 `baseline_run_id`/snapshot/diff/verdict；无 Reconciler 收敛。

### AUD-005 Capability / Preflight

- 现状：`NodeCapabilityManifest.available: bool`；`select_nodes` 无生产调用点。
- 缺口：无 6 态 `capability_status`；无 Preflight（Run 创建/派发前不检查能力）；无签名 Manifest；无 VERIFIED 证据链。

### AUD-006 状态一致性与恢复

- 现状：`job_consumer` 原子认领（pending→running + lease_expires_at）；`dag_scheduler` 聚合节点→Run 状态。
- 缺口：无 fencing token（旧 Worker 迟到结果不被拒）；`append_event` 无生产调用（Run 无事件时间线）；无 Reconciler；无"节点终态但 Run 未收口"扫描；无 100 并发/Worker kill 测试。

## 4. 第二批缺口要点

- AUD-007：断言逻辑内联在 `node_executor`（`expected_status`/`expect_text`），无 Observation/Registry/Engine；`run_assertion_results` 零写入；`GET /runs/{id}/assertions` 不存在；`dag_scheduler._finalize` 用节点状态直接推 Run PASS（与 v1.5 §06-7 冲突）。
- AUD-008：`put_artifact` 仅测试调用；无 Upload/Download API；无 `project_id/upload_status/retention_until`；GC `db.delete` 硬删无墓碑；无 Viewer。
- AUD-009：`regression_service` `fixed_sha` 只要求 ≥7 位；无 fingerprint/唯一约束；无 deployed SHA 校验；创建的 Run 无 NodeRun（永远 QUEUED）。
- AUD-010：无 `RunTerminalEventHandler`、无 `RunComparisonSnapshot`、无 `/comparison` `/cancel` 路由。
- AUD-011：`tests/e2e/aiqe/test_tc_aiqe_001_010.py` 仅断言页面 `body.count()==1`；`RunContext` 无生产调用；无跨系统混合 Workflow 种子。
- AUD-012：`defect_service.validate_reproduction` 仅校验 `artifact:/event:/run:/node:/signal:` 前缀；无存在性/项目/run scope 校验；无 ReproductionBundle。

## 5. 第三批缺口要点

- AUD-013：`BaseAgent.run(input_text)`；无 `AgentProtocol`/`AgentResult`/Registry/DAG/工具白名单；`RequirementAgent.key="A0"` 与 A0=Orchestrator 冲突。
- AUD-014/015：无 Contract / 结构化 Case 持久化（`automation_grade`/`covers_ac_ids`/`oracle_ref` 全仓 0 命中）。
- AUD-016：`FailureTriageAgent` schema 严格（confidence 必须为 null、禁止自动关缺陷），但 evidence ref 不做服务端解析。
- AUD-017：`change_impact_agent` 仅按文件名子串映射 area → suite 名，无 git diff/symbol/trace path。
- AUD-018：`learning_service.evaluate_candidate(false_positive_rate, sample_size)` 直接采用调用方自报数值（v1.5 明令禁止）。
- AUD-019：`interference_service.KINDS` 10 个资源信号，缺 `UI_OVERLAY/CROSS_FEATURE/AUTOMATION/FLAKY/REQUIREMENT_GAP/TEST_DATA/TIME` 类别；无 `InterferenceObservation` 表；`NoiseRule` 缺 11 个治理字段且创建即 active。
- AUD-020：`available: bool` + `IOS_ENABLED=False` + `node_executor` 硬编码 Android；无 PlatformBinding/Preflight/按平台聚合。

## 6. 实施顺序（本轮起的计划）

按"风险消除 / 代码量"排序，每项独立可验证：

1. ✅ AUD-001（本轮）
2. AUD-004：删除伪造 verification_run_id，E1–E6 语义与单变量校验对齐 v1.5 §04，实验必须绑定真实 `TestRun`（`status=QUEUED`，Reconciler 收敛）。
3. AUD-003：`SensitiveDataClassifier` + 输出脱敏 + Secret Handle 表；`job_consumer` 停止明文落库；canary 测试。
4. AUD-006+007：`result_writer` 统一写 `run_events` + `run_assertion_results`，`_finalize` 改为按 required assertion 聚合。
5. AUD-002：Query Registry + 项目注入 + 超时；`node_executor` 接入 db driver。
6. AUD-005：capability 6 态 + Preflight（Run 创建前 BLOCKED）。
7. AUD-008/009/010：Artifact 生命周期、Regression fingerprint/40 位 SHA/deployed SHA、终态同步 + 对比快照。
8. AUD-012/016：evidence ref 服务端解析（存在性 + 项目/run scope）。
9. AUD-011：混合 Workflow Dogfood harness（真实 Driver）。
10. AUD-013…020：Agent Protocol/Registry/DAG、Contract/Case 模型、A5 影响图、A6 Benchmark、Noise 12 类目、Platform Binding。

> 每项完成条件遵循 v1.5 §00-8：代码 + 单测/集成测试 + 正负向/安全/权限/并发路径 + 真实 Run 证据 + OpenAPI/迁移/前端同步 + 无 secret 日志 + PR 描述含代码路径/测试命令/CI/回滚。
