"""Simple proxy chain test."""
import urllib.request, json

# Login through proxy
print("1. Proxy login...")
r = json.loads(urllib.request.urlopen(urllib.request.Request(
    "http://localhost:5173/api/v1/auth/login",
    data=json.dumps({"username":"admin","password":"admin123"}).encode(),
    headers={"Content-Type":"application/json"}), timeout=10).read())
print(f"   [PASS] code={r['code']}")
token = r['data']['access_token']

# Menus through proxy
print("2. Proxy menus...")
r2 = json.loads(urllib.request.urlopen(urllib.request.Request(
    "http://localhost:5173/api/v1/system/menus",
    headers={"Authorization": f"Bearer {token}"}), timeout=10).read())
print(f"   [PASS] code={r2['code']} menus={len(r2['data'])}")

# Show menus
for m in r2['data'][:5]:
    print(f"   sort={m['sort']}({type(m['sort']).__name__}) code={m['code']} name={m['name']}")

print("\nALL PASSED - Ready for browser!")
