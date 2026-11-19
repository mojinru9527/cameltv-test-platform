#!/usr/bin/env bash
# AUD-020 / Runner egress evidence: WSL2 egress allowlist lab.
#
# Applies a default-DROP OUTPUT policy with a minimal allowlist, runs allowed/denied probes,
# captures iptables state + logs, then restores the original policy (trap).
#
# Usage (inside WSL, root):
#   bash verify_runner_egress_wsl.sh <out_dir> <allow_host> [allow_port] [allowed_url]
set -u

OUT="${1:?out_dir required}"
ALLOW_HOST="${2:?allow_host required}"
ALLOW_PORT="${3:-443}"
ALLOWED_URL="${4:-https://camel-test5.elelive.cn/camel-service/ee/sports_live/home_match?day=$(date +%Y%m%d)&sportType=football}"

mkdir -p "$OUT"

{
  echo "captured_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "distro=Ubuntu(WSL2) host=$(hostname)"
  echo "uid=$(id -u) user=$(id -un)"
  ip -4 addr show eth0 | awk '/inet /{print "ipv4="$2}'
  ip route | head -5
  grep nameserver /etc/resolv.conf
} > "$OUT/runner-identity.txt"

iptables-save > "$OUT/iptables-before.txt"

restore() {
  iptables -F OUTPUT
  iptables -P OUTPUT ACCEPT
  iptables-save > "$OUT/iptables-restored.txt"
}
trap restore EXIT

iptables -F OUTPUT
iptables -P OUTPUT DROP
iptables -A OUTPUT -o lo -j ACCEPT
iptables -A OUTPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
iptables -A OUTPUT -p udp --dport 53 -j ACCEPT
iptables -A OUTPUT -p tcp --dport 53 -j ACCEPT
iptables -A OUTPUT -d "$ALLOW_HOST" -p tcp --dport "$ALLOW_PORT" -j ACCEPT
iptables-save > "$OUT/iptables-allowlist.txt"

{
  echo "probe=allowed target=$ALLOWED_URL ($ALLOW_HOST:$ALLOW_PORT)"
  curl -skS -o /dev/null -w 'http=%{http_code} ip=%{remote_ip} seconds=%{time_total}\n' --max-time 15 "$ALLOWED_URL"; echo "curl_exit=$?"
  echo "probe=denied target=https://example.com:443"
  curl -sS -o /dev/null -w 'http=%{http_code} ip=%{remote_ip} seconds=%{time_total}\n' --max-time 8 https://example.com; echo "curl_exit=$?"
  echo "probe=denied target=http://1.1.1.1:80"
  curl -sS -o /dev/null -w 'http=%{http_code} ip=%{remote_ip} seconds=%{time_total}\n' --max-time 8 http://1.1.1.1; echo "curl_exit=$?"
} > "$OUT/probes.txt" 2>&1

python3 - "$ALLOW_HOST" "$ALLOW_PORT" > "$OUT/python-socket-probes.txt" 2>&1 <<'PY'
import socket, sys, time
host, port = sys.argv[1], int(sys.argv[2])

def probe(target, port, timeout=5):
    start = time.time()
    try:
        with socket.create_connection((target, port), timeout=timeout):
            return f"{target}:{port} OK {time.time()-start:.2f}s"
    except Exception as exc:
        return f"{target}:{port} BLOCKED {type(exc).__name__} {time.time()-start:.2f}s"

print(probe(host, port))
print(probe("example.com", 443, timeout=8))
print(probe("1.1.1.1", 80))
PY

echo "egress evidence written to $OUT"
