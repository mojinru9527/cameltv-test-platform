"""Deep diagnosis: test every combination."""
import urllib.request, json

# Get a token from 8001
print("=== Get tokens ===")
r = json.loads(urllib.request.urlopen(urllib.request.Request(
    "http://localhost:8001/api/v1/auth/login",
    data=json.dumps({"username":"admin","password":"admin123"}).encode(),
    headers={"Content-Type":"application/json"}), timeout=10).read())
token_8001 = r['data']['access_token']
print(f"Token from 8001: {token_8001[:20]}...")

# Test: 8001 direct with its own token
print("\n=== 8001 direct ===")
try:
    r = json.loads(urllib.request.urlopen(urllib.request.Request(
        "http://localhost:8001/api/v1/system/menus",
        headers={"Authorization": f"Bearer {token_8001}"}), timeout=10).read())
    print(f"code={r['code']} menus={len(r['data'])}")
except urllib.error.HTTPError as e:
    body = e.read().decode()[:500]
    print(f"HTTP {e.code}: {body}")

# Test: proxy with same token
print("\n=== Proxy (5173) with SAME token ===")
try:
    r = json.loads(urllib.request.urlopen(urllib.request.Request(
        "http://localhost:5173/api/v1/system/menus",
        headers={"Authorization": f"Bearer {token_8001}"}), timeout=10).read())
    print(f"code={r['code']} menus={len(r['data'])}")
except urllib.error.HTTPError as e:
    body = e.read().decode()[:500]
    print(f"HTTP {e.code}: {body}")

# Test: what does the proxy send to the backend?
# Check Vite's proxy handling by testing a trivial GET endpoint through proxy
print("\n=== Proxy simple GET test ===")
try:
    r = urllib.request.urlopen("http://localhost:5173/api/v1/system/users",
        timeout=10)
    print(f"HTTP {r.status}")
except urllib.error.HTTPError as e:
    body = e.read().decode()[:300]
    print(f"HTTP {e.code}: {body}")

# Check which backend port proxy is hitting
# If it hits 8001, users should either work or return 401
# If it hits 8000, it returns 500 "Internal Server Error"
print("\n=== Port 8000 test (zombie) ===")
try:
    r = json.loads(urllib.request.urlopen(urllib.request.Request(
        "http://localhost:8000/api/v1/system/menus",
        headers={"Authorization": f"Bearer {token_8001}"}), timeout=10).read())
    print(f"code={r['code']} menus={len(r.get('data',[]))}")
except urllib.error.HTTPError as e:
    body = e.read().decode()[:300]
    print(f"HTTP {e.code}: {body}")
