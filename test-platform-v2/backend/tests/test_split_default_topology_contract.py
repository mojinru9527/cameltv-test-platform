"""Contracts for the split-by-default AI topology (Batch 241).

The repository default is the split topology: a slim ``api`` image plus a
separate ``ai-gateway`` and ``runner``. The combined ``runtime`` image is kept
as a rollback path behind ``docker-compose.combined.yml``.

These tests are static (no Docker daemon required) so they can gate every PR.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

PLATFORM_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PLATFORM_ROOT / "backend"
DEPLOY_ROOT = PLATFORM_ROOT / "deploy"

BASE_COMPOSE = DEPLOY_ROOT / "docker-compose.yml"
COMBINED_OVERLAY = DEPLOY_ROOT / "docker-compose.combined.yml"
SPLIT_OVERLAY = DEPLOY_ROOT / "docker-compose.execution.yml"

API_LOCK = BACKEND_ROOT / "requirements.api.lock"
AI_LOCK = BACKEND_ROOT / "requirements.ai.lock"
RUNNER_LOCK = BACKEND_ROOT / "requirements.runner.lock"

# Linux-only transitive dependencies that a Windows-resolved lock drops,
# which then breaks ``pip install --require-hashes`` inside the image build.
LINUX_ONLY_REQUIREMENTS = ("secretstorage", "jeepney", "uvloop")


class _ComposeLoader(yaml.SafeLoader):
    """SafeLoader that understands the Compose merge tags.

    ``!reset`` discards the value inherited from an earlier ``-f`` file; for the
    purpose of static contract checks the following node is what matters.
    """


def _compose_tag(loader: yaml.SafeLoader, node: yaml.Node):  # noqa: ANN001
    if isinstance(node, yaml.MappingNode):
        return loader.construct_mapping(node, deep=True)
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node, deep=True)
    return loader.construct_scalar(node)


_ComposeLoader.add_constructor("!reset", _compose_tag)
_ComposeLoader.add_constructor("!override", _compose_tag)


def _load(path: Path) -> dict:
    return yaml.load(path.read_text(encoding="utf-8"), Loader=_ComposeLoader)


def test_base_compose_defaults_to_split_topology() -> None:
    compose = _load(BASE_COMPOSE)
    services = compose["services"]

    assert "ai-gateway" in services, "default topology must ship the AI gateway"
    assert "runner" in services, "default topology must ship the browser runner"
    assert services["backend"]["build"]["target"] == "api"
    assert services["ai-gateway"]["build"]["target"] == "ai-gateway"
    assert services["runner"]["build"]["target"] == "runner"
    assert services["volume-permissions"]["build"]["target"] == "api"


def test_backend_delegates_to_gateway_and_runner() -> None:
    services = _load(BASE_COMPOSE)["services"]
    backend_environment = "\n".join(services["backend"]["environment"])

    assert "AI_GATEWAY_URL=${AI_GATEWAY_URL:-http://ai-gateway:8100}" in backend_environment
    assert "AI_GATEWAY_ROLE=${AI_GATEWAY_ROLE:-remote}" in backend_environment
    assert "RUNNER_HTTP_URL=${RUNNER_HTTP_URL:-http://runner:8000}" in backend_environment


def test_combined_overlay_restores_single_runtime_image() -> None:
    overlay = _load(COMBINED_OVERLAY)["services"]

    assert overlay["backend"]["build"]["target"] == "runtime"
    assert overlay["volume-permissions"]["build"]["target"] == "runtime"
    assert overlay["aitde-worker"]["build"]["target"] == "runtime"
    # Disabled by profile so the rollback does not start the split services.
    assert overlay["ai-gateway"]["profiles"] == ["combined-disabled"]
    assert overlay["runner"]["profiles"] == ["combined-disabled"]
    # AI runs in-process again after a rollback.
    assert overlay["backend"]["environment"]["AI_GATEWAY_ROLE"] == "embedded"


def test_release_split_overlay_is_fail_closed() -> None:
    content = SPLIT_OVERLAY.read_text(encoding="utf-8")

    assert "${AI_GATEWAY_TOKEN:?AI_GATEWAY_TOKEN is required}" in content
    assert "${AI_GATEWAY_IMAGE:?AI_GATEWAY_IMAGE is required}" in content


@pytest.mark.parametrize(
    "path,forbidden",
    [
        (API_LOCK, ("fastembed", "onnxruntime", "numpy", "playwright")),
        (AI_LOCK, ("playwright",)),
    ],
)
def test_lock_boundaries(path: Path, forbidden: tuple[str, ...]) -> None:
    content = path.read_text(encoding="utf-8")
    for name in forbidden:
        assert not re.search(
            rf"^{re.escape(name)}==", content, re.MULTILINE
        ), f"{path.name} must not pin {name}"


def test_ai_lock_keeps_ai_runtime() -> None:
    content = AI_LOCK.read_text(encoding="utf-8")
    for name in ("fastembed", "onnxruntime", "numpy"):
        assert re.search(rf"^{re.escape(name)}==", content, re.MULTILINE)


@pytest.mark.parametrize("path", [API_LOCK, AI_LOCK, RUNNER_LOCK])
def test_locks_carry_linux_only_transitives(path: Path) -> None:
    content = path.read_text(encoding="utf-8")
    for name in LINUX_ONLY_REQUIREMENTS:
        assert re.search(
            rf"^{re.escape(name)}==", content, re.MULTILINE
        ), f"{path.name} is missing linux-only dependency {name}"


def test_gateway_health_fails_closed_without_token(monkeypatch) -> None:
    from fastapi.testclient import TestClient

    from app import ai_gateway_app
    from app.core import config

    monkeypatch.setattr(config.settings, "ai_gateway_token", "")
    client = TestClient(ai_gateway_app.app)

    response = client.get("/internal/ai/v1/health")

    assert response.status_code == 503
    assert "token" in response.json()["detail"].lower()


def test_gateway_health_reports_ok_with_token(monkeypatch) -> None:
    from fastapi.testclient import TestClient

    from app import ai_gateway_app
    from app.core import config

    monkeypatch.setattr(config.settings, "ai_gateway_token", "smoke-token")
    client = TestClient(ai_gateway_app.app)

    response = client.get("/internal/ai/v1/health")

    assert response.status_code == 200
    assert response.json()["data"]["token_configured"] is True
