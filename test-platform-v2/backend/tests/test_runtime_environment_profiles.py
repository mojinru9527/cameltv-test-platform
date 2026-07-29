"""Contracts for fixed local, test, and production runtime profiles."""
from __future__ import annotations

from pathlib import Path


PLATFORM_ROOT = Path(__file__).resolve().parents[2]
PROFILE_ROOT = PLATFORM_ROOT / "config" / "runtime"
PROFILE_NAMES = ("local", "test", "production")


def read_profile(name: str) -> dict[str, str]:
    profile_path = PROFILE_ROOT / f"{name}.env.example"
    values: dict[str, str] = {}
    for raw_line in profile_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        assert separator, f"{profile_path}: invalid profile line: {raw_line!r}"
        values[key.strip()] = value.strip()
    return values


def test_runtime_profiles_have_unique_identity_and_storage() -> None:
    profiles = {name: read_profile(name) for name in PROFILE_NAMES}

    assert {profile["PLATFORM_TARGET"] for profile in profiles.values()} == {
        "local",
        "test",
        "production",
    }
    assert len({profile["COMPOSE_PROJECT_NAME"] for profile in profiles.values()}) == 3
    assert len({profile["FRONTEND_PORT"] for profile in profiles.values()}) == 3
    assert len({profile["BACKEND_PORT"] for profile in profiles.values()}) == 3
    assert len({profile["PLATFORM_FRONTEND_URL"] for profile in profiles.values()}) == 3
    assert len({profile["DATABASE_URL"] for profile in profiles.values()}) == 3


def test_local_profile_is_development_only() -> None:
    profile = read_profile("local")

    assert profile["ENVIRONMENT"] == "development"
    assert profile["DATABASE_URL"].startswith("sqlite:///")
    assert profile["AUTO_CREATE_TABLES"] == "true"
    assert profile["COOKIE_SECURE"] == "false"
    assert profile["PLATFORM_FRONTEND_URL"] == "http://localhost:5173"
    assert profile["VITE_DEV_PORT"] == "5173"
    assert profile["VITE_PROXY_TARGET"] == "http://127.0.0.1:8000"


def test_shared_profiles_are_production_like_and_isolated() -> None:
    shared_profiles = {name: read_profile(name) for name in ("test", "production")}

    for profile in shared_profiles.values():
        assert profile["ENVIRONMENT"] == "production"
        assert profile["DATABASE_URL"].startswith("postgresql://")
        assert profile["AUTO_CREATE_TABLES"] == "false"
        assert profile["COOKIE_SECURE"] == "true"
        assert profile["PLATFORM_FRONTEND_URL"].startswith("https://")
        assert profile["ALLOWED_ORIGINS"] == profile["PLATFORM_FRONTEND_URL"]
        assert profile["CSRF_ALLOWED_ORIGINS"] == profile["PLATFORM_FRONTEND_URL"]

    assert (
        shared_profiles["test"]["POSTGRES_DB"]
        != shared_profiles["production"]["POSTGRES_DB"]
    )
    assert (
        shared_profiles["test"]["POSTGRES_PASSWORD"]
        != shared_profiles["production"]["POSTGRES_PASSWORD"]
    )
    assert "cameltv_test" in shared_profiles["test"]["DATABASE_URL"]
    assert "cameltv_production" in shared_profiles["production"]["DATABASE_URL"]
