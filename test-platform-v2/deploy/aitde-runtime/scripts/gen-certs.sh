#!/usr/bin/env bash
# AITDE V3.4 — 自签 mTLS 证书（CA + Temporal server + worker client）
#
# 生成到 ./certs/（git-ignored）。开启 Temporal mTLS 时：
#   - Temporal server 用 temporal.crt/temporal.key（服务端证书）
#   - Control Plane / worker 用 worker.crt/worker.key（客户端证书，验证 server 用 ca.crt）
#   - 把路径填入 .env：TEMPORAL_TLS_ENABLED=true + *_PATH
#
# 依赖: openssl。用法: bash scripts/gen-certs.sh
set -euo pipefail
cd "$(dirname "$0")/.."
CERT_DIR="$(pwd)/certs"
mkdir -p "$CERT_DIR"
DAYS=3650
CN=${CN:-cameltv-aitde}

echo "[gen-certs] cert dir: $CERT_DIR"

# ── CA ──
openssl req -x509 -newkey rsa:2048 -nodes -days "$DAYS" \
  -keyout "$CERT_DIR/ca.key" -out "$CERT_DIR/ca.crt" -subj "/CN=${CN}-CA"

# ── Temporal server ──
openssl genrsa -out "$CERT_DIR/temporal.key" 2048
openssl req -new -key "$CERT_DIR/temporal.key" -out "$CERT_DIR/temporal.csr" \
  -subj "/CN=temporal"
openssl x509 -req -in "$CERT_DIR/temporal.csr" -CA "$CERT_DIR/ca.crt" -CAkey "$CERT_DIR/ca.key" \
  -CAcreateserial -days "$DAYS" -out "$CERT_DIR/temporal.crt" \
  -extfile <(printf "subjectAltName=DNS:localhost,DNS:temporal,IP:127.0.0.1")

# ── Worker client（Control Plane + worker 共用；仅验证 server，不要求双向 client-auth）──
openssl genrsa -out "$CERT_DIR/worker.key" 2048
openssl req -new -key "$CERT_DIR/worker.key" -out "$CERT_DIR/worker.csr" \
  -subj "/CN=worker"
openssl x509 -req -in "$CERT_DIR/worker.csr" -CA "$CERT_DIR/ca.crt" -CAkey "$CERT_DIR/ca.key" \
  -CAcreateserial -days "$DAYS" -out "$CERT_DIR/worker.crt"

rm -f "$CERT_DIR/temporal.csr" "$CERT_DIR/worker.csr" "$CERT_DIR/ca.srl"

echo "[gen-certs] done:"
ls -1 "$CERT_DIR"
echo
echo "配置到 .env:"
echo '  TEMPORAL_TLS_ENABLED=true'
echo "  TEMPORAL_TLS_CA_PATH=$(cygpath -w "$CERT_DIR/ca.crt" 2>/dev/null || echo "$CERT_DIR/ca.crt")"
echo "  TEMPORAL_TLS_CERT_PATH=$CERT_DIR/worker.crt"
echo "  TEMPORAL_TLS_KEY_PATH=$CERT_DIR/worker.key"
echo "（对 Temporal server 使用 $CERT_DIR/temporal.crt / temporal.key）"
