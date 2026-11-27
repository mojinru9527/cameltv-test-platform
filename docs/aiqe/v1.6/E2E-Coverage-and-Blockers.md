# V1.6 E2E 覆盖与阻塞清单（机器生成）

> 本文件由 `python scripts/aiqe/release_verdict.py --emit-e2e-doc` 生成，**禁止手工编辑**。
> 产品级 TC（`TC-AIQE-*`）与平台链路 TC（`TC-PLATFORM-*`）是两个命名空间：
> 平台链路通过**不等于**产品 TC 通过；产品 TC 必须有真实业务环境 artifact。

## 产品级 TC（V16-017 原验收口径）

| TC | 标题 | 产品状态 | 平台映射 | 缺口 / 证据 |
|---|---|---|---|---|
| TC-AIQE-001 | 需求契约冻结 + 需求变更影响 | **PASS** | TC-PLATFORM-010 | 产品级 E2E 证据未归档为机器产物；当前仅有平台链路/单元证据，按 V16-017 原验收口径计为 PARTIAL。 |
| TC-AIQE-002 | 运营后台发布资讯 → 前端可查看（用户批准简化口径） | **PASS** | — | 产品级 E2E 证据未归档为机器产物；当前仅有平台链路/单元证据，按 V16-017 原验收口径计为 PARTIAL。 |
| TC-AIQE-003 | API 首次失败 + 重试成功 → 不得掩盖失败 | **PASS** | — | 产品级 E2E 证据未归档为机器产物；当前仅有平台链路/单元证据，按 V16-017 原验收口径计为 PARTIAL。 |
| TC-AIQE-004 | 广告/其他功能浮层造成交叉干扰 | **BLOCKED** | TC-PLATFORM-008 | 产品级 E2E 证据未归档为机器产物；当前仅有平台链路/单元证据，按 V16-017 原验收口径计为 PARTIAL。 |
| TC-AIQE-005 | 并发数据污染 | **PASS** | TC-PLATFORM-011 | 产品级 E2E 证据未归档为机器产物；当前仅有平台链路/单元证据，按 V16-017 原验收口径计为 PARTIAL。<br>平台侧已加入受控目标零请求断言（localhost 可到达但不在 allowlist → BLOCKED 且计数器 0）。 |
| TC-AIQE-006 | 上游第三方故障 | **PASS** | TC-PLATFORM-012 | 产品级 E2E 证据未归档为机器产物；当前仅有平台链路/单元证据，按 V16-017 原验收口径计为 PARTIAL。 |
| TC-AIQE-007 | UI Runner 自身故障 | **PASS** | TC-PLATFORM-004 | 产品级 E2E 证据未归档为机器产物；当前仅有平台链路/单元证据，按 V16-017 原验收口径计为 PARTIAL。 |
| TC-AIQE-008 | 开发修复后点击回归 | **PARTIAL** | TC-PLATFORM-005 | 产品级 E2E 证据未归档为机器产物；当前仅有平台链路/单元证据，按 V16-017 原验收口径计为 PARTIAL。 |
| TC-AIQE-009 | 多端 AC 对照 | **PASS** | — | 产品级 E2E 证据未归档为机器产物；当前仅有平台链路/单元证据，按 V16-017 原验收口径计为 PARTIAL。<br>平台侧 E1–E6 实验已补终态收敛与结论记录断言（UNKNOWN 不得给已知根因结论）。 |
| TC-AIQE-010 | 学习候选发布 | **PARTIAL** | TC-PLATFORM-009 | 产品级 E2E 证据未归档为机器产物；当前仅有平台链路/单元证据，按 V16-017 原验收口径计为 PARTIAL。<br>平台侧 A1–A6 Agent 全链路已跑通；产品级 Benchmark/激活仍以 live 现场记录为准（未归档）。 |

**产品级 TC PASS：7/10。**

## 平台链路 TC（本地确定性 SUT，不是产品验收）

| TC | 状态 | Run ID | Job | NodeRun | Assertion | Artifact | 说明 |
|---|---|---|---|---|---|---|---|
| TC-PLATFORM-001 | **PASS** | b8f401b0 | 1 | 61024738 | 1dcb5ade | ef09600f,209258a9 |  |
| TC-PLATFORM-002 | **PASS** | 4ea1bbe5 | 1 | 0940cf39 | b7a14f7e | 275033e7 |  |
| TC-PLATFORM-003 | **BLOCKED** | 5e16f3e1 | 1 | 0095d069 | 9ab1709c | — | 策略阻断发生在断言执行前，无 AssertionResult（负向场景按 BLOCKED 记录） |
| TC-PLATFORM-004 | **PASS** | ec687854 | 1,2 | 49675869 | 0ef23cf2 | a8ca96b1,8dec8587 |  |
| TC-PLATFORM-005 | **PASS** | 7b822554 | 2 | bcbb783d | 4c62b2eb | be77fb63,8d815f58 |  |
| TC-PLATFORM-006 | **PASS** | 6f70861f | 1,2 | 48c8de7b,336eb58c | 7023e89f,420d6cdc | 8e2b5c54,b795b382,e643b94e,7471e20a |  |
| TC-PLATFORM-007 | **PASS** | 8b261cc9 | 1 | 1f086685 | ab110219 | f9dce99b,4fc2348d |  |
| TC-PLATFORM-008 | **BLOCKED** | — | — | — | — | — | browser 节点由外部 Runner 执行；本用例覆盖 node_executor→PlaywrightDriver，未产生 TestRun，故不计入运行证据索引 PASS |
| TC-PLATFORM-009 | **PASS** | 950264bc | 1 | 27e762e5 | 0694e4c8 | 5d293100,38929159 |  |
| TC-PLATFORM-010 | **NOT_RUN** | — | — | — | — | — | Contract Service 平台行为测试，无 TestRun/UI/DB 链路，不能计为产品 TC-001 运行证据 |

- 平台结果文件：`docs/aiqe/v1.6/e2e/platform-results.json`（环境 `local-20261124`，机器产物含 Run/Job/Assertion/Artifact ID）。
- 平台链路 5 类负向/阻断场景按 BLOCKED/NOT_RUN 记录，不计入 PASS；它们不构成产品验收证据。
