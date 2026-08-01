"""Contracts for the fixed local and production runtime profiles."""
from __future__ import annotations

from pathlib import Path


PLATFORM_ROOT = Path(__file__).resolve().parents[2]
PROFILE_ROOT = PLATFORM_ROOT / "config" / "runtime"
LAUNCHER_PATH = PLATFORM_ROOT / "scripts" / "start-platform-environment.ps1"
PROFILE_NAMES = ("local", "production")


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
        "production",
    }
    assert {path.stem.removesuffix(".env") for path in PROFILE_ROOT.glob("*.env.example")} == {
        "local",
        "production",
    }
    assert len({profile["COMPOSE_PROJECT_NAME"] for profile in profiles.values()}) == 2
    assert len({profile["FRONTEND_PORT"] for profile in profiles.values()}) == 2
    assert len({profile["PLATFORM_FRONTEND_URL"] for profile in profiles.values()}) == 2
    assert len({profile["DATABASE_URL"] for profile in profiles.values()}) == 2


def test_local_profile_is_development_only() -> None:
    profile = read_profile("local")

    assert profile["ENVIRONMENT"] == "development"
    assert profile["DATABASE_URL"].startswith("sqlite:///")
    assert profile["AUTO_CREATE_TABLES"] == "true"
    assert profile["COOKIE_SECURE"] == "false"
    assert profile["PLATFORM_FRONTEND_URL"] == "http://localhost:5173"
    assert profile["VITE_DEV_PORT"] == "5173"
    assert profile["VITE_PROXY_TARGET"] == "http://127.0.0.1:8000"


def test_production_profile_is_secure_and_isolated_from_local() -> None:
    local = read_profile("local")
    production = read_profile("production")

    assert production["ENVIRONMENT"] == "production"
    assert production["DATABASE_URL"].startswith("postgresql://")
    assert production["AUTO_CREATE_TABLES"] == "false"
    assert production["COOKIE_SECURE"] == "true"
    assert production["PLATFORM_FRONTEND_URL"].startswith("https://")
    assert production["ALLOWED_ORIGINS"] == production["PLATFORM_FRONTEND_URL"]
    assert production["CSRF_ALLOWED_ORIGINS"] == production["PLATFORM_FRONTEND_URL"]
    assert production["POSTGRES_DB"] == "cameltv_production"
    assert "cameltv_production" in production["DATABASE_URL"]
    assert production["BACKEND_PORT"] == "8000"
    assert production["DATABASE_URL"] != local["DATABASE_URL"]
    assert production["PLATFORM_FRONTEND_URL"] != local["PLATFORM_FRONTEND_URL"]


def test_launcher_only_accepts_two_targets_and_rejects_stale_local_processes() -> None:
    launcher = LAUNCHER_PATH.read_text(encoding="utf-8")

    assert '[ValidateSet("local", "production")]' in launcher
    assert '[ValidateSet("local", "test", "production")]' not in launcher
    assert '$manifest.gitSha -ceq (Get-GitSha)' in launcher
    assert "Production origins must exactly match PLATFORM_FRONTEND_URL." in launcher
    assert "DATABASE_URL database must match POSTGRES_DB." in launcher


def test_local_status_requires_and_displays_a_verified_runtime_manifest() -> None:
    launcher = LAUNCHER_PATH.read_text(encoding="utf-8")

    assert "Assert-LocalReuseManifest `\n            -Profile $Profile `\n            -Database $Database `\n            -RequireRunning" in launcher
    assert "Local runtime status is stale/unverified:" in launcher
    assert '$manifest.target -ceq "local"' in launcher
    assert '$manifest.frontendUrl -ceq $Profile["PLATFORM_FRONTEND_URL"]' in launcher
    assert "$manifest.backendUrl -ceq $expectedBackendUrl" in launcher
    assert '$manifest.database.backend -ceq $Database["backend"]' in launcher
    assert '$manifest.database.name -ceq $Database["name"]' in launcher
    assert "[int]$manifest.ports.backend -eq $backendPort" in launcher
    assert "[int]$manifest.ports.frontend -eq $frontendPort" in launcher
    assert "function Get-VerifiedListenerProcessId" in launcher
    assert "function Set-VerifiedManifestListenerPid" in launcher
    assert "$listenerList.Count -ne 1" in launcher
    assert "has multiple listener processes" in launcher
    assert "outside this worktree" in launcher
    assert "$beforeValid -and $afterValid" in launcher
    assert 'if ([int]$listenerPid -ne [int]$startedProcess.Id)' in launcher
    assert 'return [int]$listenerPid' in launcher
    assert '-Name "backend"' in launcher
    assert '-Listeners $backendListeners' in launcher
    assert '-Name "frontend"' in launcher
    assert '-Listeners $frontendListeners' in launcher
    assert '$Manifest.pids | Add-Member -MemberType NoteProperty -Name $Name -Value $listenerPid -Force' in launcher
    assert 'Write-Host "Runtime manifest: verified"' in launcher
    assert 'Write-Host "Manifest target: $($manifest.target)"' in launcher
    assert 'Write-Host "Manifest frontend URL: $($manifest.frontendUrl)"' in launcher
    assert 'Write-Host "Manifest backend URL: $($manifest.backendUrl)"' in launcher
    assert 'Write-Host "Manifest database: $($manifest.database.backend)/$($manifest.database.name)"' in launcher
    assert 'Write-Host "Manifest ports: backend=$($manifest.ports.backend), frontend=$($manifest.ports.frontend)"' in launcher
    assert 'Write-Host "Manifest Git SHA: $($manifest.gitSha)"' in launcher
    assert 'Write-Host "Manifest PIDs: backend=$($manifest.pids.backend), frontend=$($manifest.pids.frontend)"' in launcher
