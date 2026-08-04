#!/usr/bin/env bash
# Fetch Test5 gateway API contracts (read-only, no credentials, no repo secrets).
#
# Usage (inside WSL2 with Test5 OpenVPN connected):
#   bash scripts/executor/fetch-test5-contracts.sh [OUTPUT_DIR]
#
# Environment overrides:
#   TEST5_GATEWAY_IP   gateway IP to use (default 192.168.50.170, resolved via VPN DNS)
#
# Strategy per service: /v3/api-docs first; on failure fall back to the
# Swagger2 group discovered from /swagger-resources (V1, or the live-platform
# group name). Services that require auth (admin-service 302, konfi-service
# "token无效") are recorded in the manifest with a note, never faked.
#
# Produces:
#   test-platform-v2/tests/api-testing/specs/test5-contracts/{service}.openapi.json
#   test-platform-v2/tests/api-testing/specs/test5-contracts/manifest.json
set -euo pipefail

GATEWAY_HOST="${TEST5_GATEWAY_HOST:-camel-api-gateway05.svc.elelive.cn}"
GATEWAY_PORT="${TEST5_GATEWAY_PORT:-80}"
GATEWAY_IP="${TEST5_GATEWAY_IP:-192.168.50.170}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
OUT_DIR="${1:-${REPO_ROOT}/test-platform-v2/tests/api-testing/specs/test5-contracts}"

SERVICES=(
  camel-service
  payment-service
  studio-service
  api-gateway-service
  gateway-service
  camel-mimo
  live-platform
  konfi-service
  account-service
  admin-service
)

BASE_URL="http://${GATEWAY_HOST}:${GATEWAY_PORT}"
CURL=(curl -sS -m 30 --resolve "${GATEWAY_HOST}:${GATEWAY_PORT}:${GATEWAY_IP}")

mkdir -p "${OUT_DIR}"
FETCHED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Optional DNS check via VPN gateway (informational only).
if command -v nslookup >/dev/null 2>&1; then
  VPN_IP="$(nslookup "${GATEWAY_HOST}" 10.7.7.1 2>/dev/null | awk '/^Address:/{ if ($2 !~ /#/) { print $2; exit } }' || true)"
  if [ -n "${VPN_IP}" ]; then
    echo "info: VPN DNS resolved ${GATEWAY_HOST} -> ${VPN_IP} (using ${GATEWAY_IP})"
  fi
fi

rm -f "${OUT_DIR}/manifest.json"
echo "[" > "${OUT_DIR}/manifest.json"
first=1

describe() {
  python3 -c '
import json, sys
try:
    d = json.load(open(sys.argv[1], encoding="utf-8"))
    info = d.get("info", {})
    spec = "openapi3" if "openapi" in d else ("swagger2" if "swagger" in d else "unknown")
    paths = len(d.get("paths", {}))
    print(json.dumps({"version": info.get("version", ""), "title": info.get("title", ""),
                      "spec": spec, "paths": paths}, ensure_ascii=False))
except Exception as exc:
    print(json.dumps({"version": "", "title": "", "spec": "invalid", "paths": 0,
                      "parse_error": str(exc)}, ensure_ascii=False))
' "$1"
}

fetch_with_fallback() {
  local svc="$1"
  local fn="$2"
  local url code
  url="${BASE_URL}/${svc}/v3/api-docs"
  code="$("${CURL[@]}" -o "${fn}" -w '%{http_code}' "${url}" 2>/dev/null || echo ERR)"
  if [ "${code}" = "200" ] && [ -s "${fn}" ]; then
    echo "${svc}|${code}|${url}"
    return 0
  fi
  # Fallback: Swagger2 group (V1 by default; live-platform uses its group name).
  if [ "${svc}" = "live-platform" ]; then
    url="${BASE_URL}/${svc}/v2/api-docs?group=swagger%202.X%E7%89%88%E6%9C%AC"
  else
    url="${BASE_URL}/${svc}/v2/api-docs?group=V1"
  fi
  code="$("${CURL[@]}" -o "${fn}" -w '%{http_code}' "${url}" 2>/dev/null || echo ERR)"
  echo "${svc}|${code}|${url}"
  return 0
}

for svc in "${SERVICES[@]}"; do
  fn="${OUT_DIR}/${svc}.openapi.json"
  row="$(fetch_with_fallback "${svc}" "${fn}")"
  svc_name="${row%%|*}"
  code="$(printf '%s' "${row}" | cut -d'|' -f2)"
  url="$(printf '%s' "${row}" | cut -d'|' -f3-)"
  if [ "${code}" != "200" ] || [ ! -s "${fn}" ]; then
    note=""
    if [ "${code}" = "302" ]; then note="requires-auth-redirect"; fi
    echo "${svc} -> HTTP ${code} (recorded, not fetched)${note:+ [${note}]}"
    if [ "${first}" -eq 0 ]; then echo "," >> "${OUT_DIR}/manifest.json"; fi
    cat >> "${OUT_DIR}/manifest.json" <<EOF
{"service":"${svc}","status":"failed","http_code":"${code}","note":"${note}"}
EOF
    first=0
    continue
  fi
  size="$(wc -c < "${fn}")"
  sha="$(sha256sum "${fn}" | awk '{print $1}')"
  desc="$(describe "${fn}")"
  paths="$(printf '%s' "${desc}" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("paths",0))')"
  ver="$(printf '%s' "${desc}" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("version",""))')"
  spec="$(printf '%s' "${desc}" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("spec",""))')"
  title="$(printf '%s' "${desc}" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("title",""))')"
  if [ "${spec}" = "unknown" ] || [ "${spec}" = "invalid" ] || [ "${paths}" = "0" ]; then
    note="no-contract"
    if grep -q 'token' "${fn}" 2>/dev/null; then note="requires-token"; fi
    if grep -q 'NOT FOUND' "${fn}" 2>/dev/null; then note="service-no-contract"; fi
    echo "${svc} -> HTTP ${code} (no real contract: ${note})"
    if [ "${first}" -eq 0 ]; then echo "," >> "${OUT_DIR}/manifest.json"; fi
    cat >> "${OUT_DIR}/manifest.json" <<EOF
{"service":"${svc}","status":"no-contract","url":"${url}","http_code":"${code}","size_bytes":${size},"sha256":"${sha}","paths":0,"note":"${note}","fetched_at":"${FETCHED_AT}"}
EOF
    first=0
    continue
  fi
  echo "${svc} -> HTTP ${code} bytes=${size} spec=${spec} paths=${paths} version=${ver}"
  if [ "${first}" -eq 0 ]; then echo "," >> "${OUT_DIR}/manifest.json"; fi
  cat >> "${OUT_DIR}/manifest.json" <<EOF
{"service":"${svc}","status":"ok","url":"${url}","http_code":"${code}","spec":"${spec}","size_bytes":${size},"sha256":"${sha}","paths":${paths},"info":{"version":"${ver}","title":"${title}"},"fetched_at":"${FETCHED_AT}"}
EOF
  first=0
done

echo "]" >> "${OUT_DIR}/manifest.json"
echo "manifest: ${OUT_DIR}/manifest.json"
