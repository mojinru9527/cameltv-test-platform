"""Compare backend versions on different ports."""
import urllib.request, json

TOKEN = None
# Login to 8002 (fixed backend)
r = json.loads(urllib.request.urlopen(urllib.request.Request(
    "http://localhost:8002/api/v1/auth/login",
    data=json.dumps({"username":"admin","password":"admin123"}).encode(),
    headers={"Content-Type":"application/json"}), timeout=10).read())
TOKEN = r['data']['access_token']

def test_menus(port, label):
    try:
        req = urllib.request.Request(f"http://localhost:{port}/api/v1/system/menus",
            headers={"Authorization": f"Bearer {TOKEN}"})
        r = json.loads(urllib.request.urlopen(req, timeout=10).read())
        print(f"  [{label}] Port {port}: code={r['code']} menus={len(r['data'])}")
        if r['data']:
            print(f"           First sort={r['data'][0]['sort']} type={type(r['data'][0]['sort']).__name__}")
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:300]
        print(f"  [{label}] Port {port}: HTTP {e.code} body={body}")
    except Exception as e:
        print(f"  [{label}] Port {port}: ERROR {e}")

print("=== Comparing backends ===")
test_menus(8000, "OLD zombie?")
test_menus(8001, "OLD backend")
test_menus(8002, "NEW backend (fixed)")

# Now test Vite proxy
print("\n=== Testing Vite proxy ===")
try:
    req = urllib.request.Request("http://localhost:5173/api/v1/system/menus",
        headers={"Authorization": f"Bearer {TOKEN}"})
    r = json.loads(urllib.request.urlopen(req, timeout=10).read())
    print(f"  Proxy: code={r['code']} menus={len(r['data'])}")
except urllib.error.HTTPError as e:
    body = e.read().decode()[:500]
    print(f"  Proxy: HTTP {e.code}")
    print(f"  Body: {body}")
except Exception as e:
    print(f"  Proxy: ERROR {e}")
