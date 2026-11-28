# G7 独立审计报告 — Driver 能力真实性 / 多端边界 / Artifact 安全 / 脚本与生产化

> **STATUS: HISTORICAL** — 本文记录 2026-11-2x 当时的执行事实与结论；其中 PASS/VERIFIED 等表述不代表当前发布判定。当前状态以 `release-verdict.json`、`E2E-Coverage-and-Blockers.md` 与 `governance/production-evidence.json` 为准。


- 审计组：G7（capability registry / platform adapters / artifact service / scripts/aiqe / 依赖与 CI / 监控指标）
- 负责 Issue：**V16-015、V16-016、V16-018、V16-021、V16-022、V16-023、V16-024**
- 仓库工作树：`F:\CamelTv-worktrees\DeepSeek_Harness-aiqe-v1-6`
- 分支 / 基线：`release/aiqe-v1-6`，HEAD `86a44b2cb`（= 规格文档引用的审计快照 `86a44b2cbb7c9c44d3ef6af1e324d1f42c3eae6f`）
- 工作树状态：15 个已修改文件属**在途 V16-001 改动**（`security/target_policy.py`、`services/execution_service.py`、`services/node_executor.py`、`services/dogfood.py`、`api/v1/execution_jobs.py`、`scripts/aiqe/*`、相关测试），另有未跟踪的 `docs/aiqe/v1.6/` 与本报告。本文行号：被 V16-001 修改过的文件按**当前工作树**行号，其余文件行号与 HEAD 一致。
- 规格文档：`C:\Users\26029\Downloads\CamelTv_AIQE_V1.6_修复与生产化开发实施计划.md`
- 审计方式：只读静态审计 + 只读 git/文本检索。**未执行 pytest、未连库、未改任何业务文件**；本文件是唯一写入。

## 0. 判定口径与总体结论

判定严格按规格「实施要求 / 验收（Acceptance）」逐条对照代码：只有调用链真实存在、且不是 TODO/空实现/Mock 才计 IMPLEMENTED；部分存在但关键要求在正式入口不成立计 PARTIAL；核心要求无实现计 MISSING。

| Issue | 状态 | 一句话依据 |
|---|---|---|
| V16-015 | **PARTIAL** | 6 态能力模型、心跳、版本变更降级、Preflight 拦截都已存在；但 `VERIFIED` 无任何生产写入者（只由脚本/测试 `mark_verified` 写入），模型缺 verification_run_id/artifact refs/OS/镜像/设备字段，正式 Launch 的 Preflight 用的是另一套「字符串 evidence + 30s 心跳」实现且接受 AVAILABLE/声明平台，自动降级无生产调用点。 |
| V16-016 | **PARTIAL** | 服务端计算平台状态、真机平台要求 VERIFIED、iOS 在 DeviceBroker 被门禁、Android/Appium 有执行链；但 Miniapp/Desktop/IoT Adapter 是**只有测试导入的死代码**，未接 `DriverProtocol`/`NodeExecutor`；PlatformBinding 缺 Environment/DevicePool/Runner 字段；DeviceBroker 为内存对象且全仓无生产引用；无动作粒度 Preflight、无性能指标采集；iOS 可仅凭 DB 行被标 VERIFIED。 |
| V16-018 | **PARTIAL** | 两阶段上传 + 服务端重算 sha256、跨项目 403、墓碑、路径穿越防护、worker 侧证据脱敏已实现；但缺 `created_by`/`retention_policy`（classification 只是存字段不生效）、上传会话 `expires_at` 不校验、无 Content-Type/期望大小校验、API 上传不做脱敏/Secret 扫描、无访问审计与 reconciliation、墓碑/CORRUPTED artifact 仍能被 Evidence Resolver 解析、GC 忽略 `retention_until` 且跨项目全局清理、外部 Runner 的截图/Trace 不落 RunArtifact。 |
| V16-021 | **MISSING** | `evidence_local_20.py:203` 仍保留 `...environ.get("AIQE_EVIDENCE_PASSWORD", "<weak-default>")` 弱默认值，`:10` 文档仍教 `--password <weak-default>`；`--password` 命令行参数仍存在；无「无凭据退出非 0」实现与测试；无历史凭据扫描/轮换记录。 |
| V16-022 | **PARTIAL** | 三套 `requirements*.lock` 带 hash、Dockerfile 用 digest + `--require-hashes`；但 required CI 的测试安装是 `pip install -r requirements.txt` + 浮动 `pytest`，lock 只做 dry-run；无 dependency groups；pytest 只有 slow/integration 两个 marker，无分层；AIQE 测试无 JUnit XML/coverage XML/Trace/commit SHA 产物；无干净环境单命令脚本。 |
| V16-023 | **MISSING** | 验收证据 JSON/MD 无 commit SHA、CI run、PR、镜像 digest；`config/aiqe-version.lock` 停留在 `ff5353a40`/`release-m15-20261114`/2026-11-13；v1.5 最终报告手工填写测试数量；v1.6 交付文档（矩阵/追踪矩阵/测试计划/发布报告）全部缺失；仓库无 evidence-index 生成器、无 AIQE CI workflow。 |
| V16-024 | **PARTIAL（核心缺口=监控/告警/限流/灰度全缺）** | 无任何 AIQE 指标实现（规格 §8.2 的 `aiqe_*` 指标 grep 命中 0，仓库无 prometheus/grafana/alertmanager）；无告警规则、无限流、无 AIQE 灰度阶段；仅存在既有的回滚文档/版本锁/回滚脚本与一次手工生产备份记录，且未做演练记录。 |

依赖关系（规格 §1 line 199）：本组 015/016/018 是「平台宣称 VERIFIED」的前置，当前结论意味着 **V1.6 不能宣称任何端 VERIFIED**。

---

## 1. V16-015 Capability Registry 从静态声明升级为运行证据

**状态：PARTIAL**

### 1.1 规格要求 → 实现映射

| 规格要求（§V16-015） | 现状 | 证据 |
|---|---|---|
| 5 个语义分级 REGISTERED/AVAILABLE/VERIFIED/DEGRADED/BLOCKED | 实现了 6 态枚举，但第 5 态是 `UNAVAILABLE`+`REVOKED`，不是规格的 `BLOCKED` | `test-platform-v2/backend/app/aiqe/services/capability_registry.py:46-52`、`app/aiqe/models/capability.py:41-45` |
| 记录 driver/version/platform/os-browser/runner image digest/device/supported actions/limitations/health/last_verified_at/verification_run_id/artifact refs | 只有 driver_key/driver_version/runner_version/manifest_version/manifest_signature/capabilities/platforms/verified_platforms/last_evidence_ref/heartbeat/verified_at；**无** os/browser version、镜像 digest、device id/model/os、supported actions、limitations、verification_run_id、artifact refs | `app/aiqe/models/capability.py:24-46`；迁移只有 `alembic/versions/20261124_aud005_capability_status.py:16-24` |
| VERIFIED 只能由成功的 Capability Verification Run 写入，API 不允许直接改 VERIFIED | 用户 API 确实不能写 VERIFIED（只有心跳/只读矩阵），但**生产代码没有任何写入者**：`mark_verified()` 在全仓只被测试和脚本调用 | `capability_registry.py:252-278`；全仓 grep `mark_verified(` 命中 25 处，全部在 `tests/`（`test_aiqe_aud005_capability_preflight.py:53-192` 等）与 `test-platform-v2/backend/scripts/aiqe/verify_android_device.py:169`；`app/` 内 0 调用 |
| Verification Run 必须执行真实动作（会话/导航/点击/输入/截图/断言/清理） | 不存在 Capability Verification Workflow/服务；唯一「验机」脚本不走 Job/Worker/DAG/Assertion，且**伪造 Run**：直接创建 `status="COMPLETED", outcome="PASS"` 的 TestRun（无 NodeRun/Job/断言），随后 `mark_verified` | `test-platform-v2/backend/scripts/aiqe/verify_android_device.py:114-125`（伪造 RUN）、`:126-155`（put_artifact）、`:169-171`（mark_verified）；`docs/aiqe/evidence/android-node/capability.json` 记录 `"status": "VERIFIED"` |
| 设备断连/镜像变化/Driver 版本变化/证书变化自动降级 | 仅 `register_manifest` 在 driver_version/runner_version 变化时失效（runner image digest 不跟踪）；`invalidate_verification()`/`mark_degraded()` 在全仓**无生产调用点**，设备断连/证书变化无任何检测路径 | `capability_registry.py:162-191`（版本比较）、`:281-307`（invalidate，grep 只有测试 `test_aiqe_aud005_capability_preflight.py:90`）、`:310-316`（mark_degraded，grep 只有测试 `:113`） |
| Workflow Preflight 只接受 VERIFIED（或明确批准的 AVAILABLE 测试策略），不能因 Manifest 声明 supported 就启动生产 Run | 存在两套 Preflight：①`run_launch` 走的 `services/preflight.py` 用 `row.available` + 30s 心跳 + `any(cap in caps)`（能力 OR 语义）+ 平台可空缺，文档还把 VERIFIED 定义为「evidence_ref 指向已保存自检证据」字符串；②`capability_preflight.select_nodes` 的允许集是 `{AVAILABLE, VERIFIED}`，且 `_node_has_platform` 接受**声明**平台（`platforms_json`），不存在「批准 AVAILABLE 的测试策略」对象 | `app/aiqe/services/preflight.py:29`（TTL=30）、`:62-66`（available 过滤）、`:90-110`（OR + 平台可选）；`app/aiqe/services/run_launch.py:20,204-211`；`capability_registry.py:56-58`（SCHEDULABLE 含 AVAILABLE）；`capability_preflight.py:176,206-214`（声明平台即通过） |
| 能力状态必须是「当前真实」 | 对外矩阵 API 用持久化 `row.available`（不是 `compute_effective_status`），心跳过期后仍显示 available；心跳 API 的 `verified` 也读原始 status | `app/aiqe/services/platform_matrix.py:19-29,32-63`（`row.available`）；`app/api/v1/aiqe_nodes.py:47-49` |

### 1.2 关键证据（可复核）

1. `test-platform-v2/backend/app/aiqe/services/capability_registry.py:43` — `DEFAULT_HEARTBEAT_TTL_SECONDS = 180`；但 `app/aiqe/services/preflight.py:29` — `HEARTBEAT_TTL_SECONDS = 30`，`docs/aiqe/runner-deployment.md:78` 也写 30 秒。三处不一致，实际 Launch 与矩阵判活口径不同。
2. `app/aiqe/services/capability_registry.py:112-116` — 只有 `last_evidence_ref` 非空 + `verified_at` 非空才 VERIFIED；`last_evidence_ref` 是**任意字符串**（`register_manifest(evidence_ref=...)`），没有 Run/Artifact 外键或存在性校验。
3. `app/aiqe/security/../services/platform_matrix.py:26` — 平台矩阵节点输出 `"available": bool(row.available)`；`build_platform_matrix` 的 cell 过滤同样用 `node.available`。心跳过期只在 `compute_effective_status` 里体现，矩阵不会降级。
4. `app/aiqe/services/capability_preflight.py:176` — `candidates = capability_registry.select_nodes(db, required, now=now)`，默认 `allow_statuses=SCHEDULABLE_STATUSES={AVAILABLE,VERIFIED}`（`capability_registry.py:56-58`），因此仅 AVAILABLE 的节点即可通过 Preflight。
5. `app/aiqe/services/preflight.py:98-110` — `_node_matches` 用 `any(cap in caps for cap in required)`（`required=("aiqe:playwright","browser.chromium")` 命中任一即可）且 `if platform and platforms and ...`（节点无 platform 声明时不校验平台）。这允许旧式 `aiqe:playwright` manifest 通过正式 Launch Preflight。
6. `test-platform-v2/backend/tests/test_aiqe_aud020_platform_bindings.py:157-178` — 测试用 `capability_registry.mark_verified(db, "node-ios", platforms=["ios"], evidence_ref="cap-1")`（`:39`）标 VERIFIED 后 `preflight_platform(...)["allowed"] is True`；说明「VERIFIED」完全可由 DB 行 + 任意字符串生成，无需真实运行。
7. `scripts/qa/aiqe_v14_local_dogfood.py:337-344` — 本地 dogfood 以 `evidence_ref=f"local://{node_id}/self-check"` 注册 manifest，`:173` 记录 `last_evidence_ref` 后 `record_evidence` 路径即可把节点置 AVAILABLE（`capability_registry.py:230-249`）并进入可调度集合。
8. `test-platform-v2/backend/tests/test_aiqe_capability_heartbeat.py:37` — 测试注册的能力名是 `"aiqe:playwright"`（不在 `STANDARD_CAPABILITIES`），说明 Registry 不校验能力词表；`docs/aiqe/runner-deployment.md:44-48` 直接教运维手工 `mark_verified`。
9. `app/aiqe/services/run_launch.py:227` — `capability_snapshot_json=snapshot_manifests(db)` 只快照 `available/evidence_ref`，没有 verification_run_id/policy 绑定，无法证明该 Run 的节点是在「已验证版本/环境/设备」上执行。

### 1.3 Gaps（可验证）

- **G15-1** 模型缺规格 §V16-015.1 字段：`os/browser version`、`runner image digest`、`device id/model/os`、`supported actions`、`limitations`、`verification_run_id`、`artifact refs`（`models/capability.py:24-46` 无对应列，迁移也没有）。
- **G15-2** 无「Capability Verification Run」服务/Workflow/API：`mark_verified` 是唯一 VERIFIED 写入者，且唯一生产调用者是脚本 `verify_android_device.py:169`；该脚本伪造 `COMPLETED/PASS` Run（无 Job/NodeRun/断言），属规格 §0.2.8 明令禁止的验收证据。
- **G15-3** 正式 Launch Preflight 使用 `services/preflight.py` 而非 `capability_preflight.py`：允许 AVAILABLE、允许能力名 OR 匹配、平台声明可缺省（`preflight.py:98-110`）；`capability_preflight.py:176` 也接受 AVAILABLE 且无「批准 AVAILABLE 的策略」对象。规格「只接受 VERIFIED」在两条链路上都不成立。
- **G15-4** 自动降级未接线：`invalidate_verification`/`mark_degraded` 无生产调用；设备断连、证书/权限变更、runner image digest 变化均无检测；心跳过期只影响计算结果，不落状态、不产生 Run 事件或告警。
- **G15-5** 对外可观测状态不真实：`platform_matrix.py:26,46` 与 `aiqe_nodes.py:49` 用持久化 `available`/`capability_status`，心跳过期后矩阵/心跳仍显示 available（与 `compute_effective_status` 不一致）。
- **G15-6** 心跳 TTL 三处不一致（180/30/文档 30），且无测试断言具体 TTL（`test_aiqe_capability_heartbeat.py:50-68` 只测 300s 过期）。
- **G15-7** 旧式能力名（`aiqe:*`）与新词表（`browser.*`/`device.*`）并存，Registry 不校验（`capability_registry.py:132-197` 仅校验非空），进一步削弱「真实能力」判定。

### 1.4 已存在测试与入口质量

| 测试 | 覆盖点 | 入口 | 入口质量评估 |
|---|---|---|---|
| `tests/test_aiqe_capability_registry.py:11-110` | register/evidence/select_nodes/validator | helper 直调 | 差：只证明 in-process 函数，不经过 API/Worker/Job |
| `tests/test_aiqe_aud005_capability_preflight.py:31-151` | 6 态、mark_verified 必填平台/evidence、版本降级、心跳过期、REVOKED | helper 直调 | 差：`test_verified_requires_platform_and_evidence` 只证明字符串校验，不证明「验证 Run」 |
| `tests/test_aiqe_aud005_capability_preflight.py:279-319` | Preflight 阻塞不创建空跑 Job（Worker 入口） | `dag_scheduler.schedule(preflight=schedule_guard)` + `job_consumer.run_job` | 中：确实走 Worker/调度，但 HTTP 执行被 monkeypatch（`SafeHttpExecutor.request`），且未验证「AVAILABLE 时也必须 BLOCKED」 |
| `tests/test_aiqe_capability_heartbeat.py:102-156` | 心跳 API 鉴权/404/409/恢复 | 正式 HTTP API | 好（仅心跳契约）；但未断言 TTL 与矩阵降级 |
| `tests/test_aiqe_aud020_platform_bindings.py` | 平台状态区分/不可自报/真机需 VERIFIED | helper 直调 | 差：直接用 `mark_verified` 造 VERIFIED，等于用测试数据证明能力 |
| `tests/test_aiqe_platform_matrix.py:39-61` | 矩阵真实节点聚合 | helper + 只读 API | 中：只读 API 入口；未覆盖心跳过期后降级，反而把 `available=False` 固化 |
| `tests/test_aiqe_run_launch.py:145-149` | Launch 无能力 → BLOCKED | Launch API 入口（需确认测试用 launch_run） | 中：覆盖 `CAPABILITY_UNAVAILABLE`，不覆盖 AVAILABLE→放行 |

**结论**：没有任何一条测试从「正式 Launch → Job → Worker → 能力验证 Run → mark_verified」证明 VERIFIED 由真实运行产生；反而有测试和脚本把「任意 evidence 字符串 → VERIFIED → Preflight READY」固化为契约。

### 1.5 最小整改建议（不含代码补丁）

1. `app/aiqe/models/capability.py` + 新 alembic 迁移：补 `os_version`、`browser_version`、`runner_image_digest`、`device_id/model/os`、`supported_actions_json`、`limitations_json`、`verification_run_id`（FK test_runs）、`verification_artifact_refs_json`、`last_verified_at`（复用 verified_at 但语义改为 Run 时间）。
2. `app/aiqe/services/capability_registry.py`：新增 `record_verification(db, node_id, run_id)`——只接受 `run.status=COMPLETED && run.outcome=PASS` 且存在 required assertions/Artifacts 的 Run；删除/降级 `mark_verified(evidence_ref:str)` 的外部可用性（改为仅测试/迁移内部使用）。
3. 统一 Preflight：删除 `app/aiqe/services/preflight.py` 的能力判定分支，`run_launch.py` 改调 `capability_preflight`；`select_nodes` 的默认允许集改为 `{VERIFIED}`，AVAILABLE 需显式审批对象（新表或 Run policy 中的 `allow_unverified_capabilities` + 审批人/到期）；`_node_has_platform` 只认 `verified_platforms_json`。
4. `platform_matrix.py` / `aiqe_nodes.py`：输出前统一 `compute_effective_status`，并在心跳过期时把状态落库为 DEGRADED/UNAVAILABLE、写 Run/运维事件。
5. 接线自动降级：Runner/DeviceBroker 断连事件 → `mark_degraded`；manifest 的 `runner_image_digest` 变化 → `invalidate_verification`；对每种降级产生可查询事件。
6. **必须新增负向测试** `tests/test_aiqe_v16_015_capability_evidence.py`：
   - 经正式 `POST /api/v1/aiqe/runs`（或 `run_launch.launch_run`）启动 UI 节点：仅 AVAILABLE 节点 → Run BLOCKED（无审批）；VERIFIED 节点 → 放行；断言 `NO_CAPABLE_RUNNER/CAPABILITY_UNAVAILABLE` 事件存在。
   - `mark_verified` 在无 verification Run / Run 非 PASS / Run 无 required assertion 时拒绝（403/ValueError），并断言节点状态不变。
   - 心跳过期后 `GET /api/v1/aiqe/platform-matrix` 显示 UNAVAILABLE（不再 available）。
   - 设备断连事件 → `GET /api/v1/aiqe/platform-matrix` 显示 DEGRADED，新 Run Launch BLOCKED。
   - `driver_version` 不变但 `runner_image_digest` 变化 → VERIFIED 失效。
   - 旧式 `aiqe:playwright` 能力名无法通过 Preflight（或必须显式映射）。

### 1.6 可复核命令

```powershell
$root='F:\CamelTv-worktrees\DeepSeek_Harness-aiqe-v1-6'
Select-String -Path "$root\test-platform-v2\backend\app\aiqe\services\capability_registry.py" -Pattern 'DEFAULT_HEARTBEAT_TTL|SCHEDULABLE_STATUSES|def mark_verified|def invalidate_verification|def mark_degraded'
Select-String -Path "$root\test-platform-v2\backend\app" -Pattern 'mark_verified\(' -Recurse | ForEach-Object { $_.Path.Replace("$root\",'') + ':' + $_.LineNumber }
Select-String -Path "$root\test-platform-v2\backend\app\aiqe\services\preflight.py" -Pattern 'HEARTBEAT_TTL|any\(cap in caps|row.available'
Select-String -Path "$root\test-platform-v2\backend\app\aiqe\services\platform_matrix.py" -Pattern 'row.available'
Select-String -Path "$root\scripts\qa\aiqe_v14_local_dogfood.py" -Pattern 'evidence_ref'
git -C $root log -1 --format='%H %ad %s' --date=iso
```

---

## 2. V16-016 多端适配器能力边界与路线

**状态：PARTIAL**

### 2.1 规格要求 → 实现映射

| 规格要求（§V16-016） | 现状 | 证据 |
|---|---|---|
| Web/Playwright 按 V16-002 完成真实请求拦截与证据采集 | Playwright driver 有真实 actions/screenshot/trace，但拦截层属 V16-002（本组不重复判定）；证据采集存在 | `app/aiqe/drivers/playwright_driver.py:275-394`（动作）、`:505-524`（截图/trace） |
| Android/Appium 验证安装/启动/权限/页面操作/截图/性能/清理的正式执行链 | 只有 `_execute_appium`：session 创建 + source + 可选 click + expect_text；**无安装/权限/截图/性能指标**，清理在 finally | `app/aiqe/services/node_executor.py:601-724`（`:713-717` DELETE session） |
| iOS 未完成时只能 REGISTERED/BLOCKED | DeviceBroker 有 `IOS_ENABLED=False` 门禁；但**能力注册/VERIFIED 完全绕过 DeviceBroker**：可注册 `device.ios` 节点并 `mark_verified`，`preflight_platform` 随后放行 | `app/aiqe/services/device_broker.py:9,44-45,66-67`；`tests/test_aiqe_aud020_platform_bindings.py:109,157-178`（device.ios 节点 + mark_verified → allowed） |
| 小程序：不能把 WebView 测试等同原生；需登录态/页面/网络/前后台/性能/截图 | `MiniAppAdapter` 只接受注入的 `executor(case)` 回调并汇总 5 个硬编码 case；没有任何小程序后端（minium/weapp）实现、无登录态/网络/性能证据 | `app/aiqe/adapters/miniapp.py:43-78`；全仓生产代码 0 引用（只有 `tests/test_aiqe_miniapp_adapter.py`） |
| Desktop/IoT 保持 BLOCKED，不进 GA | `DesktopDriver`/`IotDriver` 同样是注入 executor 的演示类；无 NodeExecutor 注册；`node_executor` 对 desktop/iot 走 `UNSUPPORTED_DRIVER` | `app/aiqe/adapters/desktop_driver.py:31-57`、`app/aiqe/adapters/iot_driver.py:15-31`；`node_executor.py:39,474-515`（DEVICE_DRIVERS 只有 appium/android/mobile） |
| 所有 Driver 通过统一 `DriverProtocol` 和 `NodeExecutor` 注册，不允许只能脚本手跑的平台适配器 | 无 `DriverProtocol` 注册表；adapter 类未被任何生产模块导入；三个适配器均为「测试导入即全部使用者」 | 全仓 grep `MiniappAdapter|DesktopDriver|IotDriver`：仅定义文件 + `tests/test_aiqe_miniapp_adapter.py`、`tests/test_aiqe_desktop_iot_drivers.py` |
| PlatformBinding 记录 Project/Environment/DevicePool/Runner/Capability version | 只有 project_id/target/platform/os/app version/device_model/driver_name/version/node_id/test_profile/evidence/capability_status；**无 environment_id、device_pool_id、runner version/image、capability version** | `app/aiqe/models/platform_binding.py:26-63` |
| 设备租约/并发上限/会话清理/崩溃恢复/健康检查统一进入 DeviceBroker | `DeviceBroker` 是纯内存 dict：allocate 置 busy、release、health 计数；无持久化租约、无并发上限、无崩溃恢复、无进程重启后状态；且**没有任何生产代码使用** | `app/aiqe/services/device_broker.py:34-89`；全仓 `DeviceBroker|device_broker` 在 `app/` 仅定义文件，无 import |
| 每个平台声明动作粒度；未支持动作 Preflight BLOCKED | `workflow_validator` 只校验 driver/capability 名称；Playwright 未支持动作在**运行期**抛 `UNSUPPORTED_ACTION` | `app/aiqe/services/workflow_validator.py:146-159`；`app/aiqe/drivers/playwright_driver.py:275-278` |
| 性能采集定义单位/采样/来源/缺失语义；无采集证据不得指标 PASS | 全仓 `fps/frame_rate/cpu_percent/memory_mb/perf_metrics` 0 命中；无性能断言/指标类型 | grep 结果为空；`ArtifactType`（`models/artifact.py:31-48`）无性能类型 |
| 验收：GA 每平台跑标准 Capability Verification Workflow，验证正式 Job Consumer、设备断开恢复、Artifact 上传、资源清理 | 无标准验证 workflow；Android 验证是 adb 脚本（伪造 Run）；无设备断开恢复测试；无清理断言；Artifact 上传只在脚本里直调 `put_artifact` | `scripts/aiqe/verify_android_device.py:114-171`；`app/aiqe/services/device_broker.py` 无恢复逻辑 |

### 2.2 关键证据（可复核）

1. `app/aiqe/services/platform_binding_service.py:45-47` — `REAL_DEVICE_PLATFORMS={native_android,native_ios,miniapp_wechat,desktop_windows,desktop_macos,hardware_iot}`，`:258-293` 对真机平台要求 VERIFIED；但 `:78-138` 的 `resolve_platform_status` 只看 `capabilities_json` 是否含所需能力，不校验 DeviceBroker/iOS 门禁、不校验设备是否存在。
2. `tests/test_aiqe_aud020_platform_bindings.py:157-178` — 纯 DB 行即可让 `native_ios` 变 VERIFIED 并 `preflight_platform` allowed=True（`mark_verified` 只要求非空 platforms + 非空 evidence 字符串）。
3. `app/aiqe/models/platform_binding.py:26-49` — 缺 `environment_id`/`device_pool_id`/`runner_version`/`runner_image_digest`；与规格「PlatformBinding 记录 Project/Environment/DevicePool/Runner/Capability version」逐项不符。
4. `app/aiqe/services/device_broker.py:9` — `IOS_ENABLED = False`；`:44-45,66-67` 注册/分配拒绝 iOS。该门禁只在内存对象内生效；`capability_registry.mark_verified`（`capability_registry.py:252-278`）无任何 iOS 检查。
5. `app/aiqe/adapters/miniapp.py:52-70` — `MiniappAdapter.run()` 遍历硬编码 `CASES` 调用注入 `executor`；`tests/test_aiqe_miniapp_adapter.py:15-17` 的 executor 恒返回 `{"passed": True}`。这是标准「Mock 替代真实链路」。
6. `app/aiqe/adapters/desktop_driver.py:31-57`、`iot_driver.py:15-31` — 构造器要求外部注入 `executor`/`transport`，没有官方 UIA/AppleScript/MQTT 实现；生产无导入。
7. `app/aiqe/services/node_executor.py:39` — `DEVICE_DRIVERS=frozenset({"appium","android","mobile"})`；`:474-515` 其余 driver 走 `UNSUPPORTED_DRIVER`。desktop/miniapp/iot 的 driver 名称并未进入执行器注册表。
8. `docs/aiqe/evidence/external-runner-e2e.md:3-5` 与 `docs/aiqe/evidence/android-node/capability.json` — Android 证据存在，但来源是 `external_e2e` 调 adb 冒烟 + 手工脚本 `mark_verified`；`README`/证据无「设备断开恢复」「资源清理」「性能指标」记录。

### 2.3 Gaps（可验证）

- **G16-1** 三个平台 Adapter（Miniapp/Desktop/IoT）是死代码，只被测试导入，未接 `DriverProtocol`/`NodeExecutor`，违反「不允许有平台 adapter 只能通过脚本手动运行、却未接标准执行链」。
- **G16-2** PlatformBinding 缺 Environment/DevicePool/Runner image/Capability version 字段（`models/platform_binding.py:26-49`）。
- **G16-3** DeviceBroker 无持久化租约/并发上限/崩溃恢复/健康检查接入，且在 `app/` 中零引用；设备租约未接管（`device_broker.py:34-89`）。
- **G16-4** 无动作粒度声明与 Preflight 校验：`workflow_validator.py:146-159` 只校验名称；`playwright_driver.py:275-278` 在运行期才报 `UNSUPPORTED_ACTION`。
- **G16-5** 性能采集完全缺失（无指标定义、无采集源、无断言类型），规格要求 5 条无对应实现。
- **G16-6** iOS 可仅凭 DB 行 + 任意 evidence 字符串被标 VERIFIED 并通过 `preflight_platform`（测试已固化），违反「未实现只能 REGISTERED/BLOCKED，不得宣称 VERIFIED」。
- **G16-7** 无 GA 平台的 Capability Verification Workflow：Android 验证脚本伪造 `COMPLETED/PASS` Run；无设备断开恢复、无 Artifact 上传正式链、无资源清理断言（`verify_android_device.py:114-171`）。
- **G16-8** 小程序/桌面/IoT 无「不支持清单」产物（规格要求明确列入 GA 不支持清单）——仓库内无 GA 支持矩阵文档；`docs/aiqe/evidence` 也没有对应声明。

### 2.4 已存在测试与入口质量

| 测试 | 覆盖点 | 入口 | 入口质量评估 |
|---|---|---|---|
| `tests/test_aiqe_device_broker.py:24-64` | allocate/release/能力过滤/iOS 门禁/health | 内存对象 | 差：只测内存 dict，不涉及 DB/租约/崩溃恢复 |
| `tests/test_aiqe_miniapp_adapter.py:19-43` | 版本矩阵/后端选择/5 case 汇总 | 注入 fake executor | 差：用 `executor` 恒返回 passed，等于用 Mock 证明「小程序可用」 |
| `tests/test_aiqe_desktop_iot_drivers.py:28-64` | Desktop 动作序列、IoT 只读边界 | 注入 fake executor | 差：纯单元，无官方 UIA/MQTT 实现 |
| `tests/test_aiqe_ui_device_executor.py:64-154` | playwright 分发、Appium session/click/expect_text/失败分支 | helper 直调 + monkeypatch `_execute_playwright`/`httpx.Client` | 差-中：Appium 用 fake HTTP client；playwright 分发被 monkeypatch 掉，未证明真实浏览器 |
| `tests/test_aiqe_aud020_platform_bindings.py:89-205` | 平台状态、不可自报、真机需 VERIFIED、矩阵不隐藏未验证 | helper 直调 | 中：服务层正确性；但用 `mark_verified` 造 VERIFIED，暴露 G16-6 |
| `tests/test_aiqe_external_node_report.py:86-107` | 外部 Runner 回报成功 → Run PASS | `job_consumer.complete_from_report` 正式回写入口 | 中：走正式回写；但**零断言、零 Artifact 即 PASS**，暴露 018/009 缺口 |
| `tests/e2e/aiqe/test_tc_aiqe_001_010.py:21` | 十个 TC | 需 `AIQE_E2E_BASE_URL`，否则整文件 skip | 差：CI 不设变量 → 全 skip；不计通过但也没有 BLOCKED 报告 |

### 2.5 最小整改建议

1. 新增统一 Driver 注册（`DriverProtocol` + `NODE_DRIVERS`），把 miniapp/desktop/iot 以「显式 UNSUPPORTED」注册，Preflight 直接 BLOCKED 并输出 platform + 原因；删除或迁出只被测试使用的 Adapter 演示类。
2. `app/aiqe/models/platform_binding.py` + 迁移：补 `environment_id`、`device_pool_id`、`runner_version`、`runner_image_digest`、`capability_hash`；`create_binding` 校验 Environment 属于 project（复用 `preflight._check_production` 语义）。
3. `app/aiqe/services/device_broker.py`：改为 DB 持久化设备/租约（device table + lease_owner/lease_expires_at/attempt），接入 claim/release/reconciler 清理；`IOS_ENABLED` 检查下沉到 `capability_registry`/`platform_binding_service`，禁止 `device.ios` 注册/VERIFIED。
4. `workflow_validator.py`：按 `supported_actions_json` 校验每个 driver 的 action；Preflight 阶段对未支持 action 直接 BLOCKED。
5. 性能采集：定义 `performance_metrics` 契约（unit/sampling/source/missing semantics）或显式标记 NOT_SUPPORTED 并禁止性能断言 PASS；没有采集证据时断言必须 BLOCKED。
6. **必须新增负向测试** `tests/test_aiqe_v16_016_platform_boundaries.py`：
   - Preflight 对 miniapp/desktop/iot 节点返回 BLOCKED + 原因（不进入执行）。
   - 未支持 action（如 playwright `drag`）在 Preflight 即 BLOCKED，不产生 Job。
   - `IOS_ENABLED=False` 时注册 `device.ios` capability 与 `mark_verified` 均被拒绝；`preflight_platform(["native_ios"])` 返回 PLATFORM_NOT_VERIFIED/PLATFORM_UNAVAILABLE。
   - 设备断连（模拟 device offline/心跳过期）→ 平台 DEGRADED，新 Run BLOCKED；重启后恢复需重新验证。
   - Android 通过正式 claim→payload→report 执行一次并断言存在截图/UI Artifact 与 session DELETE（资源清理）。
   - DeviceBroker 并发：第二个 allocate 必须等待/拒绝，崩溃后租约过期可回收。

### 2.6 可复核命令

```powershell
$root='F:\CamelTv-worktrees\DeepSeek_Harness-aiqe-v1-6'
Select-String -Path "$root\test-platform-v2\backend\app" -Pattern 'MiniappAdapter|DesktopDriver|IotDriver' -Recurse | ForEach-Object { $_.Path.Replace("$root\",'') + ':' + $_.LineNumber }
Select-String -Path "$root\test-platform-v2\backend\app" -Pattern 'DeviceBroker|device_broker' -Recurse | ForEach-Object { $_.Path.Replace("$root\",'') + ':' + $_.LineNumber }
Select-String -Path "$root\test-platform-v2\backend\app\aiqe\models\platform_binding.py" -Pattern 'environment_id|device_pool|runner_version|runner_image'
Select-String -Path "$root\test-platform-v2\backend\app\aiqe\services\workflow_validator.py" -Pattern 'action|driver|capability'
Select-String -Path "$root\test-platform-v2\backend\app\aiqe" -Pattern 'fps|cpu_percent|memory_mb|perf_metrics' -Recurse
```

---

## 3. V16-018 Artifact 安全、完整性与 Evidence Lifecycle

**状态：PARTIAL**

### 3.1 规格要求 → 实现映射

| 规格要求（§V16-018） | 现状 | 证据 |
|---|---|---|
| Artifact 绑定 project_id/run_id/node_run_id/attempt_id/type/content_type/size/sha256/storage_key/created_by/retention_policy/classification | 有 project_id/run_id/node_run_id/step_attempt_id/artifact_type/mime_type/size_bytes/sha256/storage_uri/retention_until/access_scope；**缺 created_by、retention_policy（只有到期时间）**；classification 仅为 `access_scope` 字符串且从不校验 | `app/aiqe/models/artifact.py:58-104`；迁移 `alembic/versions/20261124_aud008_artifact_lifecycle.py:16-53` |
| initiate → signed upload → finalize；finalize 校验对象存在/大小/hash/Content-Type/ownership | initiate 返回的只是「登录态可 PUT 的 API 路径」+ `expires_at`，无签名/token；`complete_upload` 只校验状态/空内容/最大 100MB/（可选）expected_sha256，**不校验 Content-Type、不校验期望大小、不校验收到的对象存在（直接落盘）**；`expires_at` 无任何服务端校验 | `app/aiqe/services/artifact_service.py:98-156`（`:148-155` target 无签名）、`:159-203`（`:170-179` 状态/大小、`:181-194` hash、`:196-203` 落盘）；`app/api/v1/aiqe_artifacts.py:106-128`（PUT 即 finalize） |
| 下载短时授权 URL 或代理鉴权；过期/撤销/跨项目拒绝 | 无短时 URL；走登录态代理下载 + `Cache-Control: private, max-age=300`；跨项目拒绝已实现；**URL/会话过期无法拒绝（无过期概念）** | `aiqe_artifacts.py:146-167`；`artifact_service.py:206-231`（只校验状态/项目） |
| Artifact metadata 不得含 Secret；文本/JSON/HAR/Trace/截图/视频上传前脱敏 | Worker 采集路径（`persist_execution_evidence`）会脱敏文本 + 对二进制做 `scan_bytes`；**公共上传 API 完全不做脱敏/扫描**，metadata 原样落库 | `app/aiqe/services/execution_service.py:216-292`；`artifact_service.py:282-328`（put_artifact 无 redact/scan）；`aiqe_artifacts.py:34-43,78-103`（metadata 直接入库） |
| Evidence ref 采用不可变 ID + checksum；tombstone 后引用返回明确 unavailable | ref = `artifact:<uuid>`（ID 不可变），checksum 仅在 resolver metadata 里回显；**resolver 不校验 upload_status**，PURGED/CORRUPTED 仍返回成功 | `app/aiqe/services/evidence_service.py:79-101`（`:94-100` 只读 metadata） |
| 对缺失/中断/hash 不一致/存储不可用建 reconciliation；Run 不得以 required evidence missing 状态 PASS | 只有 `incompleteness_reasons`（PENDING/CORRUPTED → Run INCOMPLETE）；无定时 reconciliation（`verify_integrity` 仅测试调用）；**零 Artifact 的 Run 仍可 PASS** | `artifact_service.py:261-279`；`dag_scheduler.py:196-228`；`execution_service.py:867-976`（`:931-951` 外部回报 `execution.evidence=[]`）；测试 `tests/test_aiqe_external_node_report.py:86-107` 证明 PASS 且无 Artifact |
| 访问审计；敏感 Artifact 额外权限/水印/审计 | 无任何 artifact 访问审计表/事件；`access_scope` 无权限语义；无敏感分级下载门禁 | 全仓 `artifact.*audit|access_log` 0 命中；`access_scope` 仅在模型/序列化出现（`artifact.py:90`、`aiqe_artifacts.py:72`） |

### 3.2 关键证据（可复核）

1. `app/aiqe/models/artifact.py:61-96` — 无 `created_by`、无 `retention_policy`、无 `classification`（只有 `access_scope`）；`:90` `access_scope` 在 `app/` 中除写库/序列化外无读取点（grep 仅 `artifact_service.py:111,143` 与 `aiqe_artifacts.py:72`）。
2. `app/aiqe/services/artifact_service.py:148-155` — 上传目标 `{artifact_id, upload_url, method, content_type, expires_at, max_bytes}`；无签名字段；`:153` 的 `expires_at` 全仓无校验点（grep `expires_at` 在 artifact 代码仅此处 + GC/测试）。
3. `artifact_service.py:159-203` — `complete_upload` 未读取 `row.mime_type` 做一致性校验，也未比对 `expected_size_bytes`（只把实际长度写回 `:200`）；`expected_sha256` 为可选（`create_pending_artifact:107` 默认 None）→ 无 hash 期望时任意内容直接 AVAILABLE。
4. `app/api/v1/aiqe_artifacts.py:106-128` — 上传接口 `content = await request.body()` 后直接 `complete_upload`；无 Secret 扫描/脱敏；`metadata` 在 create 时原样保存（`:43,95`）。对比 `execution_service.py:268-279`（worker 路径扫描并在命中时 `artifact.rejected` 且不落库），公共路径缺失同等强度。
5. `app/aiqe/services/evidence_service.py:79-101` — `artifact:<id>` 解析只校验「存在 + 同 Project + 同 Run」；`upload_status` 仅作为 metadata 回显（`:96`）。PURGED/CORRUPTED 的 artifact 仍会被 A4/Defect Draft 当作有效证据。
6. `app/aiqe/services/dag_scheduler.py:207-214` — 仅在 `incompleteness_reasons` 非空时把 PASS 降为 INCOMPLETE；`incompleteness_reasons`（`artifact_service.py:261-279`）只含 PENDING_UPLOAD/CORRUPTED，**不含 FAILED**，也不检查「required evidence 数量为 0」。
7. `app/aiqe/services/execution_service.py:931-951` — 外部 Runner 上报时构造 `NodeExecution(evidence=[])`，`persist_execution_evidence`（`:342-352`）只从 `execution.evidence` 生成截图/Trace Artifact；因此 Playwright/Appium 的 screenshot/trace/HAR 不会成为 RunArtifact（只进 `/execution-jobs/{id}/evidence` 文件包，且 `job_consumer` 无 artifact 写入）。
8. `app/aiqe/services/artifact_gc.py:28-37` — GC 用 `created_at < now-retention_days`，**忽略每行 `retention_until`**；`app/api/v1/aiqe_admin.py:286-293` 的 GC 接口按全局（不限 project）清理，仅要求 `menu:aiqe_runs` + `defect:update`，任意项目用户可触发他项目墓碑。
9. `tests/test_aiqe_p0_ops.py:44-109` 与 `tests/test_aiqe_aud008_artifact_lifecycle.py:190-208` — GC 测试全部直接构造 `RunArtifact(created_at=...)`，未覆盖 `retention_until` 或跨项目，反过来把「忽略 retention_until」固化为通过。

### 3.3 Gaps（可验证）

- **G18-1** 模型缺 `created_by`、`retention_policy`；`classification`/`access_scope` 无任何访问控制语义（`models/artifact.py:61-96`）。
- **G18-2** 上传会话无签名/无到期强制（`artifact_service.py:148-155`；`aiqe_artifacts.py:106-128`），不符合 initiate→signed upload→finalize。
- **G18-3** finalize 不校验 Content-Type、不校验 expected size、不重新 HEAD/读取对象存在性；`expected_sha256` 可省略（同上）。
- **G18-4** 上传 API 不脱敏/不扫描 Secret，metadata 可原样携带敏感值（`aiqe_artifacts.py:34-43,78-128`），与 worker 路径（`execution_service.py:216-292`）安全强度不一致。
- **G18-5** Evidence Resolver 接受 PURGED/CORRUPTED/PENDING artifact（`evidence_service.py:79-101`），违反「tombstone 后引用返回明确 unavailable」。
- **G18-6** 无 required-evidence 声明与校验：零 Artifact / 只有 FAILED Artifact 的 Run 可 PASS（`dag_scheduler.py:207-214`、`artifact_service.py:261-279`、`tests/test_aiqe_external_node_report.py:86-107`）。
- **G18-7** 外部 Runner 的截图/Trace 不落 `run_artifacts`（`execution_service.py:931-951`），Run 的 evidence 实际不可通过 `artifact:` ref 读取（与 `docs/aiqe/evidence/external-runner-e2e.md:17-21` 的「Artifacts」声明不一致，需核查其来源）。
- **G18-8** 无 artifact reconciliation：`verify_integrity` 无生产调用；对象缺失/存储不可用只能等人工 GC。
- **G18-9** GC 忽略 `retention_until` 且跨项目全局执行（`artifact_gc.py:28-37`、`aiqe_admin.py:286-293`），存在越权删除/提前删除风险。
- **G18-10** 无访问审计、无敏感 Artifact 额外权限/水印（全仓无访问日志）。

### 3.4 已存在测试与入口质量

| 测试 | 覆盖点 | 入口 | 入口质量评估 |
|---|---|---|---|
| `tests/test_aiqe_aud008_artifact_lifecycle.py:69-103` | 两阶段上传、未完成下载拒绝、hash 必填场景 | `create_pending_artifact`/`complete_upload`/`open_download` helper | 中：核心逻辑正确，但不是 API 入口 |
| 同文件 `:105-145` | hash 不匹配→CORRUPTED、空/超大→FAILED、重复上传拒绝 | helper | 中 |
| 同文件 `:148-167` | 跨项目 get/download/upload 拒绝 | helper | 中 |
| 同文件 `:171-186` | 存储被篡改→verify_integrity 标 CORRUPTED | helper | 中 |
| 同文件 `:190-208` | 过期清理墓碑 + 下载拒绝 | helper | 中；未覆盖 retention_until/项目隔离 |
| 同文件 `:219-250` | Run 证据未完成→INCOMPLETE / 完成→PASS | `dag_scheduler` + `complete_node`（状态机入口） | 中：状态入口，但 Artifact 由 helper 造 |
| 同文件 `:254-317` | POST/PUT/GET/download/403/404/RBAC | **正式 HTTP API** | 好：本 Issue 唯一 API 级链路；但只覆盖 happy path + 跨项目，不覆盖过期/类型/脱敏/墓碑引用 |
| `tests/test_aiqe_artifact_service.py:28-136` | put/read/去重/跨项目/类型/脱敏迁移/路径穿越 | helper | 差：全部 service 直调 |
| `tests/test_aiqe_p0_ops.py:44-109` | GC 墓碑/保留最近/存储失败保留 | helper（直接造行） | 差：把错误 GC 语义固化 |
| `tests/test_aiqe_artifact_minio.py:101-110` | MinIO put/read（本地 HTTP stub?） | helper | 差-中：非真实 MinIO，storage 用 stub |
| `tests/test_aiqe_tenant_scope.py:50-56` | put_artifact + project scope | helper | 差 |

**结论**：没有一条测试覆盖「上传会话过期」「Content-Type 不符」「metadata/内容含 Secret 被拒」「tombstone artifact 作为 Agent evidence 被拒」「外部 Runner UI 证据落 RunArtifact」「跨项目 GC 拒绝」；这些正是规格验收的负向项。

### 3.5 最小整改建议

1. `models/artifact.py` + 迁移：加 `created_by`、`retention_policy`、`classification`（或用 `access_scope` 实现分类语义）、`upload_token_hash`、`finalized_at`；`project_id` 改为非空（迁移已回填）。
2. `artifact_service.create_pending_artifact`：生成一次性上传 token（hash 存库）+ 服务端强制 `expires_at`；`complete_upload` 校验 token、`expires_at`、`Content-Type` 允许集、`expected_size_bytes`、`expected_sha256`，并在 finalize 前 `HEAD`/读取对象比对（大小+hash）。
3. `api/v1/aiqe_artifacts.upload_artifact_api`：复用 `evidence_redactor.scan_bytes/redact_json_text` 对内容与 metadata 扫描；命中即 4xx 且不落存储；设置 `redaction_status`（不再一律 pending）。
4. `evidence_service._resolve_one("artifact")`：`upload_status != AVAILABLE` → `EvidenceRefError(..., "EVIDENCE_UNAVAILABLE")`；ref 增加 checksum（如 `artifact:<id>#sha256:<hex>`）并在解析时校验。
5. `execution_service.complete_from_external_report`：把 Runner 上报的 evidence files（screenshot/trace/HAR）经 `EvidenceFile` → `put_artifact` 落 RunArtifact；或在 `report` API 增加 artifact manifest 并在缺失 required evidence 时把 Run 收口为 INCOMPLETE。
6. `artifact_gc.purge_expired_artifacts`：按 `retention_until <= now` 清理，强制 `project_id`/`project_scope`；`api/v1/aiqe_admin` 的 GC 接口按当前项目清理，全局清理需新权限 + 审计事件。
7. `reconciler`：新增 artifact reconciliation（对象缺失→CORRUPTED/UNKNOWN 并发事件）；`finalize` 增加 required evidence 清单校验（P0/P1 平台/驱动类型映射），缺失禁止 PASS。
8. **必须新增负向测试** `tests/test_aiqe_v16_018_artifact_security.py`：
   - 过期上传 token / 过期会话 → 400/403，且无对象落盘。
   - Content-Type 与声明不符 / 期望大小不符 → 拒绝且状态 FAILED。
   - metadata 或 HAR 内容含 canary secret → 4xx 且对象不存在、metadata 无明文。
   - PURGED/CORRUPTED artifact 作为 `artifact:<id>` evidence → `EvidenceRefError`（A4/Defect Draft API 入口）。
   - 跨项目调用 `POST /api/v1/aiqe/admin/artifacts/gc` → 403；`retention_until` 未到的 Artifact 不被清理。
   - 外部 Runner 上报 PASS 但无 required evidence → Run INCOMPLETE/BLOCKED（正式 report 入口）。
   - 对象被删除后 reconciliation 标 CORRUPTED 且新 Run 不可 PASS。
   - 下载成功后存在访问审计记录（若实现审计表）。

### 3.6 可复核命令

```powershell
$root='F:\CamelTv-worktrees\DeepSeek_Harness-aiqe-v1-6'
Select-String -Path "$root\test-platform-v2\backend\app\aiqe\models\artifact.py" -Pattern 'created_by|retention_policy|access_scope|classification'
Select-String -Path "$root\test-platform-v2\backend\app\aiqe\services\artifact_service.py" -Pattern 'expires_at|mime_type|expected_size|expected_sha256|upload_status'
Select-String -Path "$root\test-platform-v2\backend\app\aiqe\services\artifact_gc.py" -Pattern 'created_at|retention_until|project_id'
Select-String -Path "$root\test-platform-v2\backend\app\aiqe\services\evidence_service.py" -Pattern 'upload_status|artifact' -Context 1,2
Select-String -Path "$root\test-platform-v2\backend\app\aiqe\services\execution_service.py" -Pattern 'evidence=\[\]|persist_execution_evidence'
Select-String -Path "$root\test-platform-v2\backend\app\api\v1\aiqe_artifacts.py" -Pattern 'expires_at|content = await|metadata'
Select-String -Path "$root\test-platform-v2\backend\tests" -Pattern 'expires_at|upload_status' -Include 'test_aiqe_*artifact*.py','test_aiqe_aud008*.py','test_aiqe_p0_ops.py'
```

---

## 4. V16-021 删除 Dogfood 默认弱口令

**状态：MISSING**

### 4.1 证据

1. `test-platform-v2/backend/scripts/aiqe/evidence_local_20.py:203` —
   `parser.add_argument("--password", default=os.environ.get("AIQE_EVIDENCE_PASSWORD", "<weak-default>"))`
   → 弱默认口令仍在；未提供任何凭据时脚本**不会退出**，而是用弱默认值直接跑（`:227` 传入 `execute_run`）。
2. `test-platform-v2/backend/scripts/aiqe/evidence_local_20.py:10` — 模块 docstring 仍写 `--runs 20 --password <weak-default>`，等于继续教用户使用默认口令。
3. 同文件 `:153-156` — `secrets={"ADMIN_PASSWORD": password}` 把明文密码放进 RunContext；`:266` 仅断言「密码未进入 environment_snapshot」，不覆盖 outputs/attempts/jobs/artifacts（且 `assert` 在 `-O` 下失效）。
4. `scripts/aiqe/run_dogfood_mixed.py:29,48` — 管理员密码通过 `--admin-password` 命令行参数传入（进程列表可读），违反「禁止将密码写入命令行参数」。
5. `scripts/qa/aiqe_local_runner.py:12,328,344-352` — `--password` 参数（默认空串），缺凭据时只报错退出（这一点优于 021，但仍是命令行口令）。
6. `app/aiqe/services/dogfood.py:55-69` — `DogfoodConfig.validate()` 只要求 `admin_url + admin_username`（`:62-63`），**不要求 admin_password**；未注入凭据时不会 fail-fast，而是跑到登录节点失败。
7. 全仓 grep `evidence_local_20|evidence_camel_test5|verify_android_device|run_dogfood_mixed` 在 `tests/` 命中 **0** → 无「无凭据退出非 0」「不打印密码」的脚本测试。
8. 历史凭据扫描/轮换：`docs/aiqe/` 下无任何 admin123 扫描报告或轮换记录；`git grep admin123` 仍有 `test-platform-v2/backend/tests/{quick_test,qa_verification,proxy_debug,...}.py`、`tests/conftest.py:104` 等（测试夹具弱口令虽非本脚本，但「历史凭据扫描并轮换」无产物）。

### 4.2 Gaps（可验证）

- **G21-1** `evidence_local_20.py:203` 弱默认值未删除（规格第 1 条）。
- **G21-2** 未提供凭据时无「直接退出并给非敏感错误」（规格第 2 条）；脚本可无凭据启动。
- **G21-3** 仍支持 `--password` 命令行参数（`evidence_local_20.py:203`、`run_dogfood_mixed.py:29`、`aiqe_local_runner.py:328`），规格第 3 条禁止。
- **G21-4** 无「无凭据退出码非 0」与「日志不打印密码」的测试（规格测试要求）。
- **G21-5** 无历史 evidence 文件扫描与凭据轮换记录（规格第 4 条）。

### 4.3 已存在测试与入口质量

无。`tests/` 中没有针对 `scripts/aiqe/*` 的任何测试；`run_dogfood.ps1` 只跑 AIQE 单测分组，不覆盖脚本凭据行为。

### 4.4 最小整改建议

1. `test-platform-v2/backend/scripts/aiqe/evidence_local_20.py`：删除 `admin123` 默认；改为必须从 `AIQE_EVIDENCE_PASSWORD` 或 `AIQE_SECRET_HANDLE`（handle 经 `resolve_secret_handle`）读取；两者皆无 → `print(..., file=sys.stderr)` 非敏感提示 + `return 2`；删除 `--password` 参数与 docstring 示例；确保日志/异常不打印密码。
2. `scripts/aiqe/run_dogfood_mixed.py` 与 `scripts/qa/aiqe_local_runner.py`：密码只从环境/secret 文件/stdin 读取，删除 `--admin-password`/`--password` 参数（保留 `--username`）。
3. `app/aiqe/services/dogfood.py:55-69`：`include_admin_ui` 时同时要求 `admin_password` 或 handle，否则 `DogfoodConfigError`；CLI 返回非 0。
4. 新增历史扫描脚本（如 `scripts/aiqe/scan_default_credentials.py`），扫描 `docs/aiqe/evidence/**` 与 `work-logs/**` 中 `admin123`/默认口令并输出待轮换清单。
5. **必须新增负向测试** `tests/test_aiqe_v16_021_script_credentials.py`（subprocess 调用真实脚本入口）：
   - 清空 `AIQE_EVIDENCE_PASSWORD` → 退出码非 0，stderr 不含 `admin123`、不含任何口令模式。
   - `--password xxx` → 参数被拒绝（argparse 非 0）或忽略并 still fail-closed。
   - 设置 `AIQE_EVIDENCE_PASSWORD`（指向本地 fake 服务）→ 正常执行且 stdout/stderr/生成 JSON 中无明文。
   - 对 `scripts/aiqe/**` 做文本断言：不存在 `admin123` 默认值与 `--password` 定义。

### 4.5 可复核命令

```powershell
$root='F:\CamelTv-worktrees\DeepSeek_Harness-aiqe-v1-6'
Select-String -Path "$root\test-platform-v2\backend\scripts\aiqe\evidence_local_20.py" -Pattern 'admin123|--password|AIQE_EVIDENCE_PASSWORD'
Select-String -Path "$root\scripts\aiqe\run_dogfood_mixed.py","$root\scripts\qa\aiqe_local_runner.py" -Pattern 'password'
Select-String -Path "$root\test-platform-v2\backend\app\aiqe\services\dogfood.py" -Pattern 'admin_password|validate'
Select-String -Path "$root\test-platform-v2\backend\tests" -Pattern 'evidence_local_20|run_dogfood_mixed|verify_android_device'
```

---

## 5. V16-022 依赖和测试环境可复现

**状态：PARTIAL**

### 5.1 规格要求 → 实现映射

| 规格要求（§V16-022） | 现状 | 证据 |
|---|---|---|
| 1. 明确 Python/Node/系统依赖/浏览器版本 | `docs/aiqe/ops.md:9-10` 写 Python 3.12+/Node 20+；CI 用 Python 3.12、Node 22.22；Playwright `==1.61.0` 在 requirements；系统依赖（adb/Appium/微信工具）散落在 `runner-deployment.md:68-74`，无单一版本清单 | `docs/aiqe/ops.md:9-16`；`.github/workflows/main-quality-gate.yml:93-99,220-226`；`requirements.txt:27` |
| 2. bcrypt 等依赖声明在正确 dependency group，锁定版本和 hash | `requirements.txt:16 bcrypt>=4.1`；三份 lock 中 `bcrypt==5.0.0` 带 hash（pip-compile --generate-hashes）；但**没有 dependency group**（pyproject 无 `[project]`/`[dependency-groups]`），pytest 未在运行时清单声明（仅经 pytest-cov 传递），测试工具链未锁 | `requirements.txt:16`；`requirements.lock:49`；`requirements.api.lock:63`；`requirements.runner.lock:63`；`pyproject.toml` 全 44 行仅 ruff/mypy |
| 3. 单一命令构建干净测试环境；CI 用 lockfile 安装 | 无单一命令脚本；required CI 用 `pip install -r requirements.txt` + `pip install pytest`（浮动）后跑全量；lock 只做 `--dry-run --require-hashes` 解析校验（`main-quality-gate.yml:136-140`）；仅 `pr-check.yml:129-133` 的 PG 作业用 lock 安装 | `main-quality-gate.yml:101-106,128-140,181-187`；`pr-check.yml:127-133` |
| 4. 测试分层：unit/service/api/worker/browser/device | `pytest.ini` 只有 `slow`/`integration` 两个 marker；AIQE 测试平铺在 `tests/test_aiqe_*.py`（88 个文件）；`tests/e2e/aiqe/*` 未被 marker 区分，唯一被收集的 `test_tc_aiqe_001_010.py:21` 用 `skipif(not AIQE_E2E_BASE_URL)`，CI 不设 → 全 skip | `pytest.ini:1-8`；`tests/e2e/aiqe/test_tc_aiqe_001_010.py:15-21` |
| 5. CI 输出 JUnit XML/coverage XML/Playwright Trace/Artifact/commit SHA | required 后端作业不产出 JUnit/XML/Trace；`pr-check`（非阻塞）只上传 `coverage.json`；全仓 workflow grep `junit` 仅 api-regression/prod-smoke 的 API 测试；无 commit SHA 写入报告 | `main-quality-gate.yml:181-187`；`pr-check.yml:78-92`；grep workflow `junit|commit_sha` 结果 |
| 6. 失败日志保留，不得把依赖安装失败算通过 | Actions 默认日志保留；无失败用例日志/报告 artifact；依赖安装失败会让 job 失败（OK） | 同 workflow 无 `if: failure()` 上传步骤 |
| 7. 本地复现脚本和容器镜像 digest | `docs/aiqe/ops.md` 有启动步骤但 `pip install -r requirements.txt`（非 lock）；`docs/aiqe/runner-deployment.md:70` 同；Dockerfile 以 `python:3.12-slim@sha256:...` 固定 base 并用 `--require-hashes -r requirements.api.lock`；但**没有记录生成镜像的 digest** 到任何证据/文档 | `docs/aiqe/ops.md:18`；`runner-deployment.md:68-74`；`Dockerfile:2,7-8,16-17`（正向） |

### 5.2 关键证据（可复核）

1. `test-platform-v2/backend/requirements.txt:16` — `bcrypt>=4.1`（V1.5 审计的 `conftest` 缺 bcrypt 问题在依赖层已有声明）；`requirements.lock:49` — `bcrypt==5.0.0 \` 带 hash，说明锁文件确实存在。
2. `requirements-quality.txt:1-4` — 只锁 `mypy/pip-audit/ruff`，**不含 pytest**；CI 用 `pip install pytest -r requirements-quality.txt`（`main-quality-gate.yml:106`）→ pytest 版本浮动。
3. `.github/workflows/main-quality-gate.yml:101-106` — 测试安装源是 `requirements.txt`；`:128-140` 只对 `requirements.api.lock`/`requirements.runner.lock` 做 dry-run；`:181-187` 全量 pytest 无 `--junitxml`、无 coverage、无报告上传。
4. `.github/workflows/pr-check.yml:78-92` — 唯一带 coverage 的运行，输出 `coverage.json` 并上传 artifact `backend-coverage`；仍是 `pip install -r requirements.txt`（`:65-69`），且是每日非阻塞观察。
5. `test-platform-v2/backend/pyproject.toml:1-44` — 无 `[project]`、无依赖组；只有 ruff/mypy/ruff-format 配置。规格第 2 条「正确 dependency group」不成立。
6. `pytest.ini:5-8` — `markers = slow / integration`，没有 unit/service/api/worker/browser/device 层级；`tests/e2e/aiqe/test_tc_aiqe_001_010.py:21` 依赖 `AIQE_E2E_BASE_URL`，CI 未设置 → skip。
7. 全仓 `.github/workflows/*.yml` grep `aiqe|AIQE` = **0 命中**：没有任何 AIQE 专项 CI/报告/证据作业。
8. `Dockerfile:2,7-8,16-17` — 正向项：`python:3.12-slim@sha256:57cd...`、`pip install --require-hashes -r requirements.runner.lock` / `requirements.api.lock`。但镜像 digest 未写入 `config/aiqe-version.lock`（见 V16-023）。

### 5.3 Gaps（可验证）

- **G22-1** 测试环境未从 lock 安装：required CI 用 `requirements.txt` + 浮动 `pytest`（`main-quality-gate.yml:101-106`），依赖漂移不可复现。
- **G22-2** 无 dependency groups：`pyproject.toml` 无 `[project]`/`[dependency-groups]`，runtime/test/browser/device 依赖混在一个平表（`requirements.txt`）。
- **G22-3** pytest 不在任何锁定清单的显式依赖中（`requirements-quality.txt:1-4` 无 pytest），测试工具链版本不可复现。
- **G22-4** 无分层 marker/作业：`pytest.ini:5-8` 仅 slow/integration；无 unit/service/api/worker/browser/device 分层与对应 CI job。
- **G22-5** CI 无 AIQE 的 JUnit XML、coverage XML、Playwright Trace、测试 Artifact、commit SHA（`main-quality-gate.yml:181-187`、`pr-check.yml:78-92`）。
- **G22-6** 无单一命令干净环境脚本；文档仍指导 `pip install -r requirements.txt`（`docs/aiqe/ops.md:18`、`runner-deployment.md:70`）。
- **G22-7** e2e AIQE 测试在 CI 恒 skip（`test_tc_aiqe_001_010.py:21`），且「skip 不计通过也没有 BLOCKED 报告」。
- **G22-8** 容器镜像 digest 未记录、未与版本锁绑定（`config/aiqe-version.lock` 只有 image_tag）。
- **G22-9** Node 版本文档与 CI 不一致（`ops.md:10` Node 20+ vs CI `node-version: 22.22`；`main-quality-gate.yml:224`）。

### 5.4 已存在测试与入口质量

本 Issue 不是功能测试题；现有「可复现性」资产只有：三份 hash lock、Dockerfile 多阶段 lock 安装、`quality_ratchet.py`、`scripts/aiqe/run_dogfood.ps1`（按 M1–P0 分组跑单测并写 md，`:44-46` 只有日期/命令/结果，无 commit SHA/环境/digest）。这不是「干净容器按文档一次性安装并跑完规定测试集」的验收证据。

### 5.5 最小整改建议

1. 在 `pyproject.toml` 增加 `[project]` + `[dependency-groups]`（runtime / test / browser / device），或至少拆分 `requirements-test.txt` 并由 `pip-compile --generate-hashes` 生成 `requirements.test.lock`；把 pytest/pytest-cov 显式锁入 test lock。
2. `main-quality-gate.yml`：测试作业改为 `pip install --require-hashes -r requirements.test.lock`（或 api.lock + test.lock），禁止直接 `requirements.txt`；`--junitxml=artifacts/aiqe-junit.xml`、`--cov-report=xml`，`upload-artifact` 上传报告与失败日志；在报告中写 `${{ github.sha }}`、环境、镜像 tag。
3. `pytest.ini`：增加 `unit/service/api/worker/browser/device/e2e` marker 并给现有 AIQE 测试打标；CI 增加分段 job；e2e 缺环境时报告 `BLOCKED`（由报告生成器识别），不得 skip 当通过。
4. 新增 `scripts/aiqe/setup_test_env.ps1`（或 Makefile）：一条命令创建 venv、按 lock 安装、安装 Chromium、跑规定测试集并输出 JUnit/Coverage/Trace/commit SHA。
5. 镜像 digest 写入 `config/aiqe-version.lock`，并在 `docs/aiqe/runner-deployment.md` 记录本版本 runner/api 镜像 digest。
6. **必须新增负向/门禁测试** `tests/ci/test_v16_022_reproducible_env.py`（或 CI 脚本）：
   - lock 安装命中即断言 `pip install --require-hashes -r <lock>` 成功；
   - 断言 pytest 存在于 test lock（缺失则 fail）；
   - 断言 CI 报告文件包含 commit SHA/环境/镜像 digest；
   - 断言 AIQE e2e 未设置环境时输出 BLOCKED 而不是 skip 当 PASS。

### 5.6 可复核命令

```powershell
$root='F:\CamelTv-worktrees\DeepSeek_Harness-aiqe-v1-6'
Select-String -Path "$root\test-platform-v2\backend\requirements.txt","$root\test-platform-v2\backend\requirements-quality.txt" -Pattern 'bcrypt|pytest'
Select-String -Path "$root\test-platform-v2\backend\requirements.lock" -Pattern 'bcrypt==|pytest==|pytest-cov=='
Select-String -Path "$root\.github\workflows\main-quality-gate.yml" -Pattern 'pip install|pytest|junit|cov-report|upload-artifact'
Select-String -Path "$root\.github\workflows\pr-check.yml" -Pattern 'require-hashes|coverage.json|pytest tests'
Select-String -Path "$root\test-platform-v2\backend\pyproject.toml" -Pattern '\[project\]|dependency-groups'
Select-String -Path "$root\.github\workflows\*.yml" -Pattern 'aiqe|AIQE'
```

---

## 6. V16-023 证据和版本追溯

**状态：MISSING**

### 6.1 证据

1. **证据文件缺 commit/CI/PR/镜像**：
   - `docs/aiqe/evidence/local-dogfood-20.json:1-5` 只有 `generated_at/base_url/runs`；`local-dogfood-20.md:1-6` 只有生成时间/目标/digest（records 摘要），无 commit SHA、CI run、PR、镜像 digest。
   - `docs/aiqe/evidence/camel-test5-20.json:1-5`、`camel-test5-20.md` 同。
   - `docs/aiqe/evidence/external-runner-e2e.md:3-5` 只有 Run ID/Runner 名称；无 commit/CI/镜像。
   - `docs/aiqe/evidence/android-node/capability.json:1-12` 有 Run/设备/Artifacts，无 commit/CI/镜像/Workflow Snapshot hash。
2. **版本锁过期**：`config/aiqe-version.lock` 内容为
   `{"commit":"ff5353a40","image_tag":"release-m15-20261114","migration_head":"20261123_ta033_mutation_ledger","written_at":"2026-11-13T16:20:00Z"}`；
   当前 HEAD 为 `86a44b2cb`（2026-11-19），且仓库已有 `20261124_*` 迁移（`alembic/versions/20261124_aud005...` 等）——版本锁与代码/migration head 不一致，无 CI 校验。
3. **手工填写测试数量**：`docs/aiqe/aud-remediation-v15-final-report.md:30-34` 等处直接写 `test_aiqe_aud001_target_policy.py (46)`、`(28)`、`(44)` 等；规格要求「最终报告不得手工填写测试数量；从 CI artifact 自动生成」。`scripts/aiqe/run_dogfood.ps1:44-46` 写 `日期/命令/结果` 的 md 也由脚本手写，无 commit/CI/环境。
4. **状态词表缺失**：规格要求文档区分 `IMPLEMENTED / UNIT_TESTED / INTEGRATION_TESTED / E2E_VERIFIED / PRODUCTION_OBSERVED` 与 `NOT_RUN`；`docs/aiqe/**` 无该词表（grep 仅在本 G 报告/基线审计上下文出现）。
5. **v1.6 交付物缺失**：`docs/aiqe/v1.6/` 只有 `_audit/baseline-audit-G1-G3.txt`；规格 §13 要求的 `V1.6-Issue-Implementation-Matrix.md`、`V1.6-Requirement-Code-Test-Evidence-Matrix.md`、`V1.6-Test-Plan-and-Evidence.md`、`V1.6-GA-Release-Report.md`、`V1.6-Production-Runbook.md`、`V1.6-Rollback-and-Recovery.md` 全部缺失（已用 Test-Path 核对）。
6. **无 evidence-index 生成器 / 无 AIQE CI**：全仓 grep `evidence-index|--junitxml|junit`（scripts）0 命中；`.github/workflows/*.yml` 无 AIQE 作业；无 `scripts/aiqe/*evidence-index*`。
7. **发布记录**：`docs/aiqe/evidence/production-deploy-20261119.md:1-14` 有生产部署/备份/回滚标签，但仍是人工 md；无 commit SHA 与 CI run 的机器可读关联。

### 6.2 Gaps（可验证）

- **G23-1** 验收证据无 commit SHA / PR / CI run / 环境版本 / Workflow Snapshot hash / Runner 镜像 digest（各 evidence 文件逐项缺失）。
- **G23-2** `config/aiqe-version.lock` 落后于 HEAD 与 migration head，且无 CI 校验（`commit ff5353a40` vs `86a44b2cb`）。
- **G23-3** 报告中的测试数量手工填写（`aud-remediation-v15-final-report.md:30-34`），非 CI artifact 自动生成。
- **G23-4** 未使用规格要求的状态词表（IMPLEMENTED/UNIT_TESTED/INTEGRATION_TESTED/E2E_VERIFIED/PRODUCTION_OBSERVED/NOT_RUN）。
- **G23-5** v1.6 交付文档全部缺失（`docs/aiqe/v1.6/` 仅 1 个基线审计文件）。
- **G23-6** 无 `evidence-index.json` 生成器与示例；无机器可读报告，CI 无法解析 PASS/FAIL/BLOCKED。
- **G23-7** 无 CI 作业把测试/证据与 commit/CI 关联（workflow grep AIQE = 0）。

### 6.3 已存在测试与入口质量

无自动化测试；现状依赖人工 md。`scripts/aiqe/run_dogfood.ps1` 是唯一「报告生成器」，但它只记录日期/命令/结果（`:41-49`），且报告目录在 `work-logs/aiqe/dogfood/`，不含 commit/CI/环境/digest。

### 6.4 最小整改建议

1. 新增 `scripts/aiqe/generate_evidence_index.py`：读取 `GITHUB_SHA`/CI run id/环境/镜像 digest/test JUnit XML + 本地 DB 的 Run/Job/Assertion/Artifact ID，生成 `docs/aiqe/v1.6/evidence-index.json`；缺任一关键 ID 时非 0 退出。
2. 更新 `config/aiqe-version.lock` 写入当前 commit/tag/alembic head/镜像 digest，并在 CI 增加「lock.commit == HEAD && lock.migration_head == alembic heads」校验（缺失/不一致 fail）。
3. 把 v1.5/v1.6 报告改为模板渲染（从 JUnit/coverage/evidence-index 读取），禁止手工数字；文档状态列使用统一词表，未运行显式 `NOT_RUN`。
4. 补齐 `docs/aiqe/v1.6/` 规格 §13 的 9 份文档（矩阵/契约/迁移计划/测试计划/runbook/rollback/GA 报告），每份引用 evidence-index 与 commit。
5. 新增 CI workflow（或用 main-quality-gate 子 job）产出 evidence-index 并 `upload-artifact`；PR 模板加 Issue/Requirement/证据字段。
6. **必须新增负向测试** `tests/ci/test_v16_023_traceability.py`：
   - 证据条目缺 commit/CI run/env/RunID/snapshot hash/digest → 生成器非 0；
   - `config/aiqe-version.lock` 的 commit 与 HEAD 不一致 → 校验失败；
   - 文档出现手工测试数字（无生成标记）→ 检查失败；
   - 文档状态使用 `PASS` 但实际为 skip/BLOCKED → 检查失败。

### 6.5 可复核命令

```powershell
$root='F:\CamelTv-worktrees\DeepSeek_Harness-aiqe-v1-6'
Get-Content "$root\config\aiqe-version.lock"
git -C $root rev-parse HEAD
git -C $root log -1 --format='%H %ad %s' --date=iso
Get-ChildItem "$root\docs\aiqe\v1.6" -Recurse -File
Select-String -Path "$root\docs\aiqe\evidence\*.json","$root\docs\aiqe\evidence\*.md" -Pattern 'commit|github|CI|image|digest'
Select-String -Path "$root\scripts\aiqe\run_dogfood.ps1" -Pattern '日期|命令|结果'
Select-String -Path "$root\docs\aiqe\aud-remediation-v15-final-report.md" -SimpleMatch 'test_aiqe' | Select-Object -First 5
```

---

## 7. V16-024 生产化：监控、限流、备份、灰度与回滚

**状态：PARTIAL（监控/告警/限流/灰度四项 0 实现，回滚/备份为既有文档+脚本，无演练证据）**

### 7.1 规格要求 → 实现映射

| 规格要求（§8） | 现状 | 证据 |
|---|---|---|
| §8.1 API/Worker/Browser Runner/Device Runner 分离、最小权限、egress deny-by-default、只读 DB 账号、Vault、TLS | 部署侧有 runner 独立进程与 egress 文档；AIQE 侧有只读 DB 连接/策略（V16-001/004 范围）；无 Worker 容器加固/egress 配置产物（`deploy/` 无 AIQE 相关） | `docs/aiqe/runner-deployment.md:141-145`；`deploy/` 无 observability/aiqe 文件；本项跨组 |
| §8.2 必须监控的 21 个 `aiqe_*` 指标（执行 8 + 安全 7 + Agent/Learning 6） | **0 实现**：全仓 grep `aiqe_run_queued_age_seconds|aiqe_job_pending_age_seconds|aiqe_job_lease_expired_total|aiqe_run_without_job_total|aiqe_secret_canary_detected_total|...` 全部 0 命中；无 prometheus_client / OpenTelemetry / /metrics 端点 | 见 §7.2 第 1 条 |
| §8.3 告警规则（canary、策略不可用、queued 无 Job、lease 异常、跨项目、PASS 无证据、benchmark 越 gate） | **0 实现**：仓库无 alertmanager/prometheus rules/告警代码 | 全仓 `prometheus|grafana|alertmanager` 0 命中 |
| §8.4 灰度：Stage 0–5 + 停止条件 | **0 AIQE 灰度实现**：只有两个布尔开关 `aiqe_prod_run_create_enabled`、`aiqe_inprocess_executor_enabled`；无 shadow/小流量/停止条件代码；`docs/灰度放量SOP.md` 是通用平台 SOP，未覆盖 AIQE 执行链 | `app/core/config.py:27,36`；`docs/灰度放量SOP.md` |
| §8.5 迁移 Expand→Migrate→Contract、备份/恢复演练、staging 演练 | 迁移本身有（alembic 单头要求见 CI）；备份/回滚为 **人工文档**（`docs/aiqe/rollback.md` §2 手写 pg_dump；§3 回滚脚本），无自动化备份任务、无 staging 演练记录；版本锁过期 | `docs/aiqe/rollback.md:18-42`；`scripts/ops/aiqe-version-lock.ps1`、`scripts/ops/aiqe-rollback.ps1` 存在；`config/aiqe-version.lock` 过期 |
| §8.6 生产回滚条件（canary/SSRF/跨项目/假 PASS/无 Job/fencing/错误率） | 条件未代码化/未接入告警；人工 runbook 有部分（v1.4 边界回滚 §5） | `docs/aiqe/rollback.md:53-60` |
| §8.2 「指标按 project 低基数、禁止 Secret 进 label」 | 无指标实现，无法验证；但 repo 无相关约束/检查 | — |

补充：`app/core/rate_limit.py:65-72` 只有 `open_api_limiter`/`login_limiter`/`register_limiter`，**没有 AIQE API/Run 创建/Job 认领的限流**；`app/core/config.py:33` `aiqe_reconciler_enabled=False` 默认关闭且无指标/告警。

### 7.2 关键证据（可复核）

1. 全仓指标名/监控栈 0 命中：
   - `Select-String -Path $root -Pattern 'aiqe_run_queued_age_seconds|aiqe_job_pending_age_seconds|aiqe_secret_canary_detected_total' -Recurse` → 仅本报告/规格文档。
   - `Select-String -Path $root -Pattern 'prometheus|grafana|alertmanager' -Recurse -Include *.py,*.yml,*.yaml` → 0。
2. `app/core/config.py:26-45` — AIQE 开关只有 `aiqe_inprocess_executor_enabled`、`aiqe_reconciler_enabled`、`aiqe_prod_run_create_enabled`、`aiqe_run_stale_seconds`、`aiqe_retention_days` 等；无 SLO/限流/灰度比例配置。
3. `app/core/rate_limit.py:65-72` — 限流器仅三类（Open API/登录/注册），无 AIQE。
4. `docs/aiqe/ops.md:66-72` — 仅有「状态对账（必须定时）`python scripts/qa/aiqe_reconcile.py`」，没有监控/告警/指标采集；`:74-85` 的开关表也无观测项。
5. `docs/aiqe/rollback.md:3-60` — 版本锁、发布前手工 `pg_dump`、`aiqe-rollback.ps1`、回滚后验证；**无演练记录**（文档要求「发布前备份并验证可恢复；staging 用生产数据脱敏副本演练」）。
6. `docs/aiqe/evidence/production-deploy-20261119.md:8-14` — 一次手工生产备份（dump 190M）+ 旧镜像回滚标签，可作「备份可执行」的弱证据；但 `config/aiqe-version.lock` 仍停 2026-11-13，说明版本追溯未随发布更新（同时是 V16-023 gap）。
7. `deploy/` 目录 grep `prom|grafana|alert|backup|canary|aiqe|monitor` → 0 结果（无运维定义）。

### 7.3 Gaps（可验证）

- **G24-1** §8.2 全部 15 个 `aiqe_*` 指标无实现（无采集、无 /metrics、无 exporter）。
- **G24-2** §8.3 告警规则无实现（无 rules 文件、无告警代码）。
- **G24-3** AIQE 无 API 限流/队列背压（`core/rate_limit.py:65-72` 仅三类非 AIQE）。
- **G24-4** 无 AIQE 灰度阶段（Shadow/Dogfood/小流量）与停止条件实现；只有布尔开关与通用 SOP。
- **G24-5** 无备份自动化与恢复演练记录；回滚脚本/版本锁存在但版本锁过期，无 CI 校验。
- **G24-6** `aiqe_reconciler_enabled=False` 默认关闭且无「queued run 无 Job」告警；`aiqe_run_without_job_total` 无实现。
- **G24-7** 无 SLO/延迟/错误率观测；无生产观察窗口记录（V16-024 验收要求「生产演练完成且回滚可执行」）。
- **G24-8** 无 egress deny-by-default 的 AIQE 部署产物（`runner-egress/policy.json` 仅单机 lab 证据，非生产）。

### 7.4 已存在测试与入口质量

无指标/告警/限流/备份演练测试。`tests/test_aiqe_p0_ops.py` 仅覆盖 dispatch 与 artifact GC；`tests/test_aiqe_reconciler.py` 覆盖 reconcile 逻辑但不含指标/告警。没有任何测试从「生产 smoke/告警触发/回滚演练」入口进入。

### 7.5 最小整改建议

1. 新增 `app/aiqe/metrics.py`（或 `app/observability/aiqe_metrics.py`）：按规格 §8.2 定义 15 个 counter/gauge/histogram，label 仅 `project_id` 等低基数维度；在 `run_launch`、`dag_scheduler`、`job_consumer`、`lease`、`reconciler`、`target_policy`、`secret_vault`、`artifact_service` 埋点；暴露受保护的 `/metrics` 或推送到 Prometheus。
2. 新增 `deploy/monitoring/aiqe-alerts.yml`（Prometheus rules）+ `docs/aiqe/V1.6-Production-Runbook.md`（告警处置/on-call/停止条件），并把 runbook 与 §8.6 回滚条件一一对应。
3. 在 `app/core/rate_limit.py` 或中间件中增加 AIQE API 限流（每 project/每 node），并对 Run 创建、Job claim、Artifact 上传分别设阈值。
4. 灰度：在 `run_launch`/`job_consumer` 增加 stage 开关（shadow 只读、internal dogfood、小流量按 project/白名单）+ 停止条件（canary/SSRF/跨项目/假 PASS 自动熔断）。
5. 备份：新增定时备份任务/脚本（`scripts/ops/aiqe-backup.ps1`）+ 恢复演练脚本，演练结果写入 `docs/aiqe/evidence/` 并在 CI/发布报告引用；更新 `config/aiqe-version.lock` 加入镜像 digest 与 CI run。
6. **必须新增负向测试** `tests/test_aiqe_v16_024_production_ops.py`：
   - 策略拒绝/跨项目拒绝/canary 命中时对应 counter 递增，且 label 不含 Secret/URL/用户输入。
   - `/metrics` 或 exporter 输出包含 15 个指标名。
   - 告警规则文件可解析且引用的指标真实存在（用 promtool/自写解析）。
   - 超限 Run 创建/Job claim/Artifact 上传返回 429/带 retry-after。
   - 备份脚本在模拟 DB 上产出非空 dump 且恢复后校验和一致；版本锁校验失败时 CI 失败。

### 7.6 可复核命令

```powershell
$root='F:\CamelTv-worktrees\DeepSeek_Harness-aiqe-v1-6'
Select-String -Path $root -Pattern 'aiqe_run_queued_age_seconds|aiqe_job_pending_age_seconds|aiqe_secret_canary_detected_total|aiqe_target_policy_denied_total' -Recurse -Include *.py,*.yml,*.yaml,*.md | ForEach-Object { $_.Path.Replace("$root\",'') + ':' + $_.LineNumber }
Select-String -Path $root -Pattern 'prometheus|grafana|alertmanager' -Recurse -Include *.py,*.yml,*.yaml | Select-Object -First 5
Select-String -Path "$root\test-platform-v2\backend\app\core\rate_limit.py" -Pattern 'limiter|RateLimiter'
Select-String -Path "$root\test-platform-v2\backend\app\core\config.py" -Pattern 'aiqe_reconciler_enabled|aiqe_prod_run_create_enabled|aiqe_inprocess_executor_enabled'
Get-ChildItem "$root\deploy" -Recurse -File | Where-Object { $_.Name -match 'prom|grafana|alert|backup|canary|monitor' }
```

---

## 8. 跨 Issue 与全组共性发现

1. **两套 Preflight / 两套能力语义**：`app/aiqe/services/preflight.py`（Launch 用，AVAILABLE+30s+OR 能力+可缺平台+字符串 evidence）与 `app/aiqe/services/capability_preflight.py`（Worker/守卫用，AVAILABLE+VERIFIED+180s）并存且口径不一致；`run_launch.py:20,204` 用前者。这是 V16-015/016 所有「能力真实性」问题的根因。
2. **VERIFIED 没有服务端可信来源**：`mark_verified` 全仓仅测试/脚本调用；唯一「验机」路径是伪造 `COMPLETED/PASS` Run 的 adb 脚本（`scripts/aiqe/verify_android_device.py:114-171`）。按规格 §0.2.8，这类证据不得作为验收依据。
3. **Artifact 证据链与执行链脱节**：Worker 采集路径会脱敏并落 Artifact，但外部 Runner（Playwright/Appium/真机）上报路径 `execution.evidence=[]`（`execution_service.py:931-951`），截图/Trace 不进 `run_artifacts`；同时零 Artifact 的 Run 可以 PASS（`tests/test_aiqe_external_node_report.py:86-107` 已固化）。V16-018 的「required evidence」在 AIQE 侧没有声明模型。
4. **证据可追溯性整体缺失**：无 commit/CI/PR/镜像 digest 关联、版本锁过期、报告手写数字、v1.6 交付文档缺失。V16-022/023/024 三个 P2/P0 项共享同一根因：没有 CI 证据管线。
5. **文档与代码口径漂移**：心跳 TTL（180 vs 30 vs 文档 30）、`runner-deployment.md:44-48` 教手工 `mark_verified`、`runner-deployment.md:78` 的 30s、`ops.md:60` 的 `--password` 示例、`docs/aiqe/evidence/external-runner-e2e.md` 的 Artifacts 与 `run_artifacts` 实际来源不一致。文档本身不能作为证据。
6. **在途 V16-001 的边界**：工作树中 `dogfood.py` 已删除 `_ensure_target_policy`（改为要求管理员预置策略，`dogfood.py:330-349`），`execution_service`/`node_executor` 已引入 `policy_context`。这**不与本组结论冲突**：能力的「验证 Run」和「Preflight 只认 VERIFIED」仍未实现，能力的写入仍来自脚本/测试。

---

## 9. 复核命令清单（只读，可直接复制）

```powershell
$root='F:\CamelTv-worktrees\DeepSeek_Harness-aiqe-v1-6'

# 基线
git -C $root rev-parse HEAD
git -C $root status --porcelain=v1
git -C $root diff --stat

# V16-015
Select-String -Path "$root\test-platform-v2\backend\app\aiqe\services\capability_registry.py" -Pattern 'DEFAULT_HEARTBEAT_TTL_SECONDS|SCHEDULABLE_STATUSES|def mark_verified|def invalidate_verification|def mark_degraded|def select_nodes'
Select-String -Path "$root\test-platform-v2\backend\app\aiqe\services\preflight.py" -Pattern 'HEARTBEAT_TTL_SECONDS|any\(cap in caps|row.available|def preflight_graph'
Select-String -Path "$root\test-platform-v2\backend\app" -Pattern 'mark_verified\(' -Recurse | ForEach-Object { $_.Path.Replace("$root\",'') + ':' + $_.LineNumber }
Select-String -Path "$root\test-platform-v2\backend\app\aiqe\models\capability.py" -Pattern 'verification_run_id|runner_image|os_version|device_|limitations'

# V16-016
Select-String -Path "$root\test-platform-v2\backend\app" -Pattern 'MiniappAdapter|DesktopDriver|IotDriver|DeviceBroker' -Recurse | ForEach-Object { $_.Path.Replace("$root\",'') + ':' + $_.LineNumber }
Select-String -Path "$root\test-platform-v2\backend\app\aiqe\models\platform_binding.py" -Pattern 'environment_id|device_pool|runner_version|runner_image'
Select-String -Path "$root\test-platform-v2\backend\app\aiqe\services\device_broker.py" -Pattern 'IOS_ENABLED|class DeviceBroker|def allocate|def release|def health'
Select-String -Path "$root\test-platform-v2\backend\app\aiqe" -Pattern 'fps|cpu_percent|memory_mb|perf_metrics' -Recurse

# V16-018
Select-String -Path "$root\test-platform-v2\backend\app\aiqe\models\artifact.py" -Pattern 'created_by|retention_policy|access_scope'
Select-String -Path "$root\test-platform-v2\backend\app\aiqe\services\artifact_service.py" -Pattern 'expires_at|mime_type|expected_size|expected_sha256|upload_status'
Select-String -Path "$root\test-platform-v2\backend\app\aiqe\services\artifact_gc.py" -Pattern 'created_at|retention_until|project_id'
Select-String -Path "$root\test-platform-v2\backend\app\aiqe\services\evidence_service.py" -Pattern 'upload_status|artifact_row'
Select-String -Path "$root\test-platform-v2\backend\app\aiqe\services\execution_service.py" -Pattern 'evidence=\[\]|persist_execution_evidence'
Select-String -Path "$root\test-platform-v2\backend\app\api\v1\aiqe_artifacts.py" -Pattern 'expires_at|content = await|metadata'

# V16-021
Select-String -Path "$root\test-platform-v2\backend\scripts\aiqe\evidence_local_20.py" -Pattern 'admin123|--password|AIQE_EVIDENCE_PASSWORD'
Select-String -Path "$root\scripts\aiqe\run_dogfood_mixed.py","$root\scripts\qa\aiqe_local_runner.py" -Pattern 'password'

# V16-022
Select-String -Path "$root\.github\workflows\main-quality-gate.yml" -Pattern 'pip install|pytest|junit|cov-report|upload-artifact'
Select-String -Path "$root\test-platform-v2\backend\pyproject.toml" -Pattern '\[project\]|dependency-groups'
Select-String -Path "$root\test-platform-v2\backend\pytest.ini" -Pattern 'markers|slow|integration'
Select-String -Path "$root\.github\workflows\*.yml" -Pattern 'aiqe|AIQE'

# V16-023
Get-Content "$root\config\aiqe-version.lock"
Get-ChildItem "$root\docs\aiqe\v1.6" -Recurse -File
Select-String -Path "$root\docs\aiqe\evidence\*.json","$root\docs\aiqe\evidence\*.md" -Pattern 'commit|github|CI|image|digest'
Select-String -Path "$root\docs\aiqe\aud-remediation-v15-final-report.md" -SimpleMatch 'test_aiqe' | Select-Object -First 8

# V16-024
Select-String -Path $root -Pattern 'aiqe_run_queued_age_seconds|aiqe_job_pending_age_seconds|aiqe_secret_canary_detected_total|aiqe_target_policy_denied_total|aiqe_job_lease_expired_total' -Recurse -Include *.py,*.yml,*.yaml | ForEach-Object { $_.Path.Replace("$root\",'') + ':' + $_.LineNumber }
Select-String -Path $root -Pattern 'prometheus|grafana|alertmanager' -Recurse -Include *.py,*.yml,*.yaml | Select-Object -First 5
Select-String -Path "$root\test-platform-v2\backend\app\core\rate_limit.py" -Pattern 'limiter'
Get-ChildItem "$root\deploy" -Recurse -File | Where-Object { $_.Name -match 'prom|grafana|alert|backup|canary|monitor' }
```

---

## 10. 审计限制与说明

- 本报告只读静态代码/测试/迁移/CI/文档，未运行 pytest、未连库、未启动服务；因此状态是「代码与现有测试证据层面」的结论，不代表运行时已验证。`PARTIAL` 不等于「已验收」。
- 未对 V16-001 在途改动做验收（属其他审计组）；但本组引用的 `dogfood.py`/`execution_service.py`/`node_executor.py` 行号均为当前工作树，若 V16-001 继续改动这些文件，行号需重新核对。
- 本报告中「无生产调用」的判断基于全仓 `app/**` 的 import/调用检索；不排除运行时通过字符串/反射调用（已对关键函数人工确认无 `getattr` 路径）。
- 所有 Gaps 均可在第 9 节命令或对应行号复核；没有为了凑数而虚构的 gap，也没有把「只有类名/文件名/README 声明」当作已实现。
