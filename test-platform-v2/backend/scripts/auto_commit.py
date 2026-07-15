"""Auto-commit and push all 2026-07-13 changes."""
import subprocess, sys, os

os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

files = [
    "test-platform-v2/backend/app/api/v1/apitest.py",
    "test-platform-v2/backend/tests/playwright/specs/production-smoke.spec.ts",
    "test-platform-v2/backend/tests/api_production_smoke.py",
    "test-platform-v2/backend/scripts/ingest_prod_results.py",
    "test-platform-v2/backend/scripts/check_status.py",
    "test-platform-v2/backend/storage/prod-api-results.json",
    "test-platform-v2/backend/storage/prod-service-endpoints.json",
    "test-platform-v2/backend/storage/production-test-report-20260713.json",
]

def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(r.stdout)
    if r.stderr:
        print(r.stderr, file=sys.stderr)
    return r.returncode

print("=== git add ===")
run(f"git add {' '.join(files)}")

print("=== git status ===")
run("git status --short")

msg = (
    "feat(apitest/uitest/wiki): production testing + P1 fix + wiki activation\n\n"
    "P1 Fix: apitest.py create_task missing BackgroundTasks param -> 500\n"
    "UI Tests: 5/5 Playwright tests PASSED on camel1.tv\n"
    "API: 200 endpoints discovered across 7 microservices\n"
    "KB: 4 sources, 27 chunks ingested (production + Lanhu)\n"
    "Wiki: 4 pages generated from Lanhu doc (52K chars, app+pc+web)\n"
    "Scripts: ingest_prod_results.py, check_status.py, auto_commit.py\n"
)

print("=== git commit ===")
code = run(f'git commit -m "{msg}"')
if code != 0:
    print("[FAIL] commit failed")
    sys.exit(code)

print("=== git push ===")
code = run("git push origin feature/apitest-uitest-realization")
if code != 0:
    print("[FAIL] push failed")
    sys.exit(code)

print("[DONE] Committed and pushed successfully")
