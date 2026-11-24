# V1.6 E2E 覆盖与阻塞清单（机器生成）

> 本文件由 `python scripts/aiqe/release_verdict.py --emit-e2e-doc` 生成，**禁止手工编辑**。
> 产品级 TC（`TC-AIQE-*`）与平台链路 TC（`TC-PLATFORM-*`）是两个命名空间：
> 平台链路通过**不等于**产品 TC 通过；产品 TC 必须有真实业务环境 artifact。

## 产品级 TC（V16-017 原验收口径）

| TC | 标题 | 产品状态 | 平台映射 | 缺口 / 证据 |
|---|---|---|---|---|
| TC-AIQE-001 | 需求契约冻结 + 需求变更影响 | **PARTIAL** | TC-PLATFORM-010 | 产品级 E2E 证据未归档为机器产物；当前仅有平台链路/单元证据，按 V16-017 原验收口径计为 PARTIAL。 |
| TC-AIQE-002 | 运营后台发布资讯 → 前端可查看（用户批准简化口径） | **PARTIAL** | — | 产品级 E2E 证据未归档为机器产物；当前仅有平台链路/单元证据，按 V16-017 原验收口径计为 PARTIAL。 |
| TC-AIQE-003 | API 首次失败 + 重试成功 → 不得掩盖失败 | **PARTIAL** | — | 产品级 E2E 证据未归档为机器产物；当前仅有平台链路/单元证据，按 V16-017 原验收口径计为 PARTIAL。 |
| TC-AIQE-004 | 广告/其他功能浮层造成交叉干扰 | **PARTIAL** | TC-PLATFORM-008 | 产品级 E2E 证据未归档为机器产物；当前仅有平台链路/单元证据，按 V16-017 原验收口径计为 PARTIAL。 |
| TC-AIQE-005 | 并发数据污染 | **PARTIAL** | TC-PLATFORM-011 | 产品级 E2E 证据未归档为机器产物；当前仅有平台链路/单元证据，按 V16-017 原验收口径计为 PARTIAL。<br>平台侧已加入受控目标零请求断言（localhost 可到达但不在 allowlist → BLOCKED 且计数器 0）。 |
| TC-AIQE-006 | 上游第三方故障 | **PARTIAL** | TC-PLATFORM-012 | 产品级 E2E 证据未归档为机器产物；当前仅有平台链路/单元证据，按 V16-017 原验收口径计为 PARTIAL。 |
| TC-AIQE-007 | UI Runner 自身故障 | **PARTIAL** | — | 产品级 E2E 证据未归档为机器产物；当前仅有平台链路/单元证据，按 V16-017 原验收口径计为 PARTIAL。 |
| TC-AIQE-008 | 开发修复后点击回归 | **PARTIAL** | TC-PLATFORM-005 | 产品级 E2E 证据未归档为机器产物；当前仅有平台链路/单元证据，按 V16-017 原验收口径计为 PARTIAL。 |
| TC-AIQE-009 | 多端 AC 对照 | **PARTIAL** | — | 产品级 E2E 证据未归档为机器产物；当前仅有平台链路/单元证据，按 V16-017 原验收口径计为 PARTIAL。<br>平台侧 E1–E6 实验已补终态收敛与结论记录断言（UNKNOWN 不得给已知根因结论）。 |
| TC-AIQE-010 | 学习候选发布 | **PARTIAL** | — | 产品级 E2E 证据未归档为机器产物；当前仅有平台链路/单元证据，按 V16-017 原验收口径计为 PARTIAL。 |

**产品级 TC PASS：0/10。**

## 平台链路 TC（本地确定性 SUT，不是产品验收）

| TC | 状态 | Run ID | Job | NodeRun | Assertion | Artifact | 说明 |
|---|---|---|---|---|---|---|---|
| TC-PLATFORM-001 | **PASS** | 6585ec6c | 1 | c8976379 | a857c1ac | abcb7216,a25bceea |  |
| TC-PLATFORM-002 | **PASS** | 18cc6186 | 1 | 5e9df473 | 14ede863 | 9f833be6 |  |
| TC-PLATFORM-003 | **BLOCKED** | 7be7b64f | 1 | d8eeb575 | 502a914f | — | 策略阻断发生在断言执行前，无 AssertionResult（负向场景按 BLOCKED 记录） |
| TC-PLATFORM-004 | **NOT_RUN** | cc399862 | 1 | f7cec312 | — | — | fencing 负向场景：迟到结果被拒绝，无完整 Run/Assertion 链路结果可计 PASS |
| TC-PLATFORM-005 | **PASS** | e7bfcccd | 2 | 03fa13ea | c32b4119 | f90e1a9e,d464621f |  |
| TC-PLATFORM-006 | **PASS** | 66b3fcd1 | 2,1 | 21a3e307,0e285474 | 35549bbf,5ed301f0 | bfe803dd,55e53b0b,4549afdc,891bc99c |  |
| TC-PLATFORM-007 | **PASS** | 2dc8ce1c | 1 | c480f959 | 365a29ff | 9c4ab1d4,5b422daa |  |
| TC-PLATFORM-008 | **BLOCKED** | — | — | — | — | — | browser 节点由外部 Runner 执行；本用例覆盖 node_executor→PlaywrightDriver，未产生 TestRun，故不计入运行证据索引 PASS |
| TC-PLATFORM-009 | **NOT_RUN** | — | — | — | — | — | AgentTask 链路不产生 TestRun，无法计入需要 Run/Job/Assertion ID 的运行证据索引 |
| TC-PLATFORM-010 | **NOT_RUN** | — | — | — | — | — | Contract Service 平台行为测试，无 TestRun/UI/DB 链路，不能计为产品 TC-001 运行证据 |

- 平台结果文件：`docs\aiqe\v1.6\e2e\platform-results.json`（环境 `local-20261124`，机器产物含 Run/Job/Assertion/Artifact ID）。
- 平台链路 5 类负向/阻断场景按 BLOCKED/NOT_RUN 记录，不计入 PASS；它们不构成产品验收证据。
