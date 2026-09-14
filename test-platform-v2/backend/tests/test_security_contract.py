"""Static deployment contract for browser headers and fixed backend routes."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"


def test_index_uses_external_theme_bootstrap():
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")
    assert '<script src="/theme-bootstrap.js"></script>' in html
    assert "data-theme-bootstrap" not in html
    assert (FRONTEND / "public" / "theme-bootstrap.js").is_file()


def test_nginx_declares_security_headers_and_backend_routes():
    nginx = (FRONTEND / "nginx.conf").read_text(encoding="utf-8")
    assert "security-headers.conf" in nginx
    assert "location = /health" in nginx
    assert "location = /openapi.json" in nginx
    assert "location ^~ /docs" in nginx
    assert "location ^~ /redoc" in nginx


def test_frontend_image_copies_security_header_include():
    dockerfile = (FRONTEND / "Dockerfile").read_text(encoding="utf-8")
    assert "security-headers.conf /etc/nginx/conf.d/security-headers.conf" in dockerfile


def test_backend_trusts_explicit_reverse_proxy_headers():
    dockerfile = (ROOT / "backend" / "Dockerfile").read_text(encoding="utf-8")
    compose = (ROOT / "deploy" / "docker-compose.yml").read_text(encoding="utf-8")
    assert "--forwarded-allow-ips" in dockerfile
    assert "FORWARDED_ALLOW_IPS" in compose
