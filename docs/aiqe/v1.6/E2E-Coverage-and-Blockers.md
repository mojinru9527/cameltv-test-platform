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
| TC-AIQE-007 | UI Runner 自身故障 | **PARTIAL** | TC-PLATFORM-004 | 产品级 E2E 证据未归档为机器产物；当前仅有平台链路/单元证据，按 V16-017 原验收口径计为 PARTIAL。 |
| TC-AIQE-008 | 开发修复后点击回归 | **PARTIAL** | TC-PLATFORM-005 | 产品级 E2E 证据未归档为机器产物；当前仅有平台链路/单元证据，按 V16-017 原验收口径计为 PARTIAL。 |
| TC-AIQE-009 | 多端 AC 对照 | **PARTIAL** | — | 产品级 E2E 证据未归档为机器产物；当前仅有平台链路/单元证据，按 V16-017 原验收口径计为 PARTIAL。<br>平台侧 E1–E6 实验已补终态收敛与结论记录断言（UNKNOWN 不得给已知根因结论）。 |
| TC-AIQE-010 | 学习候选发布 | **PARTIAL** | — | 产品级 E2E 证据未归档为机器产物；当前仅有平台链路/单元证据，按 V16-017 原验收口径计为 PARTIAL。 |

**产品级 TC PASS：0/10。**

## 平台链路 TC（本地确定性 SUT，不是产品验收）

| TC | 状态 | Run ID | Job | NodeRun | Assertion | Artifact | 说明 |
|---|---|---|---|---|---|---|---|
| TC-PLATFORM-001 | **PASS** | 3208dd1f | 1 | cf32a48d | c051ae9c | 64f22d24,c7419f33 |  |
| TC-PLATFORM-002 | **PASS** | e77cb3fb | 1 | b2383615 | aec4585a | 35f02c2e |  |
| TC-PLATFORM-003 | **BLOCKED** | da7a6f50 | 1 | c7a6a388 | 97d39757 | — | 策略阻断发生在断言执行前，无 AssertionResult（负向场景按 BLOCKED 记录） |
| TC-PLATFORM-004 | **PASS** | 996ab69d | 1,2 | 3ba2216a | 5bbcd8b2 | 023e5cbe,b33c7bc1 |  |
| TC-PLATFORM-005 | **PASS** | aa0483d4 | 2 | 743b46e0 | 60d0e8b7 | 693c4293,79f6adb5 |  |
| TC-PLATFORM-006 | **PASS** | 9f83264a | 2,1 | 64c1e584,5a90546a | 28d4d5f0,9dadbb76 | 26a364d4,ab754555,de4e08bf,4e84de2a |  |
| TC-PLATFORM-007 | **PASS** | aadefa82 | 1 | dc8ab5e0 | ada514e4 | 654811a5,340c34fc |  |
| TC-PLATFORM-008 | **BLOCKED** | — | — | — | — | — | browser 节点由外部 Runner 执行；本用例覆盖 node_executor→PlaywrightDriver，未产生 TestRun，故不计入运行证据索引 PASS |
| TC-PLATFORM-009 | **NOT_RUN** | — | — | — | — | — | AgentTask 链路不产生 TestRun，无法计入需要 Run/Job/Assertion ID 的运行证据索引 |
| TC-PLATFORM-010 | **NOT_RUN** | — | — | — | — | — | Contract Service 平台行为测试，无 TestRun/UI/DB 链路，不能计为产品 TC-001 运行证据 |

- 平台结果文件：`docs\aiqe\v1.6\e2e\platform-results.json`（环境 `local-20261124`，机器产物含 Run/Job/Assertion/Artifact ID）。
- 平台链路 5 类负向/阻断场景按 BLOCKED/NOT_RUN 记录，不计入 PASS；它们不构成产品验收证据。
