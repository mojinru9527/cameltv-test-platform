"""API-level regression for the OpenAPI import outbound policy."""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.api.v1 import apitest_assets
from app.core.outbound_policy import OutboundPolicyError


def test_openapi_url_import_surfaces_policy_error(monkeypatch):
    def _reject(*args, **kwargs):
        raise OutboundPolicyError("禁止访问私网、回环、链路本地或保留地址")

    monkeypatch.setattr(apitest_assets, "safe_get_text", _reject)

    with pytest.raises(HTTPException) as exc:
        apitest_assets._resolve_spec_or_400(
            "openapi_url",
            "http://127.0.0.1/openapi.json",
            None,
        )

    assert exc.value.status_code == 400
    assert "禁止访问" in exc.value.detail
