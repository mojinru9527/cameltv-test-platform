# V1.6 E2E 覆盖与阻塞清单（V16-017）

> 已交付：平台链路真实 E2E（Launch → Worker → Driver → Assertion → Evidence），使用确定性本地 SUT（真实 HTTP 服务 + SQLite + 真实 Worker）。
> 未交付：CamelTv 真实业务租户/前端/小程序/原生端的 10/10 产品级 E2E；需隔离 Test 环境，见下表 BLOCKED。

## 已执行（`pytest tests/e2e/aiqe/test_v16_017_platform_chain.py`）

| TC | 场景 | 状态 | 证据 |
|---|---|---|---|
| TC-AIQE-002 | HTTP 200 但业务断言失败 | **PASS（平台链路）** | 节点 FAILED、断言 FAIL、Run 非 PASS |
| TC-AIQE-004 | DB 只读 + Query Registry | **PASS（平台链路）** | 真实 SQLite SELECT、db_row_count PASS |
| TC-AIQE-005 | SSRF / 云元数据 | **PASS（平台链路）** | 169.254.169.254 被 TargetPolicy 阻断（PORT_NOT_ALLOWED），零外呼 |
| TC-AIQE-007 | 迟到 fencing 结果 | **PASS（平台链路）** | STALE_LEASE skipped，节点未 PASS |

## BLOCKED（产品级，缺隔离 Test 环境）

| TC | 场景 | 阻塞原因 |
|---|---|---|
| TC-AIQE-001 | 跨系统 API→后台 UI→DB→前台 UI | 无真实业务租户/用户/后台与前台 UI；本地 fixture 不等同产品 |
| TC-AIQE-003 | Playwright 真实交互 + 安全拦截（产品 UI） | 无测试环境登录凭据/业务页面；安全拦截已由 V16-002 真实 Chromium 测试覆盖 |
| TC-AIQE-006 | Secret 全链路（产品登录 JWT） | 无真实测试租户登录链路；Secret 链路已由 V16-003 覆盖 |
| TC-AIQE-008 | 缺陷一键回归（真实缺陷/部署证明） | 无真实缺陷系统/部署证明/目标环境 |
| TC-AIQE-009 | Noise E1–E6（真实故障注入） | 无真实故障注入通道/生产同构环境 |
| TC-AIQE-010 | A0–A6 真实 Agent 执行（真实 LLM） | 无真实 LLM 凭据与业务上下文；Agent 链路已由 V16-013/019 注入执行验证 |

## 缺失环境清单（解除阻塞所需）

1. 隔离 Test 实例（前后端 + 数据库 + 真实登录账号），可清空/重置；
2. 测试租户业务数据构造权限；
3. 部署证明写入通道（真实 deploy SHA）；
4. 可控故障注入（网络/CPU/内存/第三方）；
5. 真实 LLM Key（A4/A5/A6）或明确的 offline Agent 替身审批策略；
6. 小程序/原生端拒绝：按 Platform-Support-Matrix 不纳入 V1.6 GA。

## 诚实结论

- 平台链路 E2E：**4/10 独立执行通过**（TC-002/004/005/007）。
- 产品级 E2E：**0/6 执行**（TC-001/003/006/008/009/010 BLOCKED），不得计入通过率，不得宣称 10/10。
- `V16-017` 状态：**PARTIAL**（R1）+ **BLOCKED**（R2）；解除条件见上。
