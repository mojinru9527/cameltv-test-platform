---
title: "ADR-0032: AIQE V1.6 产品 TC 基线映射与编号可追溯性"
owner: "qa-team"
last_reviewed: "2026-11-28"
status: "proposed"
expires: "2027-05-28"
tags: ["adr", "aiqe", "e2e", "product-tc", "baseline", "traceability"]
related: ["../aiqe/v1.6/e2e/product-tc-config.yaml", "../aiqe/v1.6/e2e/product-results.json", "0014-single-main-trunk-ai-worktrees.md"]
---

# ADR-0032: AIQE V1.6 产品 TC 基线映射与编号可追溯性

## 状态

**提议中（Proposed）— 批准状态 PENDING / 执行状态 BLOCKED。**

| 项目 | 当前值 |
|---|---|
| 产品负责人批准 | **待定（未指定批准人，未批准）** |
| 测试负责人批准 | **待定（未指定批准人，未批准）** |
| 批准时间 | **pending（未批准）** |
| 批准 commit / ADR 版本 | **pending（批准时必须记录 main 或 release SHA + 本 ADR 版本）** |
| 基线版本 | `v1.6.2-hardening` |
| 执行状态 | **BLOCKED**：10 条产品 TC 无受批准的隔离 Test 环境与真实 Runner |

在本 ADR 获得上述两名负责人明确批准（并记录批准 SHA）之前：

1. `product-tc-config.yaml` 中 `baseline_version: v1.6.2-hardening` 只能产生
   `BLOCKED` / `NOT_PROVEN`，**不得**产生任何产品 `PASS`；
2. 旧 V1.6 基线（含 2026-11-27 静态摘要）的执行结果 **不得**自动继承到本基线；
3. Release Verdict Gate E 与任何 GA/发布结论 **不得**引用本 ADR 作为已批准依据；
4. 本 ADR 不被视为“已批准的映射”，只是待审批的整改提案。

## 日期

2026-11-28

## 背景

复审报告（`CamelTv_AIQE_V1.6_Main_9bbbdbb_Code_Audit.md`）与《AIQE V1.6.2 整改开发落地
实施手册》§4 确认：

1. 当前 `docs/aiqe/v1.6/e2e/product-tc-config.yaml` 的 TC-AIQE-001～010 与 V1.6 原始验收
   计划使用**相同编号但不同语义**，例如：
   - 原 TC-006 = Secret Handle 全链路保护；当前 TC-006 = 上游第三方故障；
   - 原 TC-009 = Noise E1–E6 因果实验；当前 TC-009 = 多端 AC 对照；
   - 原 TC-010 = A0–A6 Agent/Benchmark/审批/发布；当前 TC-010 = Learning Candidate 发布。
2. 仓库内没有批准的 ADR / 映射表，导致“产品 TC 通过”无法说明究竟覆盖了哪套验收要求。
3. 历史静态 `product-results.json` 曾以人工维护的通过摘要存在，不能重放、不能证明
   本次执行，构成 FIX-001 所修复的“假绿”风险。

手册 §4.2 明确禁止的处置方式（本 ADR 同样不采用）：自行判断“新 TC 更合理”后继续沿用
旧编号；删除旧 TC 定义；改文档把旧验收要求解释成新含义；用一个新业务场景替换历史失败
的旧场景。

## 决策

1. **基线唯一**：本轮产品 TC 基线为 `v1.6.2-hardening`。`product-tc-config.yaml`、
   `product-results.json` 与 release verdict 必须读取并比对 `baseline_version`；
   不同基线的结果不得混在同一次验收中。
2. **编号保留、语义重新声明**：TC-AIQE-001～010 作为 Requirement ID 保留，但每条 TC
   的当前语义、必需断言、必需 artifact、环境与阻塞条件在配置 schema 2.0 中重新声明。
   旧 V1.6 语义不因编号被复用而消失，逐条映射见下文表 A。
3. **旧执行结果不继承**：旧基线产生的 Run/Job/静态摘要一律不能作为本基线 PASS；
   本基线 PASS 必须来自本次 `run_product_tc.py --run` 生成、经
   `verify_product_tc_results.py` 验证的机器结果（runner/execution/assertions/artifacts/
   commit_sha/environment 齐全）。
4. **缺环境即阻断**：当前没有隔离 Test 业务环境与受批准 Runner，10 条 TC 在配置中
   显式 `runner: null` + `blocked_by/owner/unblock_action/blocked_status: BLOCKED`。
   外部生产站点 Playwright 手工脚本、半自动截图、Service 直调**不得**登记为 PASS Runner。
5. **映射类型**：`SAME_SCOPE` / `SPLIT` / `MERGED` / `REPLACED` / `NEW` / `DEFERRED`，
   逐条见下表。旧范围被替换或延期时，必须给出拟登记 Requirement ID、责任人、恢复版本。
6. **恢复路径**：旧范围恢复由 FIX-004（TC-001～007 场景）、FIX-005（A0–A6）、
   FIX-007（多端/半自动）、FIX-008（Defect 回归）交付；交付前旧范围保持
   `UNCOVERED/BLOCKED`，不得宣称为已覆盖。
7. **批准门槛**：本 ADR 由产品负责人 + 测试负责人批准，并将映射结果登记到
   `docs/aiqe/v1.6/traceability/requirements.yaml` 后，才允许把任何 TC 的 `runner`
   从 `null` 改为真实 Runner，并才允许 Gate E 消费其 PASS 结果。

## 基线映射核对表（旧 V1.6 范围 → 当前 TC 语义）

> 说明：旧 V1.6 范围来自复审报告 §5.2 与整改手册 §4.5；“旧强制证据”按复审报告
> §5.2 与手册 §5 的验收要求归纳（原始计划原文见 V1.6 计划 §V16-017）；当前语义来自
> `product-tc-config.yaml`（schema 2.0）。当前 10 条 TC 的 Runner 均为 `null`，
> 状态均为 `BLOCKED`。

| 旧 TC | 旧名称 / 验收目标 | 旧强制证据 | 当前 TC | 当前语义 | 当前 Runner | 映射类型 | 理由 | 残余风险 | Requirement ID | 未覆盖范围与去向 |
|---|---|---|---|---|---|---|---|---|---|---|
| TC-001 | API 创建业务数据 → 后台 UI 修改 → DB 只读核验 → PC/Mobile 前台 UI，全部同一 Run | 同一 Run 的 Run/Job/NodeRun/Assertion/Artifact + DB 只读快照 | TC-AIQE-001 | 需求契约冻结 + 需求变更影响（V1 checksum 稳定、V2 差异可见） | null | **SPLIT** | 当前 TC-001 只覆盖契约冻结部分；原混合链未被同一 Run 覆盖 | 混合链路仍无产品级验收；契约冻结证据不能替代 UI/DB 链路 | TC-AIQE-001（部分）+ `V16-017-R3`（拟登记） | 原混合链未覆盖 → FIX-004 §5.1 恢复 |
| TC-002 | HTTP 200 但业务 Assertion FAIL，Run 不得 PASS，证据完整 | Run 终态 FAIL + Assertion FAIL + artifact | TC-AIQE-002 | 运营后台资讯发布 → DB 只读 → 公开 API/前台可见 | null | **DEFERRED** | 当前 TC-002 是发布成功链，不复现“HTTP 200 业务断言失败”负例 | 业务断言失败路径无产品级验证；资讯发布 PASS 不能代表旧 TC-002 | `V16-017-R3`（拟登记） | 未覆盖 → FIX-004 §5.2/§5.3 增加负例 |
| TC-003 | Chromium 真实交互 + iframe/fetch/redirect 对未授权内网目标拦截 | 页面真实交互结果 + policy decision/deny reason | TC-AIQE-003 | API 首次失败 + 重试成功（不得掩盖失败） | null | **REPLACED** | 当前 TC-003 是失败/重试语义，不含真实 UI 交互与安全拦截 | 真实浏览器交互与安全拦截无产品级证据；重试 PASS 不能替代 | `V16-017-R3`（拟登记） | 未覆盖 → FIX-004 §5.3 保留真实 UI + 安全拦截 |
| TC-004 | Query Registry 仅允许 SELECT；inline/write/cross-tenant/cross-project 全拒绝，DB 无写入 | Registry 允许/拒绝记录 + DB 只读核对 | TC-AIQE-004 | 浮层交叉干扰（浮层打开不误触底层、关闭后恢复） | null | **REPLACED** | 当前 TC-004 是 UI 浮层场景；广告模块不属于未来娃屿项目（已确认 WAIVED，见 `TC-AIQE-004-Waiver.md`） | DB 只读 / Query Registry 完全未覆盖；浮层 WAIVED 本身也不是 PASS | `V16-017-R3`（拟登记） | 未覆盖 → FIX-004 §5.4 恢复 DB 只读/Registry |
| TC-005 | 受控 DNS/HTTP 模拟 SSRF、redirect、DNS 变化、IPv6 mapped，危险目标零抵达 | 受控目标服务端计数器 = 0 + TargetPolicy 决策 | TC-AIQE-005 | 并发数据污染（并发写不串租户、不产生重复行） | null | **SPLIT** | 当前 TC-005 只覆盖并发数据隔离；SSRF/DNS 安全场景未覆盖 | 两类场景能力不同，并发 PASS 不能代表 SSRF/DNS 被验证 | TC-AIQE-005（部分）+ `V16-017-R3`（拟登记） | SSRF/DNS 未覆盖 → FIX-004 §5.5 单独恢复 |
| TC-006 | Token Canary 从登录输出到 Handle 下游消费，DB/API/Event/Artifact 零明文 | Secret 引用链 + 全表面明文扫描 | TC-AIQE-006 | 上游第三方故障（504 归因 BLOCKED、不误判产品 Bug） | null | **REPLACED** | 当前 TC-006 是上游故障归因，完全不含 Secret Handle 链路 | Secret 全链路保护无产品级证据；上游故障 PASS 不能替代 | `V16-017-R3` + `V16-017-R4`（拟登记） | 未覆盖 → FIX-004 §5.6 必须单独保留 Secret 全链路 |
| TC-007 | Worker 在 claim/执行/写结果/ack 各阶段崩溃、重复消息、迟到结果 fencing | DB 最终状态 + Event 顺序 + Artifact 所属 Attempt | TC-AIQE-007 | UI Runner 自身故障（Runner 失败不产生假 PASS，保留 trace） | null | **REPLACED** | 当前 TC-007 是 UI Runner 故障，不含 Worker lease/fencing | Worker 崩溃/租约/fencing 无产品级证据；Runner 故障 PASS 不能替代 | `V16-017-R3` + `V16-017-R6`（拟登记） | 未覆盖 → FIX-004 §5.7 恢复 Worker crash/lease/fencing |
| TC-008 | Defect、fixed SHA、部署证明、mandatory scope、真实执行、Comparison、幂等 | Regression API 结果 + 固定 SHA + mandatory scope 断言 | TC-AIQE-008 | 开发修复后一键回归（Regression API + 固定 SHA + mandatory scope） | null | **SAME_SCOPE** | 语义一致：都要求 Defect Regression 正式链路与固定 SHA | Runner/环境缺失导致仍无法执行；当前状态 BLOCKED，不能宣称已验收 | TC-AIQE-008 | 语义未变；待 FIX-008 交付真实 Runner 后执行 |
| TC-009 | E1–E6 对照/实验，故障类别正确归因，实验变量可追溯 | 每类故障注入 + 对照变量 + Run/Job/Artifact | TC-AIQE-009 | 多端 AC 对照（桌面/Android 真实对照，半自动不计 PASS） | null | **DEFERRED** | 当前 TC-009 是多端对照，完全不含 Noise E1–E6 因果实验 | Noise 因果实验无产品级证据；多端一致不能替代故障归因 | `V16-017-R3` + `V16-017-R5`（拟登记） | 未覆盖 → FIX-007 恢复 Noise 实验（单独 Requirement） |
| TC-010 | 真正执行 A0–A6，AgentExecution/ToolExecution/evidence refs、A5 回归范围、A6 双人审批发布 | 真实 AgentTask 链路 + Benchmark + 双人审批 + Candidate 发布 | TC-AIQE-010 | Agent A0–A6 + Benchmark + 审批 → Learning Candidate 发布链 | null | **SPLIT** | 当前 TC-010 仅保留 Learning Candidate 发布部分；A0–A6 真实 AgentTask 链未覆盖 | 无真实 A0–A6 执行证据；Learning 发布 PASS 不能替代完整 Agent 链 | TC-AIQE-010（部分）+ `V16-017-R3`（拟登记） | 未覆盖 → FIX-005/FIX-006 恢复 A0–A6 + Benchmark + 双人审批 |

## 当前新增范围（旧 V1.6 未要求或属于新语义）

| 当前 TC | 当前语义 | 映射类型 | 说明 / 依据 | 残余风险 |
|---|---|---|---|---|
| TC-AIQE-001 | 需求契约冻结与变更影响 | **NEW** | 原 V1.6 验收清单无独立契约冻结 TC；本语义为新增范围 | 不能代替旧 TC-001 混合链 |
| TC-AIQE-002 | 后台发布资讯 → DB 只读 → 公开 API/前台可见 | **NEW** | 旧 TC-002 是失败注入；发布链是新增范围 | 不能代替旧 TC-002 业务断言失败负例 |
| TC-AIQE-003 | API 首次失败 + 重试成功 | **NEW** | 旧 TC-003 是 UI + 安全拦截；重试是新增范围 | 不能代替旧 TC-003 真实交互/拦截 |
| TC-AIQE-004 | 浮层交叉干扰 | **NEW + WAIVED** | 广告模块不属于未来娃屿项目（用户 2026-11-27 确认）；以其他功能浮层适配，状态 WAIVED，不计 PASS | WAIVED 不是通过；旧 TC-004 DB 只读仍未覆盖 |
| TC-AIQE-005 | 并发数据污染 | **NEW** | 旧 TC-005 是 SSRF/DNS；并发隔离是新增范围 | 不能代替旧 TC-005 SSRF/DNS |
| TC-AIQE-006 | 上游第三方故障 | **NEW** | 旧 TC-006 是 Secret 全链路；上游故障是新增范围 | 不能代替旧 TC-006 Secret 保护 |
| TC-AIQE-007 | UI Runner 自身故障 | **NEW** | 旧 TC-007 是 Worker crash/lease/fencing；Runner 故障是新增范围 | 不能代替旧 TC-007 Worker 可靠性 |
| TC-AIQE-009 | 多端 AC 对照 | **NEW** | 旧 TC-009 是 Noise E1–E6；多端对照是新增范围 | 半自动截图不得计 PASS；不能代替 Noise 实验 |
| TC-AIQE-010 | Learning Candidate 发布 | **SPLIT**（旧 TC-010 子集） | 仅覆盖 Learning 发布部分，A0–A6 链未覆盖 | 需 FIX-005/FIX-006 补齐 |
| TC-AIQE-008 | Defect 修复后回归 | **SAME_SCOPE** | 与旧 TC-008 语义一致 | 仍缺真实执行证据与固定 SHA 绑定验证 |

**MERGED 未使用**：本轮不存在“多个旧 TC 合并为一个新 TC 且不丢失旧验收要求”的场景；
禁止用合并名义把未执行的旧范围并入新场景。

## 登记 Requirement ID（V1.6.2 已登记为 BLOCKED）

`docs/aiqe/v1.6/traceability/requirements.yaml` 已登记以下 Requirement ID（状态 `BLOCKED`），
用于保留旧 V1.6 验收范围、责任人与恢复批次；登记不等于验收通过，真实执行前不得关闭：

| Requirement ID | 范围 | 责任人 | 恢复批次 | 当前状态 |
|---|---|---|---|---|
| `V16-017-R3` | 旧 V1.6 产品验收范围恢复（表 A 中 DEFERRED/REPLACED/SPLIT 的未覆盖部分） | qa-automation | FIX-004 + FIX-008 | UNCOVERED / BLOCKED |
| `V16-017-R4` | Secret Handle 全链路保护（旧 TC-006） | qa-automation + security | FIX-004 §5.6 | UNCOVERED / BLOCKED |
| `V16-017-R5` | Noise E1–E6 因果实验（旧 TC-009） | qa-automation | FIX-007 | UNCOVERED / BLOCKED |
| `V16-017-R6` | Worker crash / lease / fencing（旧 TC-007） | backend-aiqe | FIX-004 §5.7 | UNCOVERED / BLOCKED |

在上述条目登记并完成真实执行前，旧验收要求保持“未覆盖”，不得静默删除、不得改写成
当前 TC 语义、不得计入产品 PASS。

## 版本迁移规则（旧基线 → `v1.6.2-hardening`）

1. **强制基线字段**：`product-tc-config.yaml` 顶层与每条 TC 必须声明
   `baseline_version`；`product-results.json` 必须写入同一 `baseline_version`。
2. **结果不得跨基线**：`verify_product_tc_results.py` 校验结果与配置
   `baseline_version` 一致；不一致直接失败。Producer/Consumer 均不得“自动升级”旧结果。
3. **SHA 绑定**：结果文件 `commit_sha` 必须是本次实际 checkout / 测试 SHA
   （优先 `AIQE_TESTED_COMMIT_SHA`，否则 `git rev-parse HEAD`），且逐条 PASS 的
   `execution.tested_commit_sha` 必须与之一致；复用旧 SHA 的结果被拒绝。
4. **环境绑定**：只接受 `isolated-test` / `staging-test` / `ci-test`；`local`、
   `localhost`、`production` 一律拒绝。
5. **证据即执行**：PASS 必须带 runner、execution（run/job/SHA/环境/起止时间）、
   逐条业务断言（含 evidence_ref）与可核验 artifact（路径存在 + sha256 匹配）。
   缺任一项 → `FAIL` / `NOT_PROVEN`。
6. **旧摘要不继承**：旧 `product-results.json` 的通过数字、旧 Run ID、旧 artifact
   ref 一律不得复制到本基线结果；本文件每次 `--run` 重新生成。
7. **Gate E 校验**：Release Verdict Gate E 必须读取配置 `environment` 与
   `baseline_version`，并要求 `verification.verified=true` 且逐条通过；任何
   baseline/环境/SHA 不一致或非 PASS 状态都使 Gate E 非 PASS。
8. **批准后才升级**：本 ADR 批准、矩阵登记、真实 Runner 交付三者完成前，
   `runner` 保持 `null`、状态保持 `BLOCKED`。

## 后果

### 正面影响

- 重新建立 TC 编号与验收要求的可追溯性，消除“同编号不同语义”造成的误读。
- 产品 TC 的 PASS/FAIL/BLOCKED 有单一机器事实源，旧静态摘要不再能签 GA。
- 未覆盖的旧范围被显式记录为 Requirement 恢复项，不再静默消失。

### 负面影响 / 权衡

- 在 ADR 批准与真实环境交付前，产品 TC 只能全部 BLOCKED，产品级验收进度看起来“归零”，
  这是诚实的现状态，不是回归。
- 需要产品负责人/测试负责人批准并登记矩阵，增加治理成本。
- 旧范围恢复需要 FIX-004/005/007/008 多批次投入。

### 残余风险

| 风险 | 影响 | 缓解 |
|---|---|---|
| 旧混合链/Secret/Worker/Noise 等范围未恢复 | 产品验收覆盖面不足 | 表 A 逐条绑定恢复批次与 Requirement ID，禁止宣称已覆盖 |
| 本 ADR 未批准 | 映射不具备验收效力 | 状态 PENDING/BLOCKED；批准前 Gate E 不得 PASS |
| 矩阵未登记新 Requirement ID | 追踪链断裂 | 由 FIX-004+ 批次登记；本 ADR 明确列为待办 |
| 无隔离 Test 环境/真实 Runner | 所有产品 TC 仅能 BLOCKED | 配置显式 blocked_by/owner/unblock_action；禁止假 PASS |
| 外部生产手工脚本被误用 | 生产数据风险 + 假证据 | 配置禁止登记；`runner: null` + verify 拒绝无 runner 的 PASS |
| 生成型发布文档与结果不同步 | release audit 不一致 | 由 FIX-001 在最终批次重新生成 release verdict 文档 |

## 弃选方案

### 方案 A：保留旧编号并直接沿用当前语义，不做映射

- 优点：零迁移成本。
- 缺点：复审所指“同编号不同语义”问题继续存在，无法说明覆盖了哪套要求。
- 放弃原因：违反手册 §4.2/§4.6，无法通过独立验收。

### 方案 B：删除旧 TC 定义，只保留当前 10 条

- 优点：文档简单。
- 缺点：旧验收要求被静默删除，历史失败场景消失。
- 放弃原因：手册 §4.2 明确禁止删除旧 TC 定义。

### 方案 C：把旧要求解释成当前语义（改文档措辞）

- 优点：无需补 Runner。
- 缺点：用文字等价替换执行证据，属于“改文档制造通过”。
- 放弃原因：违反 §0.2/§4.2，且无法通过 verify/Gate E。

### 方案 D：沿用旧静态通过摘要作为新基线证据

- 优点：立即恢复“全绿”。
- 缺点：旧摘要不可重放、无本次 SHA/环境/执行链，构成假绿。
- 放弃原因：FIX-001 与 §0.2 已明确禁止；新基线必须机器生成并可验证。

## 关联

- 整改手册：`CamelTv_AIQE_V1.6.2_整改开发落地实施手册.md` §0、§3（FIX-002）、§4（FIX-003）、§19
- 复审报告：`CamelTv_AIQE_V1.6_Main_9bbbdbb_Code_Audit.md` §5
- 配置：`docs/aiqe/v1.6/e2e/product-tc-config.yaml`
- 结果：`docs/aiqe/v1.6/e2e/product-results.json`
- 验证器：`scripts/aiqe/verify_product_tc_results.py`
- 执行器：`scripts/aiqe/run_product_tc.py`
- Runner 合同：`scripts/aiqe/per_tc/runner_contract.py`
- 相关 ADR：ADR-0014（单一 main 主干与 AI Worktree 隔离）
- 相关治理：Release Verdict Gate E、`docs/aiqe/v1.6/traceability/requirements.yaml`（待登记）
