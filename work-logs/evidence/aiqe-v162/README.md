# AIQE V1.6.2 Hardening — Release Evidence Index（本地快照）

> 本目录是本批次在**本地**生成的支撑证据；最终发布证据以对应 commit 的 CI artifact
> （workflow `AIQE V1.6 交付门禁`）与 `evidence-manifest.json` 为准。
> 生成日期：2026-11-28 | 基线：`2d2f508d5d1fd452972e7af49d9b4f3bde2e7b01`

## 1. 机器判定

| 证据 | 路径 | 当前状态 |
|---|---|---|
| Release Verdict | `docs/aiqe/v1.6/release-verdict.json` / `V1.6-Release-Verdict.md` | `GA_NOT_READY` / `RELEASE_CANDIDATE_BLOCKED` |
| Final Acceptance | `docs/aiqe/v1.6/V1.6.2-Hardening-Final-Acceptance.md` | 机器生成，决策 BLOCKED |
| Product Results | `docs/aiqe/v1.6/e2e/product-results.json` | `BLOCKED=10`，`verification.verified=true` |
| Platform Results | `docs/aiqe/v1.6/e2e/platform-results.json` | 历史本地平台链路（非产品验收） |
| Audit Closure | `docs/aiqe/v1.6/governance/audit-closure.yaml` / `V1.6.1-Audit-Closure-Report.md` | 0 CLOSED / 19 EXTERNAL |
| Credential Scan | `docs/aiqe/v1.6/evidence/credential-scan.json` | `CLEAN`（potential=0 / weak=0） |
| Production Evidence | `docs/aiqe/v1.6/governance/production-evidence.json` | Gate F NOT_PROVEN |
| Branch Protection | `docs/aiqe/v1.6/governance/branch-protection.json` | 缺 AIQE Aggregate check（待合并后 apply） |
| Local Service Test (TC-010) | `work-logs/evidence/aiqe-v162/local-service-test/TC-AIQE-010/learning-benchmark.local-service-test.json` | `local_service_test`，`product_status=BLOCKED` |

## 2. 测试证据（本地）

- AIQE：`pytest tests -q -k aiqe` → 1516 passed。
- 后端全量：2854 passed / 43 skipped（修复 1 个顺序依赖后复跑）。
- 关键反向测试：RV-001～012、产品伪造 PASS/hash/SHA、双人审批、Gate F 跳过阶段、Audit CLOSED 仅路径。
- 这些结果由本地执行产生；CI 会在 PR head 上重跑并以 JUnit artifact 保存。

## 3. CI 应产出的最终附件

| Artifact | Workflow Job | 说明 |
|---|---|---|
| `aiqe-v16-governance` | Traceability Gate | matrix snapshot / verdict / e2e coverage / credential scan |
| `aiqe-v16-unit-and-runtime` | Unit / Integration Gate | JUnit + platform-results + evidence-index |
| `aiqe-v16-runtime-junit` | Runtime / Negative Security Gate | 负向安全 JUnit |
| `aiqe-v16-release-gate` | Release Gate | verdict + evidence manifest（release/tag） |
| `aiqe-v16-evidence-manifest` | AIQE V1.6 Governance Gate | manifest JSON/MD |

## 4. 未随本快照提交的外部证据

- 真实隔离 Test 产品 E2E（10/10 PASS）——BLOCKED。
- 生产 Shadow/Dogfood/5%/50%/Rollback Drill 原始观测——NOT_RUN/NOT_PROVEN。
- 真实 GitHub Reviewer 对最终 SHA 的 APPROVED review——PENDING。
- Main Ruleset 更新后的 API 快照——合并后采集。
- SBOM/镜像 digest 为已有历史证据（`docs/aiqe/v1.6/evidence/image-*`），不随本批次重建。

**结论：本索引不是 GA 证书。** 在 §4 全部完成并在最终 SHA 上重跑门禁前，
`release_status` 必须保持 `RELEASE_CANDIDATE_BLOCKED`。
