"""Quick proxy chain verification."""
import urllib.request
import json

def post(url, data):
    req = urllib.request.Request(url, data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=10).read())

def get(url, token):
    req = urllib.request.Request(url,
        headers={"Authorization": f"Bearer {token}"})
    return json.loads(urllib.request.urlopen(req, timeout=10).read())

# Test 1: Direct backend login
print("1. Backend direct login (8002)...")
r1 = post("http://localhost:8002/api/v1/auth/login", {"username":"admin","password":"admin123"})
print(f"   OK code={r1['code']} user={r1['data']['user']['username']}")
token = r1['data']['access_token']

# Test 2: Direct backend menus
print("2. Backend direct menus (8002)...")
r2 = get("http://localhost:8002/api/v1/system/menus", token)
print(f"   OK code={r2['code']} menus={len(r2['data'])}")

# Test 3: Proxy login
print("3. Vite proxy login (5173)...")
r3 = post("http://localhost:5173/api/v1/auth/login", {"username":"admin","password":"admin123"})
print(f"   OK code={r3['code']} user={r3['data']['user']['username']}")
proxy_token = r3['data']['access_token']

# Test 4: Proxy menus
print("4. Vite proxy menus (5173)...")
r4 = get("http://localhost:5173/api/v1/system/menus", proxy_token)
print(f"   OK code={r4['code']} menus={len(r4['data'])}")

# Show first 5 menus
for m in r4['data'][:5]:
    print(f"   sort={m['sort']} ({type(m['sort']).__name__}) code={m['code']} name={m['name']}")

print("\n✅ ALL TESTS PASSED — Proxy chain working!")
