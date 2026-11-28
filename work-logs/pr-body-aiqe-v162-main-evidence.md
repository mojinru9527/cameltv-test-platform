## AIQE V1.6.2 Hardening — Main SHA 证据刷新（PR #642 合并后）

- Issue / Requirement ID: V16-017 / V16-021 / V16-023 / V16-024 / V16-025
- base_sha: `c6b150f141b8a48f744c9ef1ee17410f455289a5`
- head_sha: `HEAD_SHA_PLACEHOLDER`
- 业务结果: 在合并后的 Main SHA 上重采产品 TC/凭据扫描/Ruleset/Release Verdict/Final Acceptance；产品 TC 仍 10/10 BLOCKED，GA_NOT_READY / RELEASE_CANDIDATE_BLOCKED；不宣称 GA。
- 正式入口: `python scripts/aiqe/run_product_tc.py --run`、`verify_product_tc_results.py`、`scan_credentials.py`、`check_branch_protection.py --capture`、`release_verdict.py --write`、`build_v162_final_acceptance.py --write`
- 调用链: Main SHA checkout → product TC Runner（无环境，写 BLOCKED）→ verify 写 verification → scan 当前 SHA → ruleset API capture → Gate A–G → evidence files。
- 真实组件与 Mock 边界: 真实 Git checkout / Ruleset GitHub API / 本地文件扫描；产品 TC 无隔离 Test 环境，全部 BLOCKED，不以历史证据替代。
- Reviewer 角色域: qa
- 证据: commit:HEAD_SHA_PLACEHOLDER；pytest:tests/test_aiqe_v162_release_verdict.py（13 passed）；artifact:docs/aiqe/v1.6/V1.6.2-Hardening-Final-Acceptance.md、docs/aiqe/v1.6/release-verdict.json、docs/aiqe/v1.6/e2e/product-results.json、docs/aiqe/v1.6/evidence/credential-scan.json、docs/aiqe/v1.6/governance/branch-protection.json、work-logs/evidence/aiqe-v162/README.md
- 变更范围：仅证据/文档 + 基线 SHA 引用；不修改运行时代码。
- 非目标：不签 GA；不伪造产品 PASS、生产阶段或 Reviewer 身份。

## 证据刷新命令

```powershell
$env:AIQE_TESTED_COMMIT_SHA = "c6b150f141b8a48f744c9ef1ee17410f455289a5"
python scripts/aiqe/run_product_tc.py --run          # 10/10 BLOCKED（预期，exit 2）
python scripts/aiqe/verify_product_tc_results.py --expected-commit c6b150f141b8a48f744c9ef1ee17410f455289a5
python scripts/aiqe/scan_credentials.py --output docs/aiqe/v1.6/evidence/credential-scan.json
python scripts/aiqe/check_branch_protection.py --capture
python scripts/aiqe/release_verdict.py --write --emit-markdown docs/aiqe/v1.6/V1.6-Release-Verdict.md --emit-e2e-doc docs/aiqe/v1.6/E2E-Coverage-and-Blockers.md
python scripts/aiqe/build_v162_final_acceptance.py --write
python scripts/aiqe/check_release_audit.py
python scripts/aiqe/check_audit_closure.py --check
```

- 结果：`release_status=RELEASE_CANDIDATE_BLOCKED`；`product-results.commit_sha=c6b150f14`；`scan_commit_sha=c6b150f14`；Ruleset 4 个 required checks 含 `AIQE V1.6 Governance Gate`。
- 合并后发布：`v1.6.2-hardening` Pre-release（不是 GA tag），见 `work-logs/aiqe-v162-post-merge-runbook.md`。
