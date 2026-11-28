"""FIX-015：最终验收报告生成器（机器 Gate + 人工 disposition 交叉校验）。"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts/aiqe/build_v162_final_acceptance.py"


def _load():
    spec = importlib.util.spec_from_file_location("build_v162_final_acceptance", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MODULE = _load()


def test_report_blocks_ga_and_flags_missing_disposition(tmp_path: Path):
    docs = tmp_path / "docs/aiqe/v1.6"
    docs.mkdir(parents=True)
    (docs / "release-verdict.json").write_text(
        json.dumps(
            {
                "commit_sha": "a" * 40,
                "ga_ready": False,
                "gates": {"E": {"status": "NOT_PROVEN", "evidence": "NOT_PROVEN", "acceptance": "PENDING"}},
            }
        ),
        encoding="utf-8",
    )
    (docs / "e2e").mkdir()
    (docs / "e2e/product-results.json").write_text(json.dumps({"tests": []}), encoding="utf-8")
    disposition = tmp_path / "disp.yaml"
    disposition.write_text(yaml.safe_dump({"fixes": [], "known_gaps": ["g1"]}), encoding="utf-8")

    text, meta = MODULE.build_report(tmp_path, disposition_path=disposition)
    assert meta["decision"] == "RELEASE_CANDIDATE_BLOCKED"
    assert "RELEASE_CANDIDATE_BLOCKED" in text
    assert any("FIX-001" in error for error in meta["errors"])


def test_verified_without_evidence_is_error(tmp_path: Path):
    docs = tmp_path / "docs/aiqe/v1.6"
    docs.mkdir(parents=True)
    (docs / "release-verdict.json").write_text(json.dumps({"ga_ready": False}), encoding="utf-8")
    disposition = tmp_path / "disp.yaml"
    fixes = [{"fix": f"FIX-{index:03d}", "status": "BLOCKED", "reason": "x"} for index in range(1, 16)]
    fixes[0] = {"fix": "FIX-001", "status": "VERIFIED"}
    disposition.write_text(yaml.safe_dump({"fixes": fixes}), encoding="utf-8")
    _, meta = MODULE.build_report(tmp_path, disposition_path=disposition)
    assert any("FIX-001" in error and "evidence" in error for error in meta["errors"])
