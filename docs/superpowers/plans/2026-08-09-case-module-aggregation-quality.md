# Batch 130 Case Module Aggregation and Adversarial Quality — Implementation Plan

> Executor: Codex. Work only in `F:/CamelTv-worktrees/codex-batch-130-case-module-quality`. Follow tests-first for behavior changes and do not push before the Agent Team total confirmation.

**Goal:** Aggregate test cases by real functional module, preserve terminal scope as metadata, make abnormal scenarios directly reviewable, and make the 7,803-case sports asset safely importable and auditable.

**Architecture:** A pure backend taxonomy normalizer is the single source for taxonomy rendering, normalized list filtering, and import canonicalization. Historical stored values remain intact; new Batch 125/130 imports use canonical surface-qualified domains and terminal tags. A deterministic adversarial overlay and audit script close recovery/idempotency gaps without regenerating thousands of cases.

**Stack:** FastAPI, SQLAlchemy, Pydantic, React/TypeScript, Vitest, pytest, PowerShell/Python delivery scripts.

---

## Task 1: Lock taxonomy normalization with failing tests

**Files:**
- Create: `test-platform-v2/backend/app/services/test_case_taxonomy.py`
- Modify: `test-platform-v2/backend/tests/test_testcase.py`

1. Add parameterized tests for Batch 110/122/125 domain/module variants, including PC/Web/mobile suffixes and duplicate path prefixes.
2. Assert the canonical tuple is `surface + functional domain + functional subpath` and contains no terminal wrapper nodes.
3. Run `pytest tests/test_testcase.py -k taxonomy -q`; confirm the new tests fail before implementation.
4. Implement the smallest pure normalization functions and rerun until green.

## Task 2: Close taxonomy-to-list filtering contract

**Files:**
- Modify: `test-platform-v2/backend/app/services/test_case_service.py`
- Modify: `test-platform-v2/backend/app/api/v1/test_case.py`
- Modify: `test-platform-v2/backend/app/schemas/test_case.py`
- Modify: `test-platform-v2/backend/tests/test_testcase.py`

1. Add failing API tests for canonical parent/leaf filtering, exact `case_id`, `positive_negative`, surface filtering, pagination total, and soft-delete/project isolation.
2. Add query parameters `surface`, `taxonomy_domain`, `taxonomy_module`, `positive_negative`, and `case_id`.
3. Build taxonomy from normalized locations; select matching IDs once for normalized filters, then apply the ID set to list/count SQL statements.
4. Ensure module filter uses path-prefix semantics and taxonomy/list counts remain equal.
5. Run the focused backend tests.

## Task 3: Make normalized taxonomy and scenario type usable in the UI

**Files:**
- Modify: `test-platform-v2/frontend/src/api/testcase.ts`
- Modify: `test-platform-v2/frontend/src/pages/testcase/index.tsx`
- Modify: `test-platform-v2/frontend/src/pages/testcase/index.test.tsx`
- Modify: `test-platform-v2/frontend/src/pages/testcase/__tests__/caseListFormatters.test.ts`

1. Add failing component/API tests proving tree nodes send canonical filter parameters and scenario filtering sends `positive_negative`.
2. Replace raw domain/module filter state with surface/taxonomy-domain/taxonomy-module state.
3. Derive both selects from taxonomy, flatten nested module paths, and allow parent-node filtering.
4. Add the scenario Select and visible positive/negative/boundary table badge.
5. Run focused Vitest and verify no duplicate fetch dependency loop.

## Task 4: Repair stable IDs and exact import idempotency

**Files:**
- Modify: `test-platform-v2/backend/scripts/import_sports_cases.py`
- Create: `test-platform-v2/backend/tests/test_import_sports_cases.py`

1. Add failing tests for duplicate raw `TC-001` across modules, stable reruns, unrelated existing cases, existing exact IDs, terminal tags, and canonical domain/module output.
2. Derive a stable ID from collection module + raw identifier + case content; preserve existing globally unique `SP-*` IDs.
3. Pass collection module and case index into payload conversion; add terminal scope tags without duplicating records.
4. Use the exact `case_id` list filter for idempotency and validate response envelope before deciding skip/create.
5. Run mocked importer tests and `--dry-run` count assertions.

## Task 5: Add adversarial overlay and quality gate

**Files:**
- Create: `test-platform-v2/backend/scripts/build_sports_adversarial_overlay.py`
- Create: `test-platform-v2/backend/scripts/audit_sports_case_quality.py`
- Create: `test-platform-v2/backend/tests/test_sports_case_quality.py`
- Create: `test-platform-v2/work-logs/evidence/batch-130-case-module-quality/adversarial-case-overlay.json`
- Modify: `test-platform-v2/backend/scripts/consolidate_module_cases.py`
- Modify: `tests/test-case-standards/功能测试输出用例要求.md`

1. Add failing tests for all 38 module profiles, explicit UI/data/side-effect assertions, and coverage-gate failures.
2. Define one concrete primary action and risk class per business module; generate recovery and duplicate/concurrency cases with stable IDs.
3. Merge overlay cases and infer missing metadata only for the 244 historical deep cases; never rewrite their steps or expected results.
4. Audit positive/negative coverage, adversarial dimensions, required fields, stable IDs, wrapper-free taxonomy, and count conservation.
5. Regenerate the consolidated asset mechanically and save an audit JSON summary.

## Task 6: Sync contracts and execute QA

**Files:**
- Modify generated `test-platform-v2/frontend/src/types/api.d.ts` only through the locked generator.
- Create Batch 130 QA/evidence/Leader/retrospective work logs.

1. Initialize `lanhu-mcp`, then run focused tests.
2. Run backend F821, affected pytest, full pytest, Alembic single-head/import checks.
3. Run frontend focused/full Vitest, typecheck, build, and locked OpenAPI type generation drift check.
4. Run quality audit, consolidated dry-run, common-bug scan, C-condition audit, and repository-boundary checks.
5. Start isolated services on ports 8049/5219; walk desktop/tablet/mobile with Playwright and capture Network/console evidence.
6. Complete QA (P0-P3), Leader rubric/verdict, process back-write, and retrospective card.
7. Present exact files/tests/risks and ask the one total confirmation before any push.
