"""仓库级回归：V1.6.1 假绿（产品矩阵 10/10 + runtime ga_ready=false）不得再签 GA。"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts/aiqe/release_verdict.py"


def _load():
    spec = importlib.util.spec_from_file_location("release_verdict_repo_v162", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MODULE = _load()


def test_repo_verdict_is_not_ga_signed_and_blocks_gate_e():
    verdict = MODULE.build_verdict(REPO_ROOT)
    assert verdict["ga_ready"] is False
    assert verdict["ga_status"] == "GA_NOT_READY"
    assert verdict["release_status"] == "RELEASE_CANDIDATE_BLOCKED"
    gate_e = verdict["gates"]["E"]
    assert gate_e["status"] != "PASS", gate_e
    joined = "\n".join(gate_e["reasons"])
    assert "Runtime index" in joined or "产品 TC" in joined or "runner" in joined
    assert verdict["blocking"], "GA 未签署时必须有 blocking 列表"


def test_require_ga_cli_exits_nonzero_on_repo():
    import subprocess

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--require-ga"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "GA 未签署" in result.stdout
