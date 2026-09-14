"""Batch 245 password recovery delivery and public availability tests."""
from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from app.core.config import settings
from app.services import notify_service


def test_public_access_reports_password_reset_email_availability(client, monkeypatch):
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(settings, "smtp_from", "noreply@example.com")
    monkeypatch.setattr(settings, "frontend_url", "https://app.example.com")

    response = client.get("/api/v1/auth/public-access")

    assert response.status_code == 200
    assert response.json()["data"]["password_reset_email_enabled"] is True


def test_public_access_hides_incomplete_password_reset_configuration(client, monkeypatch):
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.com")
    monkeypatch.setattr(settings, "smtp_from", "")
    monkeypatch.setattr(settings, "smtp_user", "")
    monkeypatch.setattr(settings, "frontend_url", "")

    response = client.get("/api/v1/auth/public-access")

    assert response.status_code == 200
    assert response.json()["data"]["password_reset_email_enabled"] is False


def test_forgot_password_queues_frontend_reset_link(client, admin_user, db_session, monkeypatch):
    admin_user.email = "admin@example.com"
    admin_user.status = 1
    db_session.commit()
    monkeypatch.setattr(settings, "frontend_url", "https://app.example.com/")

    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        notify_service,
        "send_password_reset_email",
        lambda to_addr, reset_url: calls.append((to_addr, reset_url)) or True,
    )

    response = client.post("/api/v1/auth/forgot-password", json={"username": admin_user.username})

    assert response.status_code == 200
    assert response.json()["code"] == 0
    assert len(calls) == 1
    to_addr, reset_url = calls[0]
    assert to_addr == "admin@example.com"
    parsed = urlparse(reset_url)
    assert parsed.scheme == "https"
    assert parsed.netloc == "app.example.com"
    assert parsed.path == "/reset-password"
    assert parse_qs(parsed.query).get("token")


def test_forgot_password_keeps_generic_response_for_missing_user(client, monkeypatch):
    monkeypatch.setattr(settings, "frontend_url", "https://app.example.com")
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        notify_service,
        "send_password_reset_email",
        lambda to_addr, reset_url: calls.append((to_addr, reset_url)) or True,
    )

    response = client.post("/api/v1/auth/forgot-password", json={"username": "does-not-exist"})

    assert response.status_code == 200
    assert response.json()["code"] == 0
    assert calls == []
