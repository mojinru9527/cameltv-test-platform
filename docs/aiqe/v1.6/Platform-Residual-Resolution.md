# V1.6 平台级遗留项处理结论

> 2026-11-21；基于当前 traceability 与本机测试证据。产品级 TC-002/004/008/010 按用户意见暂跳过。

| 项 | 结论 | 证据 / 说明 |
|---|---|---|
| V16-002-R2 出口代理 | **VERIFIED** | `tests/test_aiqe_v16_002_playwright_interception.py` 11 passed；真实 Chromium + 出口代理；容器级 egress 仍由 V16-024 跟踪 |
| V16-003-R4 外部 Secret Store/KMS | **IMPLEMENTED（不冒充 VERIFIED）** | `tests/test_aiqe_v16_003_external_secret_store.py` 7 passed；真实 AWS 账号/IAM/KMS 未演练 |
| V16-017-R1 平台链路 E2E | **VERIFIED（10/10）** | `test_v16_017_platform_chain.py` 9 passed + `test_v16_017_tc001_contract.py` 1 passed |
| V16-017-R2 产品级 10/10 | **BLOCKED** | 当前产品 TC 7/10；TC-004 PARTIAL，TC-008/010 按用户意见跳过；原“管理员锁”阻塞描述已过期 |
| V16-024-R3 灰度/备份/监控 | **PARTIAL** | 本地 SQLite drill 3 passed；staging PostgreSQL、Shadow/狗粮/小流量、Prometheus、云 KMS 仍 NOT_RUN |
| V16-025-R1 工程治理门禁 | **VERIFIED** | `.github/workflows/aiqe-v16-gates.yml`、CODEOWNERS、PR 模板字段、evidence-index 生成器均存在；traceability/release audit 测试 11 passed |

## 仍需外部条件

- V16-003-R4：真实 AWS Secrets Manager + KMS + IAM/staging 凭证；
- V16-024-R3：staging/生产同构 PostgreSQL、Prometheus/告警栈、云 KMS；
- V16-017-R2：TC-002/004 产品链路，以及 TC-008/010（用户已要求跳过）。
