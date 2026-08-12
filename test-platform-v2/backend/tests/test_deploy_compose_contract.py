"""Security and persistence contracts for the v2 Docker Compose deployment."""
from __future__ import annotations

import json
import re
from pathlib import Path

import yaml


PLATFORM_ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ROOT = PLATFORM_ROOT.parent
BACKEND_ROOT = PLATFORM_ROOT / "backend"
COMPOSE_PATH = PLATFORM_ROOT / "deploy" / "docker-compose.yml"
DOCKERFILE_PATH = BACKEND_ROOT / "Dockerfile"
PYTHON_LOCK_PATH = BACKEND_ROOT / "requirements.lock"
ROOT_DOCKERIGNORE_PATH = REPOSITORY_ROOT / ".dockerignore"
PLAYWRIGHT_ROOT = BACKEND_ROOT / "tests" / "playwright"
LANHU_MODULE_PATH = REPOSITORY_ROOT / "lanhu-mcp" / "lanhu_mcp_server.py"
FRONTEND_ROOT = PLATFORM_ROOT / "frontend"
ACCEPTANCE_LAUNCHER = PLATFORM_ROOT / "scripts" / "start-batch56-acceptance.ps1"


def _compose() -> tuple[str, dict]:
    content = COMPOSE_PATH.read_text(encoding="utf-8")
    return content, yaml.safe_load(content)


def test_compose_keeps_production_knowledge_ingest_opt_in() -> None:
    content, compose = _compose()
    backend_environment = compose["services"]["backend"]["environment"]
    postgres_environment = compose["services"]["postgres"]["environment"]

    assert all(
        "container_name" not in service
        for service in compose["services"].values()
    )
    assert (
        "KNOWLEDGE_INGEST_PRODUCTION_DATA="
        "${KNOWLEDGE_INGEST_PRODUCTION_DATA:-false}"
    ) in backend_environment
    assert "SECRET_KEY=${SECRET_KEY:?SECRET_KEY is required}" in backend_environment
    assert (
        "ADMIN_PASSWORD=${ADMIN_PASSWORD:?ADMIN_PASSWORD is required}"
    ) in backend_environment
    assert (
        "TESTER_PASSWORD=${TESTER_PASSWORD:?TESTER_PASSWORD is required}"
    ) in backend_environment
    assert (
        "ENVIRONMENT=${ENVIRONMENT:?ENVIRONMENT is required}"
    ) in backend_environment
    assert (
        "COOKIE_SECURE=${COOKIE_SECURE:?COOKIE_SECURE is required}"
    ) in backend_environment
    assert "AUTO_CREATE_TABLES=false" in backend_environment
    assert "DATABASE_URL=${DATABASE_URL:?DATABASE_URL is required}" in backend_environment
    assert (
        postgres_environment["POSTGRES_PASSWORD"]
        == "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
    )
    assert re.search(
        r"postgresql(?:\+\w+)?://[^:\s]+:(?!<|\$\{)[^@\s]+@",
        content,
    ) is None


def test_compose_persists_backend_generated_artifacts() -> None:
    _, compose = _compose()
    backend_volumes = compose["services"]["backend"]["volumes"]

    assert "tp-artifacts:/app/storage" in backend_volumes
    assert compose["volumes"]["tp-artifacts"]["driver"] == "local"


def test_artifact_mount_covers_current_runtime_paths() -> None:
    ui_runner = (
        BACKEND_ROOT / "app" / "services" / "playwright_executor.py"
    ).read_text(encoding="utf-8")
    lanhu_evidence = (
        BACKEND_ROOT / "app" / "api" / "v1" / "lanhu_evidence.py"
    ).read_text(encoding="utf-8")

    assert '/ "storage" / "ui-runs"' in ui_runner
    assert '/ "storage" / "lanhu-evidence"' in lanhu_evidence


def test_backend_build_context_contains_runner_and_root_lanhu_submodule() -> None:
    _, compose = _compose()
    backend_build = compose["services"]["backend"]["build"]
    backend_environment = compose["services"]["backend"]["environment"]

    assert backend_build == {
        "context": "../..",
        "dockerfile": "test-platform-v2/backend/Dockerfile",
    }
    assert "WORKSPACE_ROOT=/app" in backend_environment
    assert "LANHU_MCP_DIR=/app/lanhu-mcp" in backend_environment
    assert "DATA_DIR=/app/storage/lanhu-data" in backend_environment
    assert (PLAYWRIGHT_ROOT / "package-lock.json").is_file()
    assert LANHU_MODULE_PATH.is_file()


def test_backend_image_installs_locked_ui_lanhu_and_media_runtime() -> None:
    dockerfile = DOCKERFILE_PATH.read_text(encoding="utf-8")
    package_lock = json.loads(
        (PLAYWRIGHT_ROOT / "package-lock.json").read_text(encoding="utf-8")
    )

    playwright_version = package_lock["packages"]["node_modules/playwright"]["version"]
    test_version = package_lock["packages"]["node_modules/@playwright/test"]["version"]
    assert playwright_version == test_version

    package_copy = (
        "COPY test-platform-v2/backend/tests/playwright/package*.json "
        "./tests/playwright/"
    )
    source_copy = (
        "COPY test-platform-v2/backend/tests/playwright ./tests/playwright"
    )
    assert package_copy in dockerfile
    assert source_copy in dockerfile
    assert dockerfile.index(package_copy) < dockerfile.index("npm ci")
    assert dockerfile.index("npm ci") < dockerfile.index(source_copy)
    assert "npm ci || npm install" not in dockerfile

    assert (
        "lanhu_mcp_server.py /app/lanhu-mcp/lanhu_mcp_server.py"
    ) in dockerfile
    # Batch 63：云构建（Railway 等）不拉 Git 子模块，Dockerfile 改为构建期 clone
    assert "github.com/mojinru9527/lanhu-mcp" in dockerfile
    assert "nodejs" in dockerfile
    assert "npm" in dockerfile
    assert "ffmpeg" in dockerfile
    assert "python -m playwright install chromium" in dockerfile
    assert "playwright install --with-deps chromium" in dockerfile
    assert "PLAYWRIGHT_BROWSERS_PATH=/ms-playwright" in dockerfile
    assert dockerfile.count("python:3.12-slim@sha256:") == 2
    assert (
        "COPY test-platform-v2/backend/requirements.txt "
        "test-platform-v2/backend/requirements.lock ./"
    ) in dockerfile
    assert "pip install --no-cache-dir --require-hashes -r requirements.lock" in dockerfile
    assert (
        'pip install --no-cache-dir --no-deps --force-reinstall '
        '"playwright==${PLAYWRIGHT_VERSION}"'
    ) in dockerfile
    lock = PYTHON_LOCK_PATH.read_text(encoding="utf-8")
    assert "playwright==1.61.0" in lock
    assert "--hash=sha256:" in lock


def test_backend_runtime_uses_non_root_user_and_writable_paths() -> None:
    dockerfile = DOCKERFILE_PATH.read_text(encoding="utf-8")
    _, compose = _compose()
    backend = compose["services"]["backend"]

    assert "python -m venv /opt/venv" in dockerfile
    assert "COPY --from=builder /opt/venv /opt/venv" in dockerfile
    assert "VIRTUAL_ENV=/opt/venv" in dockerfile
    assert "PATH=/opt/venv/bin:$PATH" in dockerfile
    assert "/root/.local" not in dockerfile
    assert "pip install --user" not in dockerfile

    assert "ARG APP_UID=10001" in dockerfile
    assert "ARG APP_GID=10001" in dockerfile
    assert 'groupadd --gid "${APP_GID}" cameltv' in dockerfile
    assert (
        'useradd --uid "${APP_UID}" --gid "${APP_GID}" '
        "--create-home --home-dir /home/cameltv"
    ) in dockerfile
    assert "HOME=/home/cameltv" in dockerfile
    assert "XDG_CACHE_HOME=/home/cameltv/.cache" in dockerfile

    mkdir = "mkdir -p /app/storage /app/storage/lanhu-data /ms-playwright"
    chown = (
        "chown -R cameltv:cameltv "
        "/app /data /ms-playwright /home/cameltv"
    )
    runtime_user = "USER cameltv:cameltv"
    assert mkdir in dockerfile
    assert chown in dockerfile
    assert runtime_user in dockerfile
    assert dockerfile.index(chown) < dockerfile.index(runtime_user)
    assert dockerfile.index("npm ci") < dockerfile.index(runtime_user)
    assert dockerfile.index("lanhu_mcp_server.py") < dockerfile.index(runtime_user)
    assert [
        line.strip()
        for line in dockerfile.splitlines()
        if line.lstrip().startswith("USER ")
    ] == [runtime_user]
    assert backend.get("user") not in {"0", "root", "0:0", "root:root"}


def test_existing_volumes_receive_the_runtime_uid_before_backend_starts() -> None:
    _, compose = _compose()
    initializer = compose["services"]["volume-permissions"]
    backend = compose["services"]["backend"]

    assert initializer["user"] == "0:0"
    assert initializer["command"][-1] == "chown -R 10001:10001 /data /app/storage"
    assert initializer["volumes"] == [
        "tp-data:/data",
        "tp-artifacts:/app/storage",
    ]
    assert backend["depends_on"]["volume-permissions"] == {
        "condition": "service_completed_successfully",
    }


def test_runtime_migration_requires_one_head_and_never_uses_create_all() -> None:
    dockerfile = DOCKERFILE_PATH.read_text(encoding="utf-8")

    assert "alembic heads | grep -c ' (head)$'" in dockerfile
    assert "alembic upgrade head" in dockerfile
    assert "alembic upgrade heads" not in dockerfile


def test_root_dockerignore_bounds_repository_build_context() -> None:
    dockerignore = ROOT_DOCKERIGNORE_PATH.read_text(encoding="utf-8").splitlines()

    assert "**/node_modules/" in dockerignore
    assert "**/test-results/" in dockerignore
    assert "**/.git" in dockerignore
    assert ".ai-worktree.json" in dockerignore


def test_frontend_proxies_forward_performance_websockets() -> None:
    vite_config = (FRONTEND_ROOT / "vite.config.ts").read_text(encoding="utf-8")
    nginx_config = (FRONTEND_ROOT / "nginx.conf").read_text(encoding="utf-8")
    frontend_dockerfile = (FRONTEND_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "changeOrigin: true, ws: true" in vite_config
    assert "proxy_http_version 1.1;" in nginx_config
    assert "proxy_set_header Upgrade $http_upgrade;" in nginx_config
    assert 'proxy_set_header Connection "upgrade";' in nginx_config
    assert "node:22.22-alpine@sha256:" in frontend_dockerfile
    assert "nginx:alpine@sha256:" in frontend_dockerfile


def test_database_image_is_pinned_by_digest() -> None:
    _, compose = _compose()

    assert compose["services"]["postgres"]["image"].startswith(
        "postgres:16-alpine@sha256:",
    )


def test_acceptance_launcher_binds_evidence_to_owned_clean_processes() -> None:
    launcher = ACCEPTANCE_LAUNCHER.read_text(encoding="utf-8")

    assert "Assert-PortIsFree -Port 8000" in launcher
    assert "Assert-PortIsFree -Port 5173" in launcher
    assert "Refusing to reuse an unverified process" in launcher
    assert "ExpectedCommandFragment $backendRoot" in launcher
    assert "ExpectedCommandFragment $frontendRoot" in launcher
    assert "status --porcelain=v1 -- ." in launcher
    assert "working_tree_clean = $workingTreeClean" in launcher
    assert "& npm ci" in launcher
