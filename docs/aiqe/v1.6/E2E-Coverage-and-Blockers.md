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
| TC-AIQE-005 | 并发数据污染 | **PARTIAL** | TC-PLATFORM-011 | 产品级 E2E 证据未归档为机器产物；当前仅有平台链路/单元证据，按 V16-017 原验收口径计为 PARTIAL。 |
| TC-AIQE-006 | 上游第三方故障 | **PARTIAL** | TC-PLATFORM-012 | 产品级 E2E 证据未归档为机器产物；当前仅有平台链路/单元证据，按 V16-017 原验收口径计为 PARTIAL。 |
| TC-AIQE-007 | UI Runner 自身故障 | **PARTIAL** | — | 产品级 E2E 证据未归档为机器产物；当前仅有平台链路/单元证据，按 V16-017 原验收口径计为 PARTIAL。 |
| TC-AIQE-008 | 开发修复后点击回归 | **PARTIAL** | TC-PLATFORM-005 | 产品级 E2E 证据未归档为机器产物；当前仅有平台链路/单元证据，按 V16-017 原验收口径计为 PARTIAL。 |
| TC-AIQE-009 | 多端 AC 对照 | **PARTIAL** | — | 产品级 E2E 证据未归档为机器产物；当前仅有平台链路/单元证据，按 V16-017 原验收口径计为 PARTIAL。 |
| TC-AIQE-010 | 学习候选发布 | **PARTIAL** | — | 产品级 E2E 证据未归档为机器产物；当前仅有平台链路/单元证据，按 V16-017 原验收口径计为 PARTIAL。 |

**产品级 TC PASS：0/10。**

## 平台链路 TC（本地确定性 SUT，不是产品验收）

| TC | 状态 | Run ID | Job | NodeRun | Assertion | Artifact | 说明 |
|---|---|---|---|---|---|---|---|
| TC-PLATFORM-001 | **PASS** | 85b06644 | 1 | f15dd626 | ae13d189 | 9fe6bd5d,9493c8ff |  |
| TC-PLATFORM-002 | **PASS** | 905cdae4 | 1 | 3fcf0126 | 42980d36 | 728c45d6 |  |
| TC-PLATFORM-003 | **BLOCKED** | 4e1ef203 | 1 | 99d8a329 | d9ce8d38 | — | 策略阻断发生在断言执行前，无 AssertionResult（负向场景按 BLOCKED 记录） |
| TC-PLATFORM-004 | **NOT_RUN** | 2185d391 | 1 | 8f5f2faa | — | — | fencing 负向场景：迟到结果被拒绝，无完整 Run/Assertion 链路结果可计 PASS |
| TC-PLATFORM-005 | **PASS** | d239f2df | 2 | 7977b416 | 0f016e06 | e826ecde,3b00afb5 |  |
| TC-PLATFORM-006 | **PASS** | 9faa7812 | 1,2 | 34ef4cd4,639dc9d2 | ac462859,2fa06309 | 2f389112,6f9bfe36,e3dd7994,65a6f9be |  |
| TC-PLATFORM-007 | **PASS** | ec04f232 | 1 | 4762f7ea | 5dcca2b1 | 64a51b85,430484d8 |  |
| TC-PLATFORM-008 | **BLOCKED** | — | — | — | — | — | browser 节点由外部 Runner 执行；本用例覆盖 node_executor→PlaywrightDriver，未产生 TestRun，故不计入运行证据索引 PASS |
| TC-PLATFORM-009 | **NOT_RUN** | — | — | — | — | — | AgentTask 链路不产生 TestRun，无法计入需要 Run/Job/Assertion ID 的运行证据索引 |
| TC-PLATFORM-010 | **NOT_RUN** | — | — | — | — | — | Contract Service 平台行为测试，无 TestRun/UI/DB 链路，不能计为产品 TC-001 运行证据 |

- 平台结果文件：`docs\aiqe\v1.6\e2e\platform-results.json`（环境 `local-20261124`，机器产物含 Run/Job/Assertion/Artifact ID）。
- 平台链路 5 类负向/阻断场景按 BLOCKED/NOT_RUN 记录，不计入 PASS；它们不构成产品验收证据。
