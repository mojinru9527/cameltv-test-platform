# Production Capacity Guard - QA Report

Date: 2026-09-07 | Executor: codex
Verdict: PASS for local implementation; production rollout NOT EXECUTED.
Base: 8f6599bb (origin/main at worktree creation, Batch 232 / PR 414).

## Executed checks

| Check | Exit | Result |
|---|---:|---|
| `python -m unittest discover -s deploy/release-console/tests -v` | 0 | 21 passed; evidence/unittest.txt |
| `pwsh -NoProfile -File scripts/ops/test-capacity.ps1` | 0 | Structured argument transport, shell isolation, successful admission, four fail-closed rejection paths |
| `ruff check deploy/release-console/capacity.py deploy/release-console/release_cleanup.py deploy/release-console/tencent_executor.py deploy/release-console/tests --select F` | 0 | No undefined/unused Python symbols |
| `python -m compileall -q deploy/release-console` | 0 | Python syntax passes |
| PowerShell `Parser.ParseFile` for scripts/ops/release.ps1 | 0 | No parse errors |
| PyYAML safe_load of ai-delivery-policy.yml | 0 | Parsed |
| `python -m pytest deploy/release-control/tests -q` with PYTHONPATH=deploy/release-control/src | 0 | Entire adjacent deployment-domain suite: 27 passed |
| `python scripts/ci/test_classify_ci_changes.py` | 0 | 10 passed |
| `git diff --cached --check` | 0 | No whitespace errors |
| `pwsh scripts/git/dev-gate.ps1 -SkipBackend -SkipFrontend` | 1 | Output PASS_WITH_WARN; HARD=0 / WARN=332; do not describe wrapper as exit 0 |
| `scan-common-bugs.ps1 -BaselinePath .../scan-main.json` | 0 | 332 -> 332, delta 0; no new warning files/categories or hard findings |

Initial red phase: test modules failed to import absent capacity/cleanup helpers
(exit 1), then implementation and additional behavioral tests passed. Apply
tests include an actual temporary-file removal while retaining a backup file;
Docker actions are mocked, and no test deletes production objects.

## Baseline and scope

The clean detached checkout F:/CamelTv-release-20260907-b232 is at the same
8f6599bb revision and has no dirty files. Scan baseline and branch inventories
are saved in evidence/production-capacity-guard/scan-{main,branch}.json.
Their warning file/count maps are identical; full-platform tests are not
claimed to pass. This batch changes only deploy/, scripts/ops/,
.github/workflows/ and work-logs/; these are neutral operations paths in the
current CI classifier (backend=false, frontend=false). No platform app,
frontend, schema, dependency lock or test-platform-v2/deploy file is changed.
Thus platform pytest/Vitest/typecheck/build are not applicable to this diff.
New release-console Python and PowerShell tests are explicitly added to the
delivery-policy workflow; existing CI did not run this separate console suite.
Remote required checks and PR audit have not run because push is not yet authorized.

## Production evidence (read-only)

- Preview JSON: evidence/production-capacity-guard/production-preview.json.
- Current/rollback pairs retained: release-20260907-0001 and release-20260906-0001.
- Candidates: backend/frontend tags release-20260905-0001 and release-20260905-0002.
- Archive candidates: backend/frontend tar pairs release-20260903-0001 and
  release-20260905-0001, total 2851748352 bytes (2.656 GiB).
- Upload admission invoked with 1425670656 archive bytes: exit 1 as expected;
  free=2745151488 and required=8589934592 bytes. No upload/load/restart followed.
- At 23:44 CST, disk remained 94% used / about 2.6 GiB available; RAM available
  2222 MiB, swap used 306 MiB. No production cleanup or runtime config applied.
- Six running container IDs unchanged from initial inventory. Backend, frontend,
  postgres, AITDE worker and Temporal report healthy. The API health endpoint
  `/api/v1/open/health` returns code=0, data.status=ok, version=2.3.0.
  `/health` at the public frontend returns SPA HTML and is not backend evidence.
- `flock` exists at /usr/bin/flock. Existing production release-console does
  not yet contain this patch; until upgraded, preview only.

## Findings and operational limits

1. P1: Free-disk objective of 8 GiB remains unmet. Shared image layers mean the
   four eligible tags have little unique space. Stopped legacy worker retains
   an approximately 5.319 GB unique old image; it is deliberately protected.
   Retirement needs its own explicit recovery evidence, or expand the disk.
2. P2: Current main's release.ps1 still reads digests before fresh buildx export.
   This pre-existing first-release issue is outside the capacity patch; the
   tests validate upload admission directly and do not claim a clean full
   production release has been executed.
3. Approximation: admission uses archive-size factors and a reserve, not an
   exact expansion bound. Custom containerd roots require matching inspection.
4. No rollback drill, image build, authenticated UI regression or production
   deletion was executed. Preserved image-pair presence is not a rollback drill.
5. The cleanup tool does not read pending deployments from the console DB;
   operators must pin those tags and pause out-of-band deployment before apply.

## Retro card

Planned: 2 hours implementation/QA, excluding gated rollout.
Actual: approximately 0.3 hours to local QA.
Defects: new-code P0=0, P1=0; operational P1=1 and known baseline P2=1 above.
Rework: 2 review rounds (apply-path tests and recent rebuild protection).
Root causes: capacity management debt, independent deployment tools.
Next prevention: always compare actual unique/shared image storage and measure
post-cleanup free space; never promise summed virtual image sizes as savings.
