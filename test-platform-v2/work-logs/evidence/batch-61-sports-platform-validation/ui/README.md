# Batch 61 体育 UI R2 脱敏证据索引

## 当前状态

| 项目 | 值 |
| --- | --- |
| 日期 | `2026-08-01` |
| 基线 SHA | `174e002fbe53d75d49aaf09c269fac622a4c7c58` |
| 本地 security suite | `PASS 17/17` |
| sports Playwright 收集 | `38 tests in 9 files` |
| Test5 browser contexts | `0` |
| Test5/production requests | `0` |
| R2 UI 状态 | `23/23 BLOCKED` |

当前仅有本地 fail-closed 证据：缺少 `CAMELTV_TEST_DATA_JSON` 时首条用例抛出 `B61-BLOCKED:CAMELTV_TEST_DATA_JSON`，第二条未执行，且未打开 Test5。没有 trace、traffic JSON、HTML 或业务截图，因为这些文件若没有真实授权环境和稳定数据，只会形成不可接受的伪证据。

## 解阻后的证据要求

每条证据以 `TC-B61-UI-xxx` 开头，并包含完整代码/合同 SHA、环境、视口、浏览器、脱敏 correlation ID 和 DOM/API/data oracle 摘要。提交前扫描 URL、query、header、request/response body、trace、HTML、JSON、console、截图 OCR 可见文本和未知二进制；任一 Token、Cookie、密码、私钥、真实 PII 或 canary 命中均记 FAIL 且不持久化原始文件。

AI 仅可辅助元素定位，不得接收凭据、PII、原始流量或决定支付、退款、权益、余额是否正确。
