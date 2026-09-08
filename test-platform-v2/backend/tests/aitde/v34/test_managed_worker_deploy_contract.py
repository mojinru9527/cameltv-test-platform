"""Deployment contracts for the managed Durable Runtime Worker."""

from pathlib import Path

import yaml


PLATFORM_ROOT = Path(__file__).resolve().parents[4]
COMPOSE_PATH = PLATFORM_ROOT / "deploy" / "docker-compose.yml"
DOCKERFILE_PATH = PLATFORM_ROOT / "backend" / "Dockerfile"
WORKER_LAUNCHER = (
    PLATFORM_ROOT / "deploy" / "aitde-runtime" / "scripts" / "start-worker.sh"
)
PRODUCTION_PROFILE = PLATFORM_ROOT / "config" / "runtime" / "production.env.example"


def _compose() -> dict:
    return yaml.safe_load(COMPOSE_PATH.read_text(encoding="utf-8"))


def test_compose_manages_durable_worker_lifecycle() -> None:
    worker = _compose()["services"]["aitde-worker"]

    assert worker["profiles"] == ["aitde-worker"]
    assert worker["extends"] == {"service": "backend"}
    assert worker["depends_on"]["backend"] == {"condition": "service_healthy"}
    assert worker["restart"] == "unless-stopped"
    assert worker["init"] is True
    assert worker["command"][0] == "/usr/local/bin/start-aitde-worker"
    assert "kill -0" in worker["healthcheck"]["test"][-1]

    environment = worker["environment"]
    assert "BACKEND_APP_DIR=/app" in environment
    assert "BACKEND_URL=http://backend:8000/api/v2" in environment
    assert "API_TOKEN=${AITDE_WORKER_API_TOKEN:-}" in environment
    assert (
        "WORKER_HEARTBEAT_SECONDS=${AITDE_WORKER_HEARTBEAT_SECONDS:-60}"
        in environment
    )


def test_backend_and_worker_define_the_same_temporal_routing() -> None:
    services = _compose()["services"]
    expected = {
        "TEMPORAL_ENABLED=${TEMPORAL_ENABLED:-false}",
        "TEMPORAL_GRPC_ENDPOINT=${TEMPORAL_GRPC_ENDPOINT:-127.0.0.1:7233}",
        "TEMPORAL_NAMESPACE=${TEMPORAL_NAMESPACE:-default}",
        "TEMPORAL_TASK_QUEUE=${TEMPORAL_TASK_QUEUE:-worker-test}",
    }

    assert expected <= set(services["backend"]["environment"])
    assert expected <= set(services["aitde-worker"]["environment"])


def test_backend_image_contains_managed_worker_launcher() -> None:
    dockerfile = DOCKERFILE_PATH.read_text(encoding="utf-8")
    launcher = WORKER_LAUNCHER.read_text(encoding="utf-8")

    assert (
        "COPY --chmod=0555 test-platform-v2/deploy/aitde-runtime/scripts/start-worker.sh "
        "/usr/local/bin/start-aitde-worker" in dockerfile
    )
    assert dockerfile.index('FROM runtime-base AS runner') < dockerfile.index('start-worker.sh') < dockerfile.index('FROM runtime-base AS api')
    assert 'BACKEND_APP_DIR=${BACKEND_APP_DIR:-' in launcher
    assert 'cd "$BACKEND_APP_DIR"' in launcher
    assert 'heartbeat.pid' in launcher
    assert 'gateway.pid' in launcher


def test_production_profile_enables_managed_worker_without_real_credentials() -> None:
    profile = PRODUCTION_PROFILE.read_text(encoding="utf-8")

    assert "COMPOSE_PROFILES=aitde-worker" in profile
    assert "AITDE_V3_ENABLED=true" in profile
    assert "TEMPORAL_ENABLED=true" in profile
    assert "TEMPORAL_GRPC_ENDPOINT=aitde-temporal:7233" in profile
    assert "AITDE_WORKER_API_TOKEN=change-me-production-worker-token" in profile
    assert "AITDE_WORKER_HEARTBEAT_SECONDS=60" in profile
