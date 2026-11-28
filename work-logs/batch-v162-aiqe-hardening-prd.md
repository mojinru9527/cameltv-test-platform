# Batch AIQE-V162 — V1.6.2 Hardening 整改 PRD

> `mode: full`（涉及 AIQE 执行链路 / Agent / Benchmark 语义加固）
> 关联手册：`CamelTv_AIQE_V1.6.2_整改开发落地实施手册.md`（FIX-001～FIX-015）
> 基线：`origin/main` = `2d2f508d5d1fd452972e7af49d9b4f3bde2e7b01`
> 分支：`feature/aiqe-v162-hardening`

## 1. 背景与问题

V1.6.1 复审（PR #639/#640/#641）确认：发布判定在 Runtime `ga_ready=false`、产品 TC 仅
1/10 真实 PASS 的情况下仍输出 `GA_SIGNED`；产品 TC Runner 全为 null；TC 编号语义漂移；
Agent/Benchmark/多端/Regression 证据存在 Service 直调、半自动折算、另一用例替代原缺陷；
生产测试凭据明文；生产阶段跳过仍标 PASS；provenance、审计关闭、Ruleset、Reviewer 身份
均不满足 GA 条件。

## 2. 目标

把上述 15 项复审发现转化为可执行、可验证、可否决的工程整改，默认 fail-closed：
**任何缺失证据、未执行阶段、未绑定身份的验收都不得计入 PASS，也不得签署 GA。**

## 3. 范围（FIX-001～FIX-015）

| FIX | 范围 | 交付 |
|---|---|---|
| FIX-001 | Gate E 假绿 | 严格 Gate E + RV-001～012 测试 + CLI 退出码 |
| FIX-002 | 产品 TC Runner | 配置 schema v2、`--plan/--run/--verify-results`、Runner 合同 |
| FIX-003 | TC 基线漂移 | ADR 0032 映射、baseline_version 校验 |
| FIX-004 | TC-001～007 场景 | Runner 执行结构与业务断言（无环境时 BLOCKED） |
| FIX-005 | A0–A6 正式链 | AgentTask API → Job → Worker → Audit E2E |
| FIX-006 | Benchmark/Learning | 样本级指标复算、数据集口径、双人审批 |
| FIX-007 | 多端状态 | `SEMI_AUTOMATIC` 只映射 PARTIAL，最弱覆盖聚合 |
| FIX-008 | Defect 回归 | WWY-V5-001 保持 OPEN，正式 Regression API + scope/SHA/comparison |
| FIX-009 | 凭据与扫描 | 移除明文、Secret 注入、Scanner 覆盖 `.fill()`、当前 SHA 分级 |
| FIX-010 | 生产阶段 | 跳过阶段标 NOT_RUN/WAIVED，Gate F 语义校验 |
| FIX-011 | Provenance | tested/head/merge/release SHA 分字段，Builder 不覆盖 |
| FIX-012 | 审计关闭 | closure_rule_id + 语义验证器，旧 CLOSED 重新审计 |
| FIX-013 | Ruleset | 精确 AIQE Aggregate required check + 快照 |
| FIX-014 | Reviewer 身份 | GitHub login/user id/review id/SHA 绑定 |
| FIX-015 | 最终验收 | 精确 SHA 全量门禁、Evidence Manifest、最终报告 |

## 4. 非目标（明确不做）

- 不在本批次伪造任何生产账号、GitHub Review、CI Run、Run/Job/Assertion ID。
- 不在无隔离 staging/Test 环境与 Secret 的情况下宣称产品 TC PASS。
- 不执行生产发布、不轮换外部站点密码（需账号 owner 操作）。
- 不把 `WAIVED / PARTIAL / BLOCKED / NOT_RUN / NOT_PROVEN / SEMI_AUTOMATIC` 折算为 PASS。
- 不降低既有测试断言；不以删除失败用例换取绿色。

## 5. 验收标准

1. `release_verdict.py --require-ga` 在 runtime `ga_ready=false`、产品 TC 非真实 PASS、
   provenance 不一致、生产阶段未执行、Ruleset 缺 AIQE check、Reviewer 无真实身份时均非零退出。
2. 产品 TC 配置无“无解释的 runner null”；`product-results.json` 只能由本次执行生成，
   静态 10/10 不再能让 Gate E PASS。
3. 每个 FIX 至少有一个正向 + 一个反向测试；测试可在 CI 重复执行。
4. `Audit Closure` 的 CLOSED 必须经过语义验证器；不满足的条目已降级为 EXTERNAL。
5. 最终报告明确 `RELEASE_CANDIDATE_BLOCKED` 与未完成项，不以 CI 绿色代替 GA。

## 6. 设计要点

- **状态单一事实源**：`scripts/aiqe/statuses.py`，只有 `PASS` 计入通过；
  `SEMI_AUTOMATIC/MANUAL/SCREENSHOT` → `PARTIAL`。
- **Gate 计算与事实读取分离**：`validators/` 纯函数读取原始 JSON/YAML 并返回 `GateCheck`；
  `release_verdict.py` 只组合结果，不再用“一个数字”替代逐条验证。
- **证据链**：product results → verify → Gate E；platform/runtime → provenance validator；
  production stage → Gate F；branch ruleset → Gate G；acceptance record → Gate acceptance。
- **失败语义**：缺失/冲突/过期 = `NOT_PROVEN`；已执行失败 = `FAIL`；
  环境/Runner 不可用 = `BLOCKED`；部分覆盖 = `PARTIAL`；豁免 = `WAIVED`（不计 PASS）。

## 7. 风险与缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| 无 staging/Secret，产品 TC 只能 BLOCKED | GA 无法签署 | 如实报告，给 owner/unblock_action，不伪造 PASS |
| 70 条 acceptance 无 GitHub 身份 | Gate B–G acceptance PENDING | 保留历史记录，GA 模式拒绝；新 PR 由真实 Reviewer 审批 |
| Ruleset 新增 required check 可能阻塞后续 PR | 交付阻塞 | 先合并含 Aggregate Job 的 PR，再更新 Ruleset；Job 失败即修复 |
| Agent/Benchmark 改动影响既有测试 | 回归风险 | 只做验证加固、保持默认行为兼容；全量 AIQE 回归 |
| 生产阶段证据修正引发文档冲突 | 审计误判 | 保留原始 stage 文件，新增 normalization 说明与机器判定 |
