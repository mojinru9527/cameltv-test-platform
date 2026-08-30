#!/usr/bin/env python
"""AITDE V3.4 mTLS drill (V34-007 / §93-599): invalid client cert must be rejected.

Proves against the LIVE Temporal server (frontend, requireClientAuth) that:
  1. A worker presenting a cert signed by the trusted CA (worker.crt -> ca.crt) connects.
  2. A worker presenting NO client cert is rejected (server requires mutual auth).
  3. A worker presenting a cert signed by a ROGUE CA (not our ca.crt) is rejected.

Run: python scripts/drill_mtls_reject.py
"""
from __future__ import annotations

import asyncio
import datetime
import tempfile
from pathlib import Path

from temporalio.client import Client
from temporalio.service import TLSConfig

DEP = Path(__file__).resolve().parent.parent
CA = DEP / "certs" / "ca.crt"
WORKER_CERT = DEP / "certs" / "worker.crt"
WORKER_KEY = DEP / "certs" / "worker.key"
SERVER = "127.0.0.1:7233"
NS = "default"


def _tls(cert: Path | None, key: Path | None) -> TLSConfig:
    ca_data = CA.read_bytes()
    return TLSConfig(
        server_root_ca_cert=ca_data,
        client_cert=cert.read_bytes() if cert is not None else None,
        client_private_key=key.read_bytes() if key is not None else None,
    )


def _make_rogue_cert() -> tuple[Path, Path]:
    """Generate a ROGUE CA + a client cert signed by it (NOT our ca.crt).

    Uses the ``cryptography`` lib (no openssl dependency on Windows host).
    """
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    rd = Path(tempfile.mkdtemp(prefix="aitde-rogue-"))
    now = datetime.datetime.now(datetime.timezone.utc)
    ttl = now + datetime.timedelta(days=1)

    # Rogue CA (self-signed, NOT our ca.crt)
    rogue_ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    rogue_ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "rogue-ca")])
    rogue_ca_cert = (
        x509.CertificateBuilder()
        .subject_name(rogue_ca_name)
        .issuer_name(rogue_ca_name)
        .public_key(rogue_ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(ttl)
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(rogue_ca_key, hashes.SHA256())
    )

    # Rogue client leaf cert signed by the ROGUE CA
    client_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    client_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "rogue-worker")])
    rogue_client_cert = (
        x509.CertificateBuilder()
        .subject_name(client_name)
        .issuer_name(rogue_ca_cert.subject)
        .public_key(client_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(ttl)
        .sign(rogue_ca_key, hashes.SHA256())
    )

    cert_path = rd / "rogue.client.crt"
    key_path = rd / "rogue.client.key"
    cert_path.write_bytes(rogue_client_cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        client_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )
    return cert_path, key_path


async def _connect(label: str, tls_config: TLSConfig) -> bool:
    try:
        c = await Client.connect(SERVER, namespace=NS, tls=tls_config)
        # Client.connect performs the TLS handshake + a real cluster RPC. A
        # successful non-raising connect proves the mTLS handshake completed
        # with a server-trusted client identity.
        print(f"[OK]      {label}: server accepted the mTLS handshake")
        return True
    except Exception as e:  # noqa: BLE001
        kind = type(e).__name__
        print(f"[REJECT]  {label}: {kind}: {str(e)[:300]}")
        return False


async def main() -> int:
    print(f"mTLS drill against {SERVER} namespace={NS}")
    print(f"CA        = {CA}")
    print(f"worker    = {WORKER_CERT}")
    print()

    # Case 1: valid cert signed by our CA -> expect OK
    ok_valid = await _connect("valid worker cert (signed by our CA)", _tls(WORKER_CERT, WORKER_KEY))

    # Case 2: no client cert -> expect REJECT (server requires mutual auth)
    ok_none = await _connect("no client cert", _tls(None, None))

    # Case 3: rogue-CA client cert -> expect REJECT
    r_cert, r_key = _make_rogue_cert()
    ok_rogue = await _connect("rogue-CA client cert", _tls(r_cert, r_key))

    print()
    results = {
        "valid_cert_accepted": ok_valid,
        "no_cert_rejected": not ok_none,
        "rogue_cert_rejected": not ok_rogue,
    }
    for k, v in results.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")

    # The validating assertion for §93-599: invalid cert(s) refused while valid accepted.
    all_pass = ok_valid and (not ok_none) and (not ok_rogue)
    print(f"\nRESULT: {'PASS' if all_pass else 'FAIL'} (valid accepted AND invalid refused)")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
