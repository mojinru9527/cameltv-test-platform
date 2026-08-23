"""Restart Vite dev server by killing old and spawning new.

凭据策略（安全审计修复）：不再在仓库内硬编码 JWT；认证检查令牌从环境变量
TP_TOKEN 读取，未配置时跳过鉴权探测（仅提示）。
"""
import subprocess, time, os, signal, sys

os.chdir(r"F:\CamelTv\test-platform-v2\frontend")
TOKEN = os.environ.get("TP_TOKEN", "").strip()

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

# Test proxy (auth token from env TP_TOKEN; 未设置时跳过鉴权探测)
try:
    if not TOKEN:
        print("Proxy menus: TP_TOKEN 未设置，跳过鉴权探测（获取方式见运维手册）")
    else:
        req = urllib.request.Request("http://localhost:5173/api/v1/system/menus",
            headers={"Authorization": f"Bearer {TOKEN}"})
        r = json.loads(urllib.request.urlopen(req, timeout=10).read())
        print(f"Proxy menus: code={r['code']} count={len(r['data'])}")
except urllib.error.HTTPError as e:
    body = e.read().decode()[:300]
    print(f"Proxy menus ERROR: HTTP {e.code}: {body}")
except Exception as e:
    print(f"Proxy menus ERROR: {e}")

print("\nDone! Visit http://localhost:5173")
