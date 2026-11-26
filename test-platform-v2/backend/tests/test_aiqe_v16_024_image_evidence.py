"""V16-024/P1-9：镜像证据采集脚本的离线单测。"""
from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts/aiqe/capture_image_evidence.py"


def _load():
    spec = importlib.util.spec_from_file_location("capture_image_evidence", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


MODULE = _load()


def test_sha256_file_matches_hashlib(tmp_path):
    import hashlib

    target = tmp_path / "image.tar"
    payload = b"cameltv-image-evidence" * 1024
    target.write_bytes(payload)
    assert MODULE._sha256_file(target) == hashlib.sha256(payload).hexdigest()


def test_git_head_is_full_sha():
    head = MODULE._git_head()
    assert len(head) == 40, head
    assert all(char in "0123456789abcdef" for char in head)


def test_default_output_lives_in_repo_evidence():
    assert MODULE.DEFAULT_OUTPUT.parent == REPO_ROOT / "docs/aiqe/v1.6/evidence"


RUNTIME_SCRIPT = REPO_ROOT / "scripts/aiqe/verify_image_runtime.py"


def _load_runtime():
    spec = importlib.util.spec_from_file_location("verify_image_runtime", RUNTIME_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


RUNTIME = _load_runtime()


def test_single_head_accepts_exactly_one_head_line():
    output = "20261122_v16_catalog_post_merge (batch27) (head)\n"
    assert RUNTIME._single_head(output) == "20261122_v16_catalog_post_merge (batch27) (head)"


def test_single_head_rejects_multiple_or_empty():
    assert RUNTIME._single_head("a (head)\nb (head)\n") == ""
    assert RUNTIME._single_head("a\nb\n") == ""
