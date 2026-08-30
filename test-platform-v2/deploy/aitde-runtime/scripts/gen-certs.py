#!/usr/bin/env python
"""AITDE V3.4 mTLS cert generator (cross-platform, no openssl dependency).

Regenerates CA + Temporal server cert + worker client cert into ``./certs/``
(git-ignored) WITH the correct SubjectAlternativeNames so hostname verification
succeeds for DNS:localhost, DNS:temporal, IP:127.0.0.1 and IP:172.20.0.3.

This replaces the bash ``gen-certs.sh`` (whose ``-extfile <(...)`` SAN injection
is not portable to Windows).

Usage: python scripts/gen-certs.py
"""
from __future__ import annotations

import datetime
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

DEP = Path(__file__).resolve().parent.parent
CERT_DIR = DEP / "certs"
CERT_DIR.mkdir(parents=True, exist_ok=True)
DAYS = 3650
CN = "cameltv-aitde"

# SANs that must validate for host / container / cluster access.
SERVER_SANS = [
    "DNS:localhost",
    "DNS:temporal",
    "DNS:aitde-temporal",
    "IP:127.0.0.1",
    "IP:172.20.0.3",  # default compose network container IP (set BIND_ON_IP=0.0.0.0)
]

now = datetime.datetime.now(datetime.timezone.utc)
ttl = now + datetime.timedelta(days=DAYS)


def _write(name: str, data: bytes) -> None:
    (CERT_DIR / name).write_bytes(data)
    print(f"  wrote {name}")


def _san(*names: str) -> x509.SubjectAlternativeName:
    gens = []
    for n in names:
        if n.startswith("IP:"):
            gens.append(x509.IPAddress(__import__("ipaddress").ip_address(n[3:])))
        elif n.startswith("DNS:"):
            gens.append(x509.DNSName(n[4:]))
    return x509.SubjectAlternativeName(gens)


# ── CA ──────────────────────────────────────────────────────────────────────
ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, f"{CN}-CA")])
ca_cert = (
    x509.CertificateBuilder()
    .subject_name(ca_name)
    .issuer_name(ca_name)
    .public_key(ca_key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(now)
    .not_valid_after(ttl)
    .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
    .add_extension(x509.KeyUsage(
        digital_signature=True, key_cert_sign=True, crl_sign=True,
        content_commitment=False, data_encipherment=False, key_agreement=False,
        key_encipherment=False, encipher_only=None, decipher_only=None,
    ), critical=True)
    .sign(ca_key, hashes.SHA256())
)
_write("ca.crt", ca_cert.public_bytes(serialization.Encoding.PEM))
_write("ca.key", ca_key.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.TraditionalOpenSSL,
    serialization.NoEncryption(),
))

# ── Temporal server cert ─────────────────────────────────────────────────────
srv_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
srv_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "temporal")])
srv_cert = (
    x509.CertificateBuilder()
    .subject_name(srv_name)
    .issuer_name(ca_cert.subject)
    .public_key(srv_key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(now)
    .not_valid_after(ttl)
    .add_extension(_san(*SERVER_SANS), critical=False)
    .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
    .add_extension(x509.KeyUsage(
        digital_signature=True, key_encipherment=True, key_agreement=False,
        key_cert_sign=False, crl_sign=False, content_commitment=False,
        data_encipherment=False, encipher_only=None, decipher_only=None,
    ), critical=True)
    .sign(ca_key, hashes.SHA256())
)
_write("temporal.crt", srv_cert.public_bytes(serialization.Encoding.PEM))
_write("temporal.key", srv_key.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.TraditionalOpenSSL,
    serialization.NoEncryption(),
))

# ── Worker client cert ───────────────────────────────────────────────────────
wk_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
wk_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "worker")])
wk_cert = (
    x509.CertificateBuilder()
    .subject_name(wk_name)
    .issuer_name(ca_cert.subject)
    .public_key(wk_key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(now)
    .not_valid_after(ttl)
    .add_extension(_san("DNS:worker"), critical=False)
    .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
    .sign(ca_key, hashes.SHA256())
)
_write("worker.crt", wk_cert.public_bytes(serialization.Encoding.PEM))
_write("worker.key", wk_key.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.TraditionalOpenSSL,
    serialization.NoEncryption(),
))

print(f"\n[gen-certs] regenerated {len(list(CERT_DIR.glob('*'))) } files into {CERT_DIR}")
