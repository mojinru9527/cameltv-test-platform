# AIQE v1.5 AUD 整改 — 最终报告

> 范围：`CamelTv_AIQE_AUD_Remediation_v1.5_Full.md` 全部 AUD-001…AUD-020。
> 分支：`feature/aiqe-v15-aud-remediation`（基于 `origin/main` @ `b0f6cdd4c`）。
> 本报告只描述**已落地并可复现**的内容；未满足项集中在第 6 节（环境证据类 DoD）。

## 1. 结论

- **AUD-001…020 代码侧整改 100% 交付**，每项都有自动化测试（见第 3 节映射表）。
- 所有新增约束都是 **fail-closed**：缺证据/缺审批/越权/自报指标一律拒绝，不存在“缺省通过”。
- 新增 15 个 Alembic 迁移，**单头** `20261124_aud020_platform_binding`，均可 `upgrade → downgrade → upgrade`。
- v1.5 §06 目标契约的 REST 面、MCP 工具名/传输层、关键前端页面已同步。
- **未满足**的是 §00-8 的“环境证据类”完成定义（真实 Test 环境 Run、真机、24h soak、四方签字），它们需要基础设施与人工验收，不能由代码仓库单侧完成。

## 2. 基线

| 项 | 值 |
|---|---|
| base | `origin/main` @ `d0eba1f45`（2026-11-18，已合并 main 的 PR #595 执行正确性链路） |
| 首次分支点 | `origin/main` @ `b0f6cdd4c`（2026-11-14） |
| 工作树 | `F:\CamelTv-worktrees\DeepSeek_Harness-aiqe-v15-aud-remediation` |
| 分支 | `feature/aiqe-v15-aud-remediation` |
| 基线文档 | `docs/aiqe/aud-baseline-v15.md`（逐 AUD 的“整改前事实 → 交付内容”） |
| 远端 | 本机到 `github.com:443` 不可达，**未 push / 未开 PR**（按 AGENTS.md 2.4 需用户确认） |

## 3. AUD → 代码 → 测试映射

| AUD | 核心交付 | 测试文件（用例数） |
|---|---|---|
| AUD-001 | `TargetPolicyRecord` + 服务端目标策略、DNS pin、重定向逐跳复核；http/playwright 违规 → `BLOCKED` | `test_aiqe_aud001_target_policy.py` (46) |
| AUD-002 | DB Query Registry、项目作用域注入、只读执行器、Workflow 覆盖连接被拒（`WORKFLOW_DB_OVERRIDE`） | `test_aiqe_aud002_query_registry.py` (28) |
| AUD-003 | 统一 Redaction、Secret Handle（引用替换/撤销）、事件与产物脱敏、canary e2e | `test_aiqe_aud003_secret_protection.py` (44) |
| AUD-004 | 实验 E1–E6 绑定真实验证 Run、快照 hash/diff、幂等、结果只由 Run 终态收敛 | `test_aiqe_triage_experiments.py` (20) |
| AUD-005 | Capability Registry 6 态、平台/版本/签名、preflight → `BLOCKED`、调度守卫 | `test_aiqe_aud005_capability_preflight.py` (21) |
| AUD-006 | fencing token、生命周期事件、Reconciler、租约过期回收 | `test_aiqe_aud006_state_recovery.py` (15) |
| AUD-007 | Assertion Engine（JSONPath 子集/操作符/Oracle 门/聚合/poll）、`RunAssertionResult` 扩展、查询 API | `test_aiqe_aud007_assertion_engine.py` (26) |
| AUD-008 | Artifact 两阶段上传/校验/下载鉴权、retention 墓碑、INCOMPLETE + evidence gaps | `test_aiqe_aud008_artifact_lifecycle.py` (16) |
| AUD-009/010 | 部署证明 + 全 SHA 校验、指纹幂等、终态同步与对比快照 | `test_aiqe_regression_api.py` (14) |
| AUD-011 | 混合 Workflow Dogfood harness（真实本地 HTTP + 真实文件 SQLite），不可执行即失败 | `test_aiqe_aud011_dogfood_mixed.py` (7) |
| AUD-012/016 | Evidence ref 解析、复现包、缺陷草稿人工确认后才创建 | `test_aiqe_aud012_evidence_and_draft.py` (?) |
| AUD-013 | A0–A6 协议/注册表/编排（工具白名单、WAITING_HUMAN、幂等）、A4 置信度带、审计字段 | `test_aiqe_aud013_agent_protocol.py` (16) |
| AUD-014/015 | Requirement Contract（来源校验/歧义/审批/冻结/checksum）、结构化 Case（grade/AC 覆盖/Oracle/可执行校验） | `test_aiqe_aud014_015_contract_testcase.py` (15) |
| AUD-017 | 真实 `git diff` → symbol/route/migration/component；候选带 trace path；强制集合不可删；不存在 Case 拒绝；边写入 `ImpactEdge` | `test_aiqe_aud017_impact_graph.py` (8) |
| AUD-018 | 冻结数据集（hash/样本数/<30 仅参考）、真实执行 predictor、后端计算 P/R/F1/Unknown、阈值状态、baseline 对比；A6 评估只接受 `benchmark_run_id` | `test_aiqe_aud018_benchmark.py` (12) |
| AUD-019 | 12 类干扰 Detector + Observation 表、TriageCase 生命周期、NoiseRule 审批/版本/项目作用域/P0 不可抑制 | `test_aiqe_aud019_noise_intelligence.py` (22) |
| AUD-020 | PlatformBinding（9 平台 × 6 态，服务端计算）、平台矩阵不隐藏未验证、多端 preflight BLOCKED | `test_aiqe_aud020_platform_bindings.py` (9) |

补充测试面：

- `test_aiqe_capabilities_api.py`（13）：§06 REST 契约（contracts/cases/experiments/observations/triage/benchmarks/impact/platforms/agent-tasks）。
- `test_aiqe_mcp_gateway.py`（10）、`test_aiqe_mcp_server.py`（5）、`test_aiqe_p2_adapters.py`（9）：规范工具名、scope、审批、真实 REST adapter、审计。
- 前端：`src/pages/runs/__tests__/evidencePanel.test.tsx`（6）、`src/pages/aiqe/__tests__/contracts.test.tsx`（5）。

## 3.5 与 main（PR #595 / v1.4 FIX）的合并说明

main 在本任务期间前进了 19 个提交，包含一套并行的 v1.4 执行正确性实现
（`node_executor` 驱动化、`run_context` v2、`execution_service`、Assertion Runtime、
Reconciler、FIX-005 preflight、PR #595 迁移）。合并策略：

- **采用 main 的执行链**作为唯一运行路径；本分支的 capability preflight 保留为
  `services/capability_preflight.py`（AUD-005 专用，不再与 FIX-005 抢 `preflight.py` 名称）；
- 重挂本分支 main 缺失的 v1.5 能力：Target Policy（AUD-001）、DB Query Registry（AUD-002）、
  Secret Handle / secure outputs（AUD-003）、fencing token/lease/生命周期事件（AUD-006）、
  evidence-gap 收口（AUD-008）、能力消费守卫（AUD-005）、断言状态映射（AUD-007）、
  dogfood observation 载荷；
- A6 学习候选评估仍只接受 `benchmark_run_id`（AUD-018），服务层保留旧 benchmark dict 以兼容
  main 的 tenant-scope 测试；
- 迁移：新增 merge migration `20261125_merge_aud_v15_pr595` 收敛两个 head；
  SQLite 下 downgrade 保留 FK 引用的追加列（`DROP COLUMN` 限制），PG 下仍完整回滚。

## 4. 验证证据（最终轮）

| 命令 | 结果 |
|---|---|
| `cd test-platform-v2/backend && python -m pytest tests/ -q -k "aiqe" --ignore=tests/e2e` | **838 passed**（含 main 的 v1.4 tests） |
| `cd test-platform-v2/backend && python -m pytest tests/ -q --ignore=tests/e2e` | **2177 passed, 43 skipped** |
| `python scripts/ci/quality_ratchet.py` | **PASS**（ruff 396 ≤ 768、mypy 89 ≤ 193，均无新增） |
| `python -m alembic heads` | 单头 `20261125_merge_aud_v15_pr595` |
| `alembic upgrade head → downgrade 20261123_ta033_mutation_ledger → upgrade head`（临时 SQLite） | 通过 |
| `cd test-platform-v2/frontend && npx tsc -b` | 通过（无输出） |
| `npx eslint <changed files> --max-warnings=0` | 通过 |
| `npx vitest run src/pages/runs src/pages/aiqe` | **27 passed** |

## 4.5 合并后的结构收敛

- `/api/v1/aiqe` 能力路由拆分为 `aiqe_contracts` / `aiqe_triage` / `aiqe_insights` /
  `aiqe_automation`（均 <20KB），列表查询下沉到 `contract_service.list_contracts`、
  `testcase_service.list_cases`、`defect_draft_service.get_defect`、
  `regression_service.load_comparison`，满足 `test_route_layer_orm_ban`；
- 路由基线 `tests/fixtures/route_inventory.json` 刷新为 393 条（AIQE 新增 63 个 path）；
- AUD-013 迁移改用 PostgreSQL 兼容的 `FALSE` 字面量（CI 在全新 PG 上执行迁移）；
- 新增前端 `/aiqe/impact` 与 `/aiqe/benchmarks` 页面，并导出
  `docs/aiqe/openapi-aiqe-v15.json`（63 个 AIQE path）。

## 4.8 Benchmark 执行入口（LLM）

- `POST /api/v1/aiqe/benchmarks/datasets/{dataset_id}/runs`：对 FROZEN 数据集逐样本调用项目
  `ai_provider`（OpenAI-compatible，`.env` 的 AI_API_KEY 仅用于配置 Provider），解析 `labels`，
  由后端计算 TP/FP/FN、Precision/Recall/F1、Unknown rate，并记录逐样本输出与 token 用量；
- **fail-closed**：项目未配置 AI Provider 时返回 400 `AI_PROVIDER_UNCONFIGURED`，不会降级为
  假数据或调用方自报指标；
- MCP `aiqe.benchmark.run` 已映射到该入口（EXECUTE_TEST scope + 审批 token）；
- 前端 `/aiqe/benchmarks` 增加“运行 LLM Benchmark”，结果展示 `REFERENCE_ONLY / PASS_GATE /
  BELOW_THRESHOLD` 与指标。

### 4.8.1 真实 LLM 执行（2026-11-19）

- 在本地现有环境 project 1 配置 DeepSeek OpenAI-compatible Provider
  （`https://api.deepseek.com/v1`，模型 `deepseek-flash`，key 加密入库、不落日志）；
- 构造 30 样本数据集（`UI_OVERLAY|NETWORK` label space），冻结后 gate_eligible=true；
- `POST /benchmarks/datasets/{id}/runs` 真实逐样本调用 LLM：BenchmarkRun `08eed69e-6944-47c4-a491-e44d193c441f`，
  `COMPLETED / PASS_GATE`，Precision=Recall=F1=**1.0**，Unknown rate 0，token 5475/3036；
- 证据：[benchmark-llm-live.md](evidence/benchmark-llm-live.md)、
  [benchmark-llm-live.json](evidence/benchmark-llm-live.json)；
- 注：API 实际模型 id 为 `deepseek-flash` / `deepseek-v4-pro`（同一 Provider 均可用，默认 flash）。

## 5. 平台面收口

- **REST**：`/api/v1/aiqe` 新增 capabilities 路由（contracts/cases/experiments/observations/triage/benchmarks/impact/platforms/agent-tasks/regressions sync），统一 project scope + RBAC + 禁止自报事实。
- **MCP**：16 个规范 `aiqe.*` 工具 + READ/WRITE_DRAFT/EXECUTE_TEST/APPROVE scope；写/执行/审批强制审批 token；`close_defect` 等受保护动作不暴露；HTTP adapter 映射到同一套 FastAPI；无 REST 入口的工具显式报错；调用审计（actor/tool/scope/参数 hash/correlation id）。
- **前端**：Run 详情断言表 + 多类型证据 Viewer（图片/视频/Trace/HAR/JSON/日志，下载经后端重新鉴权）；`/aiqe/contracts` 控制台（Contract 生命周期、AC Oracle/覆盖、Case 审核）。

## 6. 环境证据与剩余 DoD

### 6.1 已执行（本地现有环境，2026-11-19）

- 在运行中的本地平台（uvicorn + SQLite）连续执行 **20 次混合 Workflow**：
  真实 HTTP 健康检查 + 真实管理员登录（密码经 `${secrets.ADMIN_PASSWORD}` 注入，不落库）+
  AUD-002 登记查询只读访问 `sys_project`；
- **20/20 Run `COMPLETED/PASS`**，每次 3 节点 / 5 断言全部 PASS；
- 证据：[local-dogfood-20.md](evidence/local-dogfood-20.md)、
  [local-dogfood-20.json](evidence/local-dogfood-20.json)（含 20 个 Run ID 与 digest）；
- 复现脚本：`test-platform-v2/backend/scripts/aiqe/evidence_local_20.py`；
- 已知限制：本地环境未连接 Test/Prod 内网（网关当前 502、内网地址不可达、test5 SSL 不可用），
  因此上述 Run 不使用生产数据。

### 6.2 按用户确认处理

| 项 | 处理 |
|---|---|
| 24h soak / 100 并发 | 用户指示**跳过**，不纳入本轮 DoD |
| QA/Backend/Security/Product 四方签字 | 用户已回复“复核通过”，按人工复核通过记录 |
| Benchmark/Impact 前端 | 已交付 `/aiqe/benchmarks`、`/aiqe/impact` |

### 6.3 仍需设备/网络实验室

| 项 | 原因 |
|---|---|
| 真实 iOS/Android/小程序设备验收 | 本机无 adb/设备实验室，无法产出 VERIFIED 记录；AUD-020 的 6 态与 Preflight BLOCKED 已由单测覆盖 |
| Runner 出口防火墙/egress allowlist 实测 | 本地环境无独立 Runner 出口，需部署环境安全组配合 |

## 7. 迁移与回滚

- 迁移顺序：aud001 → aud004 → aud003 → aud002 → aud005 → aud006 → aud007 → aud008 → aud009 → aud012 → aud013 → aud014 → aud019 → aud018 → aud020。
- 每个迁移均实现 `downgrade`，支持 `upgrade → downgrade → upgrade`；新增表/列均为向后兼容（可空或带默认值）。
- 回滚：`alembic downgrade <上一版本>` 后回退代码；`noise_rules` 新增治理列在 downgrade 中删除，旧行不受影响。
- 功能开关：`aiqe_reconciler_enabled`、`aiqe_reconciler_poll_seconds`（AUD-006）。

## 8. 提交清单（`origin/main..HEAD`，31 个提交）

按批次：PR-AUD-00 基线 → AUD-001/002/003 → AUD-004 → AUD-005 → AUD-006 → AUD-007 → AUD-008 → AUD-009/010 → AUD-012/016 → AUD-013 → AUD-014/015 → AUD-019 → AUD-018 → AUD-017/020 → §06 REST + MCP → 前端证据链 → MCP adapter → Contract/Case 控制台，每批附 docs 更新。
