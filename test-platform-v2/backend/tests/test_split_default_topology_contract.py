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


# ── P0-4 凭据最小化契约 ──────────────────────────────────────────────
# 背景：生产审计发现 backend / runner / aitde-worker / ai-gateway 四个容器
# 都带着同一份明文 AI_API_KEY 与 DSH_API_KEY。remote 角色的服务把 LLM 调用
# 经 AI_GATEWAY_URL 委派给 ai-gateway，本不需要云端明文 Key；Key 每多复制
# 一份就多一个泄漏面（本次事故即为 Key 泄漏后被外部持续调用）。
# 下列静态契约保证「凭据只在真正消费它的地方出现」，防止再次扩散。

TEMPORAL_COMPOSE = DEPLOY_ROOT / "aitde-runtime" / "docker-compose.yml"

# 服务名 → 该服务是否允许持有明文凭据
AI_KEY_HOLDERS = ("ai-gateway",)
DSH_KEY_HOLDERS = ("runner", "aitde-worker")


def _env_keys(service: dict) -> set[str]:
    """把 list 形式与 mapping 形式的 environment 统一成键名集合。"""
    environment = service.get("environment") or []
    if isinstance(environment, dict):
        return set(environment)
    return {str(item).split("=", 1)[0] for item in environment}


def _env_items(service: dict) -> dict[str, str]:
    environment = service.get("environment") or []
    if isinstance(environment, dict):
        return {str(k): str(v) for k, v in environment.items()}
    out: dict[str, str] = {}
    for item in environment:
        key, _, value = str(item).partition("=")
        out[key] = value
    return out


def test_split_topology_scopes_plaintext_ai_key_to_gateway_only() -> None:
    services = _load(BASE_COMPOSE)["services"]

    for name, service in services.items():
        has_key = "AI_API_KEY" in _env_keys(service)
        if name in AI_KEY_HOLDERS:
            assert has_key, f"{name} 是 AI 凭据持有者，必须注入 AI_API_KEY"
        else:
            assert not has_key, (
                f"{name} 不得持有明文 AI_API_KEY（P0-4 凭据最小化）；"
                "它应经 AI_GATEWAY_URL 委派给 ai-gateway"
            )


def test_split_topology_scopes_dsh_key_to_executors_only() -> None:
    services = _load(BASE_COMPOSE)["services"]

    for name, service in services.items():
        has_key = "DSH_API_KEY" in _env_keys(service)
        if name in DSH_KEY_HOLDERS:
            assert has_key, f"{name} 会派生 DSH 子进程，必须注入 DSH_API_KEY"
        else:
            assert not has_key, (
                f"{name} 不得持有明文 DSH_API_KEY（P0-4 凭据最小化）；"
                "只有 WORKER_EXECUTION_ENABLED=true 的执行服务需要它"
            )


def test_combined_rollback_restores_in_process_credentials() -> None:
    """回滚到合并镜像后本进程同时承担 API/AI/DSH，凭据必须回到 backend。"""
    backend_env = _env_items(_load(COMBINED_OVERLAY)["services"]["backend"])

    assert backend_env["AI_GATEWAY_ROLE"] == "embedded"
    assert "AI_API_KEY" in backend_env
    assert "DSH_API_KEY" in backend_env


def test_public_ingress_binds_loopback_by_default() -> None:
    """P0-5：前端与 Temporal 都只允许经 Caddy 反代进入，不得直接绑 0.0.0.0。"""
    frontend_ports = _load(BASE_COMPOSE)["services"]["frontend"]["ports"]
    assert all(str(p).startswith("${FRONTEND_BIND:-127.0.0.1}:") for p in frontend_ports), (
        f"frontend 必须默认绑定回环，当前为 {frontend_ports}"
    )

    temporal_ports = _load(TEMPORAL_COMPOSE)["services"]["temporal"]["ports"]
    published = [p for p in temporal_ports if "7233" in str(p) or "8080" in str(p)]
    assert published, "temporal 必须显式声明 gRPC/UI 端口绑定"
    for binding in published:
        assert str(binding).startswith(
            ("${TEMPORAL_GRPC_BIND:-127.0.0.1}:", "${TEMPORAL_UI_BIND:-127.0.0.1}:")
        ), f"Temporal 端口必须默认绑定回环，当前为 {binding}"


def test_remote_role_without_local_key_is_not_a_security_issue(monkeypatch) -> None:
    """委派链路完整时，「本地没有明文 Key」是设计而非缺陷，不得报警。"""
    from app.core import config

    monkeypatch.setattr(config.settings, "environment", "production")
    monkeypatch.setattr(config.settings, "secret_key", "a" * 64)
    monkeypatch.setattr(config.settings, "admin_password", "Str0ng-Passw0rd!")
    monkeypatch.setattr(config.settings, "cookie_secure", True)
    monkeypatch.setattr(config.settings, "ai_enabled", True)
    monkeypatch.setattr(config.settings, "ai_api_key", "")
    monkeypatch.setattr(config.settings, "ai_gateway_url", "http://ai-gateway:8100")
    monkeypatch.setattr(config.settings, "ai_gateway_token", "delegated-token")
    monkeypatch.setattr(config.settings, "ai_gateway_role", "remote")
    monkeypatch.setattr(config.settings, "worker_execution_enabled", False)
    monkeypatch.setattr(config.settings, "dsh_enabled", True)
    monkeypatch.setattr(config.settings, "dsh_api_key", "")

    issues = config.settings.validate_security()

    assert not [i for i in issues if "AI_API_KEY" in i], issues
    assert not [i for i in issues if "DSH" in i], issues
    assert config.settings.ai_gateway_delegated is True


def test_embedded_role_without_key_is_still_flagged(monkeypatch) -> None:
    """没有委派链路时（embedded），缺 Key 仍是真实配置缺陷。"""
    from app.core import config

    monkeypatch.setattr(config.settings, "environment", "production")
    monkeypatch.setattr(config.settings, "secret_key", "a" * 64)
    monkeypatch.setattr(config.settings, "admin_password", "Str0ng-Passw0rd!")
    monkeypatch.setattr(config.settings, "cookie_secure", True)
    monkeypatch.setattr(config.settings, "ai_enabled", True)
    monkeypatch.setattr(config.settings, "ai_api_key", "")
    monkeypatch.setattr(config.settings, "ai_gateway_url", "")
    monkeypatch.setattr(config.settings, "ai_gateway_token", "")
    monkeypatch.setattr(config.settings, "ai_gateway_role", "embedded")
    monkeypatch.setattr(config.settings, "worker_execution_enabled", True)
    monkeypatch.setattr(config.settings, "dsh_enabled", True)
    monkeypatch.setattr(config.settings, "dsh_api_key", "")

    issues = config.settings.validate_security()

    assert config.settings.ai_gateway_delegated is False
    assert [i for i in issues if "AI_API_KEY" in i], issues
    assert [i for i in issues if "DSH" in i], issues
