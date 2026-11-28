# 产品 TC 证据状态：V1.6.1 历史，不得用于 V1.6.2 基线

**STATUS: HISTORICAL**

本目录下 2026-11-28 之前生成的 JSON/PNG 属于 **V1.6.1 基线**，用于当时的人工复测/演示，
**不是** `v1.6.2-hardening` 基线的产品级 PASS 证据。

V1.6.2 复审（FIX-001/FIX-007/FIX-008）确认：

- `TC-AIQE-009/multi-end.json` 把微信小程序 `SEMI_AUTOMATIC` 计入整体 `PASS`，
  且桌面/安卓仅截图为证、无业务断言；该结论已作废，当前整体状态为 **BLOCKED**。
- `TC-AIQE-008/remember-account.json` 是 `WWY-V5-006`（记住账号）单用例，
  **不能替代/关闭仍 FAIL 的 `WWY-V5-001`**；当前 TC-AIQE-008 无正式 Regression
  API + 固定 SHA + Comparison Snapshot，状态为 **BLOCKED**。
- 其余 `TC-AIQE-00x/*` 均为本地/现场执行或外部生产站点手工脚本产物，
  缺目标环境 provenance、真实 Runner execution 与基线绑定，状态为 **BLOCKED**。

当前唯一有效事实源：

- 配置：`docs/aiqe/v1.6/e2e/product-tc-config.yaml`（baseline `v1.6.2-hardening`）
- 结果：`docs/aiqe/v1.6/e2e/product-results.json`（本次生成，10/10 BLOCKED）
- 映射：`docs/adr/0032-aiqe-v16-product-tc-baseline-mapping.md`
- 判定：`docs/aiqe/v1.6/release-verdict.json`（Gate E NOT_PROVEN，GA 未签署）

禁止把上述历史文件复制进新基线的 product-results、验收记录或 GA 材料；
新基线 PASS 必须来自隔离 Test Runner 本次执行并附 Run/Job/Assertion/Artifact/SHA。
