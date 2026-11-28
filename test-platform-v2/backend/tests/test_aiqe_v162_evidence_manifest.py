"""FIX-015：Release Evidence Manifest 生成与缺失阻断。"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts/aiqe/build_evidence_manifest.py"


def _load():
    spec = importlib.util.spec_from_file_location("build_evidence_manifest", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MODULE = _load()


def test_manifest_computes_hash_and_marks_missing(tmp_path: Path):
    (tmp_path / "a.json").write_text('{"ok": true}\n', encoding="utf-8")
    specs = (
        {"kind": "x", "path": "a.json", "job": "job-a"},
        {"kind": "y", "path": "missing.json", "job": "job-b"},
    )
    manifest = MODULE.build_manifest(tmp_path, commit_sha="a" * 40, specs=specs)
    assert manifest["complete"] is False
    assert manifest["missing"] == ["missing.json"]
    present = manifest["entries"][0]
    assert len(present["sha256"]) == 64
    assert present["size_bytes"] == (tmp_path / "a.json").stat().st_size


def test_cli_require_complete_nonzero(tmp_path: Path):
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--root",
            str(tmp_path),
            "--commit-sha",
            "b" * 40,
            "--output",
            str(tmp_path / "manifest.json"),
            "--require-complete",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert result.returncode != 0
    payload = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert payload["complete"] is False
    assert payload["missing"]
