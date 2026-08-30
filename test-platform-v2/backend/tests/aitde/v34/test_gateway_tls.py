"""AITDE V3.4 gateway TLS + worker CLI tests (V34-002 / V34-007).

The gateway builds a ``temporalio.service.TLSConfig`` from the configured cert
paths when mTLS is enabled (V34-007 worker machine identity foundation). The
worker CLI entry (``python -m app.modules.aitde.workflow.gateway --task-queue``)
reaches the fail-closed path when Temporal is disabled.
"""
from __future__ import annotations


from app.core.config import settings
from app.modules.aitde.workflow import gateway as gw


def test_tls_config_built_from_cert_paths(monkeypatch, tmp_path):
    """When TLS is enabled and cert paths are set, _get_client passes a TLSConfig."""
    ca = tmp_path / "ca.crt"
    cert = tmp_path / "worker.crt"
    key = tmp_path / "worker.key"
    for p in (ca, cert, key):
        p.write_bytes(b"mock-cert-material")

    original = {
        "enabled": settings.temporal_enabled,
        "tls": settings.temporal_tls_enabled,
        "ca": settings.temporal_tls_ca_path,
        "cert": settings.temporal_tls_cert_path,
        "key": settings.temporal_tls_key_path,
        "endpoint": settings.temporal_grpc_endpoint,
    }
    # Fake a connected client so we can inspect the connect kwargs without network.
    captured: dict = {}

    monkeypatch.setattr(settings, "temporal_enabled", True)
    monkeypatch.setattr(settings, "temporal_tls_enabled", True)
    monkeypatch.setattr(settings, "temporal_tls_ca_path", str(ca))
    monkeypatch.setattr(settings, "temporal_tls_cert_path", str(cert))
    monkeypatch.setattr(settings, "temporal_tls_key_path", str(key))

    import temporalio.client as _client_mod

    async def fake_connect(endpoint, **kwargs):
        captured["endpoint"] = endpoint
        captured["kwargs"] = kwargs
        return "FAKE_CLIENT"

    monkeypatch.setattr(_client_mod.Client, "connect", staticmethod(fake_connect))

    import asyncio

    instance = gw.TemporalWorkflowGateway()
    client = asyncio.run(instance._get_client())  # noqa: SLF001
    assert client == "FAKE_CLIENT"
    tls = captured["kwargs"]["tls"]
    assert tls is not None and tls.__class__.__name__ == "TLSConfig"

    # Restore settings.
    monkeypatch.setattr(settings, "temporal_enabled", original["enabled"])
    monkeypatch.setattr(settings, "temporal_tls_enabled", original["tls"])
    monkeypatch.setattr(settings, "temporal_tls_ca_path", original["ca"])
    monkeypatch.setattr(settings, "temporal_tls_cert_path", original["cert"])
    monkeypatch.setattr(settings, "temporal_tls_key_path", original["key"])


def test_tls_disabled_no_tlsconfig(monkeypatch):
    original = (settings.temporal_enabled, settings.temporal_tls_enabled)
    monkeypatch.setattr(settings, "temporal_enabled", True)
    monkeypatch.setattr(settings, "temporal_tls_enabled", False)
    import temporalio.client as _client_mod

    captured: dict = {}

    async def fake_connect(endpoint, **kwargs):
        captured["kwargs"] = kwargs
        return "FAKE_CLIENT"

    monkeypatch.setattr(_client_mod.Client, "connect", staticmethod(fake_connect))

    import asyncio

    instance = gw.TemporalWorkflowGateway()
    asyncio.run(instance._get_client())  # noqa: SLF001
    assert captured["kwargs"]["tls"] is False

    monkeypatch.setattr(settings, "temporal_enabled", original[0])
    monkeypatch.setattr(settings, "temporal_tls_enabled", original[1])


def test_worker_cli_fail_closed_when_disabled():
    """CLI worker entry raises fail-closed (503 TEMPORAL_DISABLED) when disabled."""
    code, detail = gw.temporal_gateway.unavailable()
    assert code == "TEMPORAL_DISABLED"
    assert detail is not None
