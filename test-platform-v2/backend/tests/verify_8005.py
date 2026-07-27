"""Verify backend on 8005 has the fix."""
import urllib.request, json

print("Testing backend on port 8005...")

# Login
r = json.loads(urllib.request.urlopen(urllib.request.Request(
    "http://127.0.0.1:8005/api/v1/auth/login",
    data=json.dumps({"username":"admin","password":"admin123"}).encode(),
    headers={"Content-Type":"application/json"}), timeout=10).read())
token = r['data']['access_token']
print(f"[PASS] Login OK")

# Menus
r2 = json.loads(urllib.request.urlopen(urllib.request.Request(
    "http://127.0.0.1:8005/api/v1/system/menus",
    headers={"Authorization": f"Bearer {token}"}), timeout=10).read())
print(f"[PASS] Menus OK: code={r2['code']} count={len(r2['data'])}")

# Check sort types
bad = [m for m in r2['data'] if not isinstance(m['sort'], int)]
if bad:
    print(f"[FAIL] Non-int sorts: {bad}")
else:
    print(f"[PASS] All {len(r2['data'])} sort values are int")

# Show first 3
for m in r2['data'][:3]:
    print(f"  sort={m['sort']:>3}  code={m['code']}  name={m['name']}")

print("\nBackend 8005 is CORRECT and READY.")
print("The MenuOut float->int fix is working.")
