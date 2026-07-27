"""QA Verification Script — tests all 3 bug fixes against live services."""
import urllib.request
import json
import sys

BASE = "http://localhost:8001"
FRONTEND = "http://localhost:5173"
passed = 0
failed = 0

def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✅ {name}: PASS {detail}")
    else:
        failed += 1
        print(f"  ❌ {name}: FAIL {detail}")

# ── Test 1: Login ──
print("\n═══ Test 1: Login API ═══")
data = json.dumps({"username": "admin", "password": "admin123"}).encode()
req = urllib.request.Request(f"{BASE}/api/v1/auth/login", data=data,
    headers={"Content-Type": "application/json"})
resp = json.loads(urllib.request.urlopen(req).read())
token = resp["data"]["token"]
check("Login returns token", bool(token), f"token={token[:20]}...")
check("Login code=0", resp["code"] == 0, f"code={resp['code']}")

# ── Test 2: Menus endpoint (was 500) ──
print("\n═══ Test 2: Menus API (Bug Fix: 500 → 200) ═══")
try:
    req2 = urllib.request.Request(f"{BASE}/api/v1/system/menus",
        headers={"Authorization": f"Bearer {token}"})
    resp2 = json.loads(urllib.request.urlopen(req2).read())
    menus = resp2["data"]
    check("HTTP 200 (was 500)", resp2["code"] == 0, f"code={resp2['code']}")
    check("Menu count > 0", len(menus) > 0, f"count={len(menus)}")

    # Check sort values are int (not float — the core bug)
    float_sorts = [m for m in menus if isinstance(m["sort"], float)]
    check("All sort values are int (not float)", len(float_sorts) == 0,
          f"float_count={len(float_sorts)}")

    # Print first 5
    for m in menus[:5]:
        print(f"     sort={m['sort']} ({type(m['sort']).__name__}) code={m['code']}")
except Exception as e:
    check("Menus endpoint", False, str(e))

# ── Test 3: Favicon (was 404) ──
print("\n═══ Test 3: Favicon (Bug Fix: 404 → 200) ═══")
try:
    req3 = urllib.request.Request(f"{FRONTEND}/favicon.svg")
    resp3 = urllib.request.urlopen(req3)
    content = resp3.read().decode()
    check("HTTP 200 (was 404)", resp3.status == 200, f"status={resp3.status}")
    check("Content is SVG", content.startswith("<svg"), "SVG detected")
    check("Contains CT text", "CT</text>" in content, "brand text present")
    check("Content-Type is image/svg+xml",
          resp3.headers.get("Content-Type", "").startswith("image/svg+xml"),
          resp3.headers.get("Content-Type", "unknown"))
except Exception as e:
    check("Favicon endpoint", False, str(e))

# ── Test 4: CSS selector fix (data-sidebar) ──
print("\n═══ Test 4: CSS Sidebar Selectors (Bug Fix: root→sidebar) ═══")
try:
    # Get the main page, find CSS asset URLs
    req4 = urllib.request.Request(f"{FRONTEND}/")
    html = urllib.request.urlopen(req4).read().decode()
    check("Frontend page loads", "<!doctype html>" in html.lower(), "HTML served")

    # Find CSS file references in HTML
    import re
    css_files = re.findall(r'href="(/assets/[^"]+\.css)"', html)
    check("CSS assets found in HTML", len(css_files) > 0, f"count={len(css_files)}")

    # Check each CSS file for sidebar selectors
    root_refs = 0
    sidebar_refs = 0
    for css_file in css_files[:3]:
        try:
            css_req = urllib.request.Request(f"{FRONTEND}{css_file}")
            css_content = urllib.request.urlopen(css_req).read().decode()
            root_refs += css_content.count('[data-sidebar="root"]')
            sidebar_refs += css_content.count('[data-sidebar="sidebar"]')
        except:
            pass

    check("No [data-sidebar='root'] in CSS (was 5)", root_refs == 0,
          f"root_refs={root_refs}")
    check("[data-sidebar='sidebar'] present in CSS", sidebar_refs > 0,
          f"sidebar_refs={sidebar_refs}")
except Exception as e:
    check("CSS check", False, str(e))

# ── Test 5: Full API smoke test ──
print("\n═══ Test 5: API Smoke Test ═══")
endpoints = [
    ("GET", "/api/v1/system/users", "Users list"),
    ("GET", "/api/v1/system/roles", "Roles list"),
    ("GET", "/api/v1/system/permissions", "Permissions list"),
]
for method, path, label in endpoints:
    try:
        req = urllib.request.Request(f"{BASE}{path}",
            headers={"Authorization": f"Bearer {token}"})
        resp = json.loads(urllib.request.urlopen(req).read())
        check(f"{label} ({path})", resp["code"] == 0, f"code={resp['code']}")
    except Exception as e:
        check(f"{label} ({path})", False, str(e)[:80])

# ── Summary ──
print(f"\n{'='*50}")
print(f"RESULTS: {passed} passed, {failed} failed, {passed+failed} total")
if failed == 0:
    print("VERDICT: ✅ ALL TESTS PASSED — Ready for delivery")
else:
    print(f"VERDICT: ❌ {failed} FAILURES — Needs fixes before delivery")
print(f"{'='*50}")
sys.exit(0 if failed == 0 else 1)
