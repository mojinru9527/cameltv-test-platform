"""Final proxy chain verification."""
import urllib.request, json

PROXY = "http://localhost:5173"

# 1. Login through proxy
print("1. Proxy login...")
r = json.loads(urllib.request.urlopen(urllib.request.Request(
    f"{PROXY}/api/v1/auth/login",
    data=json.dumps({"username":"admin","password":"admin123"}).encode(),
    headers={"Content-Type":"application/json"}), timeout=10).read())
assert r['code'] == 0, f"Login failed: {r}"
token = r['data']['access_token']
print(f"   [PASS] Login OK, token={token[:20]}...")

# 2. Menus through proxy
print("2. Proxy menus...")
r2 = json.loads(urllib.request.urlopen(urllib.request.Request(
    f"{PROXY}/api/v1/system/menus",
    headers={"Authorization": f"Bearer {token}"}), timeout=10).read())
assert r2['code'] == 0, f"Menus failed: {r2}"
print(f"   [PASS] Menus OK, count={len(r2['data'])}")

# 3. Verify sort types
bad = [m for m in r2['data'] if not isinstance(m['sort'], int)]
assert len(bad) == 0, f"Non-int sorts: {bad}"
print(f"   [PASS] All {len(r2['data'])} sort values are int")

# 4. Favicon
print("3. Favicon...")
req = urllib.request.Request(f"{PROXY}/favicon.svg")
resp = urllib.request.urlopen(req, timeout=5)
assert resp.status == 200, f"Favicon status: {resp.status}"
content = resp.read().decode()
assert content.startswith("<svg"), "Not SVG"
print(f"   [PASS] Favicon 200 OK, SVG valid")

# 5. HTML has favicon link
print("4. HTML favicon link...")
html = urllib.request.urlopen(f"{PROXY}/", timeout=5).read().decode()
assert 'favicon.svg' in html, "No favicon link in HTML"
print("   [PASS] HTML has favicon.svg link")

# 6. Direct backend check
print("5. Backend direct...")
r3 = json.loads(urllib.request.urlopen(urllib.request.Request(
    "http://localhost:8001/docs"), timeout=5).read() or "{}")
print("   [PASS] Backend docs accessible")

print("\n===== ALL CHECKS PASSED =====")
print("Ready for browser verification at http://localhost:5173")
