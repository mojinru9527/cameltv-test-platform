"""Restart Vite dev server by killing old and spawning new."""
import subprocess, time, os, signal, sys

os.chdir(r"F:\CamelTv\test-platform-v2\frontend")

# Kill existing Vite
print("Killing existing Vite...")
result = subprocess.run(["taskkill", "/F", "/IM", "node.exe"], capture_output=True, text=True)
print(result.stdout)
print(result.stderr)

time.sleep(2)

# Start new Vite
print("Starting Vite with updated config...")
with open("../backend/vite_out.log", "w") as log:
    proc = subprocess.Popen(
        ["npx", "vite", "--port", "5173", "--host"],
        stdout=log, stderr=log,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
    )
print(f"Vite PID: {proc.pid}")

# Wait for startup
time.sleep(5)

# Test
import urllib.request, json
try:
    r = urllib.request.urlopen("http://localhost:5173/", timeout=5)
    print(f"Frontend status: {r.status}")
except Exception as e:
    print(f"Frontend error: {e}")

# Test proxy
try:
    req = urllib.request.Request("http://localhost:5173/api/v1/system/menus",
        headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjoxNzg0NTcxNTA3fQ.CPTWOPm7Ju2vRcSpbKXtR7hbw5PVdw_3tx_4PMQ8DL4"})
    r = json.loads(urllib.request.urlopen(req, timeout=10).read())
    print(f"Proxy menus: code={r['code']} count={len(r['data'])}")
except urllib.error.HTTPError as e:
    body = e.read().decode()[:300]
    print(f"Proxy menus ERROR: HTTP {e.code}: {body}")
except Exception as e:
    print(f"Proxy menus ERROR: {e}")

print("\nDone! Visit http://localhost:5173")
