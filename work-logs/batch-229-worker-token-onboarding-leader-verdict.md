# Batch 229 - Leader Verdict

> Leader | Date: 2026-09-04 | Decision: Conditional pass (pending total confirmation, required checks and final PR audit)

## Review Summary

| Dimension | Result | Notes |
|-----------|--------|-------|
| Implementation | Pass | Reuses Token hash/lifecycle; no schema, credential table or dependency added |
| Security | Pass | Least privilege scope; CI Token rejected; disabled Token rejected; no secret evidence |
| User workflow | Pass | Runtime -> preselected creation -> one-time setup -> disable/delete is browser-proven |
| Regression | Pass | Backend 2425, frontend 629, focused 67, migrations 8, route guards 4 |
| Production claim | Pass | Reports explicitly avoid claiming a local fixture means production Worker online |

## Approved Decisions

1. Worker heartbeat uses existing API Tokens with the single `workers:register` scope; browser JWT is not a machine credential.
2. `WORKER_KEY` remains the stable node identifier, while `API_TOKEN` is the revocable credential.
3. Runtime links authorized admins to `/system?tab=tokens&purpose=worker`; read-only users see contact-admin guidance.
4. The creation success dialog is the only place that exposes the plain Token and startup setup; close clears it.
5. Copied Bash setup exports both variables before starting the Worker.
6. Mobile/tablet System tabs wrap with 44px targets, and header labels remain icon-only below `lg` to prevent overlap.

## Spot Checks

- `workflows.py:33-38`, `service.py:79-87`, `token_service.py:43-51`: auth, scope and usage update.
- `runtime/index.tsx:144-152`, `TokensTab.tsx:187-292`: discoverability, purpose, one-time result and revoke wording.
- `system/index.tsx:43-59`: permission-aware deep link and responsive tabs.
- `start-worker.sh:27-32`: empty Token fails before either child process starts.
- `work-logs/evidence/batch-229-worker-token-onboarding/`: safe browser, network and regression evidence.

## Verdict

The local implementation and critical browser path pass. Merge remains blocked until all three delivery conditions are satisfied:

1. User provides the exact one-time confirmation covering push of `fix/batch-229-worker-token-onboarding`, Draft PR creation and merge after checks.
2. Required checks on the Draft PR are green.
3. Final `audit-ai-pr.ps1 -RequireSuccessfulChecks` succeeds.

After those conditions, Leader may change this verdict to APPROVED, mark the PR Ready and squash merge to `main`. Production deployment and sports acceptance are outside this batch.

## Next-Batch Conditions

- No new C condition. C227-2 stays Deferred; this batch resolves only the Worker credential subproblem and does not close the external production prerequisites.

## Knowledge Audit

- New reusable pattern: a copied setup is not valid until environment propagation is proven; plain shell assignments on separate lines are insufficient for child processes.
- The pattern is captured in `tokenPurposes.test.ts`, the Runbook, QA report and browser evidence. No knowledge-ingest tool is available in this session.
- No conflict was found with existing C conditions or Runtime architecture.

## Process Feedback

| Finding | Action | Location |
|---------|--------|----------|
| Static UI tests missed unexported shell variables | Added executable-semantics assertions and browser verification | `tokenPurposes.test.ts`, E229-02 |
| Class-name tests passed while parent height still overlapped content | Required box metrics and screenshot iteration | `system/index.tsx`, E229-04 |
| No Agent Team template change is required | No skill/CHANGELOG modification | This verdict |

## Retro Card

| Planned vs actual | Defects (P0/P1/P2/P3) | Rework | Root cause | Next prevention |
|-------------------|-------------------------|--------|------------|-----------------|
| 4.5h / about 3.5h | 0/5/2/0 | 3 | Technical debt + missing executable/browser contract | Treat generated configuration and responsive parent geometry as acceptance contracts |

**Skills used**: Agent Team defined the artifacts/gates; Bug Guard guided auth and process checks; UI conventions drove responsive fixes; Playwright CLI supplied real frontend evidence.
