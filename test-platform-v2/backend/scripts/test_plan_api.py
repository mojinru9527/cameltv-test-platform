"""Quick smoke test for test-plan APIs."""
import json
import urllib.request
import urllib.error

BASE = "http://localhost:8000/api/v1"
_token = None

def set_token(t):
    global _token
    _token = t

def req(method, path, data=None):
    url = f"{BASE}{path}"
    headers = {"Content-Type": "application/json"}
    if _token:
        headers["Authorization"] = f"Bearer {_token}"
        headers["X-Project-Id"] = "1"
    body = json.dumps(data).encode() if data else None
    r = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())

# 1. Login
print("=== Login ===")
r = req("POST", "/auth/login", {"username": "admin", "password": "admin123"})
set_token(r["data"]["access_token"])
print(f"  token: {_token[:20]}...")

# 2. Create Plan
print("\n=== Create Plan ===")
r = req("POST", "/test-plans", {"name": "Regression v1.0", "description": "First round regression", "status": "active"})
plan_id = r["data"]["id"]
print(f"  created plan #{plan_id}: {r['data']['name']}")

# 3. Add Cases
print("\n=== Add Cases ===")
r = req("POST", f"/test-plans/{plan_id}/cases", {"case_ids": [1, 2, 3, 4, 5]})
print(f"  added: {r['data']['added']}")

# 4. Execute cases
print("\n=== Execute Cases ===")
for pcase_id in [1, 2, 3]:
    status = "pass" if pcase_id != 3 else "fail"
    r = req("POST", f"/test-plans/{plan_id}/cases/{pcase_id}/execute", {"status": status, "notes": f"Test note {pcase_id}"})
    print(f"  pcase {pcase_id}: {r['data']['status']}")

# 5. Get Plan Detail
print("\n=== Plan Detail ===")
r = req("GET", f"/test-plans/{plan_id}")
d = r["data"]
print(f"  stats: {d['stats']}")
print(f"  cases: {len(d['cases'])}")
for c in d["cases"]:
    print(f"    - {c['case_title'][:30]}... [{c['last_status']}]")

# 6. List Plans
print("\n=== List Plans ===")
r = req("GET", "/test-plans")
print(f"  total: {r['data']['total']}")

# 7. Executions
print("\n=== Executions ===")
r = req("GET", f"/test-plans/{plan_id}/executions")
print(f"  total: {r['data']['total']}")

# 8. Delete Plan
print("\n=== Delete Plan ===")
r = req("DELETE", f"/test-plans/{plan_id}")
print(f"  deleted: {r['data']}")

print("\n[OK] All API tests passed!")
