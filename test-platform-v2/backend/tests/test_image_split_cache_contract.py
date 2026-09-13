"""Batch 238 — image split and build cache contract tests."""
from __future__ import annotations

from pathlib import Path

import yaml


PLATFORM = Path(__file__).resolve().parents[2]
REPO = PLATFORM.parent
BACKEND = PLATFORM / "backend"
FRONTEND = PLATFORM / "frontend"


def test_backend_dockerfile_has_light_api_and_heavy_runtime_targets():
    dockerfile = (BACKEND / "Dockerfile").read_text(encoding="utf-8")
    assert "FROM runtime-base AS runner" in dockerfile
    assert "FROM runtime-base AS api" in dockerfile
    assert "FROM runner AS runtime" in dockerfile

    runner = dockerfile[dockerfile.index("FROM runtime-base AS runner"):dockerfile.index("FROM runtime-base AS api")]
    api = dockerfile[dockerfile.index("FROM runtime-base AS api"):dockerfile.index("FROM runner AS runtime")]
    assert "nodejs" in runner
    assert "playwright install" in runner
    assert "nodejs" not in api
    assert "playwright install" not in api


def test_buildkit_cache_mounts_are_wired():
    backend = (BACKEND / "Dockerfile").read_text(encoding="utf-8")
    frontend = (FRONTEND / "Dockerfile").read_text(encoding="utf-8")
    assert "--mount=type=cache,target=/root/.cache/pip" in backend
    assert "--mount=type=cache,target=/root/.npm" in backend
    assert "--mount=type=cache,target=/root/.npm npm ci" in frontend


def test_opt_in_execution_overlay_uses_split_targets():
    path = PLATFORM / "deploy" / "docker-compose.execution.yml"
    compose = yaml.safe_load(path.read_text(encoding="utf-8"))
    services = compose["services"]
    assert services["backend"]["build"]["target"] == "api"
    assert services["runner"]["build"]["target"] == "runner"
    assert services["aitde-worker"]["build"]["target"] == "runner"
    assert services["volume-permissions"]["build"]["target"] == "api"


def test_frontend_heavy_chunks_and_spa_shell_cache_policy():
    vite = (FRONTEND / "vite.config.ts").read_text(encoding="utf-8")
    nginx = (FRONTEND / "nginx.conf").read_text(encoding="utf-8")
    for chunk in ("vendor-charts", "vendor-graph", "vendor-mindmap"):
        assert chunk in vite
    assert "location = /index.html" in nginx
    assert "no-cache, no-store, must-revalidate" in nginx
    assert 'Cache-Control "public, immutable"' in nginx
