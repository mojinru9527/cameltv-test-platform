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
    assert "FROM runtime-api-base AS api" in dockerfile
    assert "FROM runtime-ai-base AS ai-gateway" in dockerfile
    assert "FROM runner AS runtime" in dockerfile

    runner = dockerfile[dockerfile.index("FROM runtime-base AS runner"):dockerfile.index("FROM runtime-api-base AS api")]
    api = dockerfile[dockerfile.index("FROM runtime-api-base AS api"):dockerfile.index("FROM runtime-ai-base AS ai-gateway")]
    assert "nodejs" in runner
    assert "playwright install" in runner
    assert "nodejs" not in api
    assert "playwright install" not in api


def test_runner_node_provisioning_fails_loudly_and_ships_npm():
    """C248-8：装 Node 的那层必须自带 node/npm 断言，且不得用会吞掉失败的管道。

    历史缺陷：``curl -fsSL … | bash -``（无 pipefail）在下载失败时静默退化成
    Debian 的 nodejs —— 有 node、没有 npm，构建要到下一步才以 ``npm: not found``
    （exit 127）失败，导致发布被迫改用「复用已验证 runner 镜像」。
    """
    dockerfile = (BACKEND / "Dockerfile").read_text(encoding="utf-8")
    runner = dockerfile[dockerfile.index("FROM runtime-base AS runner"):dockerfile.index("FROM runtime-api-base AS api")]
    # 只看指令行：注释里会引用这个反模式来说明历史缺陷
    instructions = "\n".join(
        line for line in runner.splitlines() if not line.strip().startswith("#")
    )

    assert "| bash -" not in instructions, "curl 管道到 shell 会吞掉下载失败（静默降级）"
    assert "nodesource_setup.sh" in instructions, "NodeSource setup 必须先落盘再执行（失败即中断）"
    assert "process.versions.node" in instructions, "必须断言 Node 主版本（NodeSource 22）"
    assert "npm --version" in instructions, "必须断言 npm 存在（静默降级时正是缺 npm）"


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
    assert services["ai-gateway"]["build"]["target"] == "ai-gateway"
    assert services["backend"]["environment"]["AI_GATEWAY_URL"] == "http://ai-gateway:8100"


def test_frontend_heavy_chunks_and_spa_shell_cache_policy():
    vite = (FRONTEND / "vite.config.ts").read_text(encoding="utf-8")
    nginx = (FRONTEND / "nginx.conf").read_text(encoding="utf-8")
    for chunk in ("vendor-charts", "vendor-graph", "vendor-mindmap"):
        assert chunk in vite
    assert "location = /index.html" in nginx
    assert "no-cache, no-store, must-revalidate" in nginx
    assert 'Cache-Control "public, immutable"' in nginx

def test_python_dependency_layers_are_split_by_runtime_role():
    api = (BACKEND / "requirements.api.lock").read_text(encoding="utf-8")
    ai = (BACKEND / "requirements.ai.lock").read_text(encoding="utf-8")
    runner = (BACKEND / "requirements.runner.lock").read_text(encoding="utf-8")

    for heavy in ("fastembed==", "onnxruntime==", "numpy==", "playwright=="):
        assert heavy not in api
    for ai_pkg in ("fastembed==", "onnxruntime==", "numpy=="):
        assert ai_pkg in ai
    assert "playwright==" not in ai
    for runner_pkg in ("fastembed==", "onnxruntime==", "numpy==", "playwright=="):
        assert runner_pkg in runner
    for ocr_pkg in ("rapidocr-onnxruntime==", "opencv-python==", "pyclipper==", "shapely=="):
        assert ocr_pkg in runner
        assert ocr_pkg not in api
        assert ocr_pkg not in ai
