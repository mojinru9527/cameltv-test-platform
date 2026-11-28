# V1.6.2 Hardening — Post-Merge Runbook

> PR: [#642](https://github.com/mojinru9527/cameltv-test-platform/pull/642) — **已合并**
> Main SHA：`c6b150f141b8a48f744c9ef1ee17410f455289a5`（2026-11-28 squash）
> 当前状态：代码已合并、Ruleset 已启用 AIQE 聚合门禁；本 PR 刷新 Main SHA 证据并准备 hardening Pre-release。

## 1. 合并（squash）— 已完成

```powershell
gh pr merge 642 --squash --delete-branch   # 已完成，merge commit c6b150f14
```

## 2. Main Ruleset 增加 AIQE Aggregate Gate — 已完成

```powershell
python scripts/aiqe/update_branch_protection.py `
  --reviewer-login MoojinR --ensure-required-checks --apply
python scripts/aiqe/check_branch_protection.py --capture
python scripts/aiqe/check_branch_protection.py --check
```

线上 `protect-main (#18351498)` required checks 现为 4 个（含 `AIQE V1.6 Governance Gate`，
integration_id=15368），`check_branch_protection.py --check` 通过。

## 3. 在 Main SHA 上重跑证据

```powershell
$env:AIQE_EXPECTED_COMMIT = $MAIN_SHA
$env:AIQE_TESTED_COMMIT_SHA = $MAIN_SHA
python scripts/aiqe/run_product_tc.py --run            # 无环境时 10/10 BLOCKED，exit 2
python scripts/aiqe/verify_product_tc_results.py --expected-commit $MAIN_SHA
python scripts/aiqe/scan_credentials.py --output docs/aiqe/v1.6/evidence/credential-scan.json
python scripts/aiqe/release_verdict.py --write `
  --emit-markdown docs/aiqe/v1.6/V1.6-Release-Verdict.md `
  --emit-e2e-doc docs/aiqe/v1.6/E2E-Coverage-and-Blockers.md
python scripts/aiqe/check_audit_closure.py --check
python scripts/aiqe/build_v162_final_acceptance.py --write
python scripts/aiqe/build_evidence_manifest.py --commit-sha $MAIN_SHA --require-complete
python scripts/aiqe/check_release_audit.py
```

- 预期：`GA_NOT_READY` / `RELEASE_CANDIDATE_BLOCKED`；`--require-ga` exit 1。
- 只有 FIX-015 全部外部条件满足（产品 E2E 10/10、生产阶段/rollback、真实 review）
  才允许把 `release_status` 变为 `GA_SIGNED`。

## 4. 证据提交

证据文件变更通过独立 `chore(aiqe-v162): main SHA 证据快照` PR 合入；
不要直接 push main。PR 描述引用本 runbook 与 Evidence Manifest。

## 5. 发布（Hardening RC，不是 GA）

- 创建 annotated tag `v1.6.2-hardening`（**不要**用 `aiqe-v*`，避免触发 GA release-gate 的
  `--require-ga` 失败；GA tag 只在 `--require-ga` exit 0 后创建）。
- GitHub Release 标注 **Pre-release**，正文引用：
  - `docs/aiqe/v1.6/V1.6.2-Hardening-Final-Acceptance.md`
  - `docs/aiqe/v1.6/release-verdict.json`
  - `work-logs/evidence/aiqe-v162/README.md`
- 明确写出 `RELEASE_CANDIDATE_BLOCKED` 与未完成的外部项，不写 GA/10-10/PRODUCTION_DEPLOYED。

## 6. 回滚

- 代码：`git revert <merge_commit>` 走 PR。
- Ruleset：`update_branch_protection.py` 的 before/after 输出保存；如需回退，用 GitHub API
  恢复原 3 个 contexts（本次变更仅追加，不删除）。
- 证据：全部为新增/生成文件，无数据库迁移。

## 7. 后续 GA 条件（owner）

1. 隔离 Test 环境/Secret/Runner：产品 TC 10/10 真实 PASS。
2. 生产 Shadow/Dogfood/5%/50% 或正式 WAIVED + Rollback Drill 原始证据。
3. 70 条 acceptance 记录绑定真实 GitHub review id/user id/当前 SHA（MoojinR）。
4. Main Ruleset 生效并快照。
5. 最终 Main/Release SHA 上 `release_verdict.py --require-ga` exit 0。
