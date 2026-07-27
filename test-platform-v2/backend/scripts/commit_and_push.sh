#!/bin/bash
# Run this to commit and push all 2026-07-13 production test + wiki changes
set -e
cd "$(dirname "$0")/../../.."

echo "=== Staging files ==="
git add \
  test-platform-v2/backend/app/api/v1/apitest.py \
  test-platform-v2/backend/tests/playwright/specs/production-smoke.spec.ts \
  test-platform-v2/backend/tests/api_production_smoke.py \
  test-platform-v2/backend/scripts/ingest_prod_results.py \
  test-platform-v2/backend/scripts/check_status.py \
  test-platform-v2/backend/storage/prod-api-results.json \
  test-platform-v2/backend/storage/prod-service-endpoints.json \
  test-platform-v2/backend/storage/production-test-report-20260713.json

echo "=== Git status ==="
git status --short

echo ""
echo "=== Committing ==="
git commit -m @'
feat(apitest/uitest/wiki): production testing + P1 fix + wiki activation

== P1 Bug Fix ==
- apitest.py create_task: added missing BackgroundTasks parameter → fixes 500 error
  (task_worker polling was masking this real defect)

== Production Testing (www.camel1.tv) ==
- 5/5 Playwright UI tests PASSED (production-smoke.spec.ts)
  TC-PROD-001 homepage, TC-PROD-002 login, TC-PROD-003 interaction (622 elements),
  TC-PROD-004 API health (56 calls), TC-PROD-005 performance (6.1s load)
- API endpoint discovery: 200 microservice endpoints across 7 services
  (account/camel/payment/studio/search/konfi)
- API smoke tests (api_production_smoke.py) + endpoint catalog

== Knowledge Base + Wiki ==
- KB ingest: 4 sources, 27 chunks with production test data
- Lanhu import: 52,426 chars extracted, covers app+pc+web
- Wiki compilation: 4 pages generated (index/module/requirement/source)
- All RAG/Wiki/Graph flags activated via .env
- Embedding pending (model download blocked by HF, chunks ready for backfill)

== Scripts ==
- scripts/ingest_prod_results.py: batch ingest test results to KB
- scripts/check_status.py: verify wiki job, KB sources, RAG search
'@

echo ""
echo "=== Pushing ==="
git push origin feature/apitest-uitest-realization

echo ""
echo "=== DONE ==="
