"""Debug the Vite proxy 500 error with detailed response."""
import urllib.request
import json

# Login through proxy to get token
print("Logging in through proxy...")
req1 = urllib.request.Request("http://localhost:5173/api/v1/auth/login",
    data=json.dumps({"username":"admin","password":"admin123"}).encode(),
    headers={"Content-Type": "application/json"})
r1 = json.loads(urllib.request.urlopen(req1, timeout=10).read())
token = r1['data']['access_token']
print(f"  Token OK: {token[:30]}...")

# Now try menus through proxy — capture full error
print("\nCalling menus through proxy...")
try:
    req2 = urllib.request.Request("http://localhost:5173/api/v1/system/menus",
        headers={"Authorization": f"Bearer {token}"})
    r2 = json.loads(urllib.request.urlopen(req2, timeout=10).read())
    print(f"  OK: code={r2['code']} menus={len(r2['data'])}")
except urllib.error.HTTPError as e:
    print(f"  HTTP {e.code}")
    body = e.read().decode()
    print(f"  Body: {body[:500]}")

# Also test: menus without auth header through proxy
print("\nMenus WITHOUT auth header (expect 401)...")
try:
    req3 = urllib.request.Request("http://localhost:5173/api/v1/system/menus")
    r3 = json.loads(urllib.request.urlopen(req3, timeout=10).read())
    print(f"  Unexpected OK: code={r3['code']}")
except urllib.error.HTTPError as e:
    print(f"  HTTP {e.code}: {e.read().decode()[:200]}")

# Also test: same token directly to backend
print("\nDirect backend call with same token...")
try:
    req4 = urllib.request.Request("http://localhost:8002/api/v1/system/menus",
        headers={"Authorization": f"Bearer {token}"})
    r4 = json.loads(urllib.request.urlopen(req4, timeout=10).read())
    print(f"  OK: code={r4['code']} menus={len(r4['data'])}")
except urllib.error.HTTPError as e:
    print(f"  HTTP {e.code}: {e.read().decode()[:200]}")
