"""V16-025 发布审计脚本验收（secrets / fake E2E / migration / traceability / docs）。"""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "aiqe" / "check_release_audit.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_release_audit", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


MODULE = _load()


def test_secrets_and_e2e_scans(tmp_path):
    app = tmp_path / "app"
    app.mkdir()
    (app / "bad.py").write_text("DEFAULT_PASSWORD = 'admin123'\n", encoding="utf-8")
    assert MODULE.scan_secrets(app)

    e2e = tmp_path / "tests" / "e2e" / "aiqe"
    e2e.mkdir(parents=True)
    (e2e / "test_tc_aiqe_001_010.py").write_text("def test_x(): pass\n", encoding="utf-8")
    (e2e / "test_skip.py").write_text(
        "import pytest\npytestmark = pytest.mark.skipif(True, reason='x')\n", encoding="utf-8"
    )
    errors = MODULE.scan_e2e_tests(e2e)
    assert any("FAKE_E2E" in item for item in errors)
    assert any("SKIP_E2E" in item for item in errors)


def test_migrations_require_downgrade(tmp_path):
    versions = tmp_path / "versions"
    versions.mkdir()
    (versions / "20261119_v16_999_x.py").write_text("def upgrade(): pass\n", encoding="utf-8")
    errors = MODULE.scan_migrations(versions)
    assert any("downgrade" in item for item in errors)


def test_requirements_status_rules(tmp_path):
    path = tmp_path / "requirements.yaml"
    path.write_text(
        """
requirements:
  - id: X1
    status: VERIFIED
    tests: {}
    evidence: []
  - id: X2
    status: BLOCKED
    blocked_reason: ""
""",
        encoding="utf-8",
    )
    errors = MODULE.check_requirements(path)
    assert any("X1" in item and "VERIFIED" in item for item in errors)
    assert any("X2" in item and "blocked_reason" in item for item in errors)


def test_docs_rejects_fake_claim_but_allows_negation(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "bad.md").write_text("V1.6 已 GA 通过，10/10 PASS\n", encoding="utf-8")
    (docs / "ok.md").write_text("不得宣称 PRODUCTION_OBSERVED；当前未 GA 通过。\n", encoding="utf-8")
    errors = MODULE.scan_docs(docs)
    assert any("bad.md" in item for item in errors)
    assert not any("ok.md" in item for item in errors)


def test_repo_release_audit_is_clean():
    report = MODULE.run_audit(ROOT)
    assert report["ok"], report["errors"]


def _verdict(**overrides) -> dict:
    verdict = {
        "ga_ready": False,
        "ga_status": "GA_NOT_READY",
        "summary": {
            "requirements": 2,
            "verified": 1,
            "accepted": 0,
            "partial": 1,
            "product_tc_pass": 0,
            "product_tc_total": 10,
        },
        "gates": {
            "E": {"status": "NOT_PROVEN"},
            "F": {"status": "NOT_PROVEN"},
            "G": {"status": "NOT_PROVEN"},
        },
    }
    verdict.update(overrides)
    return verdict


def _docs_with_matrix(tmp_path: Path) -> Path:
    docs = tmp_path / "docs"
    (docs / "traceability").mkdir(parents=True)
    (docs / "traceability" / "requirements.yaml").write_text(
        """
requirements:
  - id: V16-001-R1
    issue: V16-001
    status: VERIFIED
  - id: TC-AIQE-001
    issue: TC-AIQE-001
    status: PARTIAL
    e2e:
      product:
        status: PARTIAL
      platform:
        tc_ids: [TC-PLATFORM-010]
""",
        encoding="utf-8",
    )
    return docs


def test_doc_consistency_rejects_product_tc_claim(tmp_path):
    docs = _docs_with_matrix(tmp_path)
    (docs / "claim.md").write_text("| TC-AIQE-001 | 契约冻结 | VERIFIED |\n", encoding="utf-8")
    errors = MODULE.check_doc_consistency(_verdict(), docs)
    assert any("TC-AIQE-001" in item for item in errors)


def test_doc_consistency_rejects_ten_of_ten_claim(tmp_path):
    docs = _docs_with_matrix(tmp_path)
    (docs / "claim.md").write_text("产品级 TC 10/10 全部通过。\n", encoding="utf-8")
    errors = MODULE.check_doc_consistency(_verdict(), docs)
    assert any("10/10" in item for item in errors)


def test_doc_consistency_allows_negated_claims(tmp_path):
    docs = _docs_with_matrix(tmp_path)
    (docs / "claim.md").write_text(
        "不得宣称 10/10；TC-AIQE-001 当前不是 VERIFIED。\n", encoding="utf-8"
    )
    errors = MODULE.check_doc_consistency(_verdict(), docs)
    assert not errors


def test_doc_consistency_rejects_gate_checkbox(tmp_path):
    docs = _docs_with_matrix(tmp_path)
    (docs / "V1.6-GA-Release-Report.md").write_text(
        "# GA\n\n### Gate E：Driver / E2E\n- [x] 产品级 TC 全部通过\n", encoding="utf-8"
    )
    errors = MODULE.check_doc_consistency(_verdict(), docs)
    assert any("Gate E" in item for item in errors)


def test_doc_consistency_skips_historical_docs(tmp_path):
    docs = _docs_with_matrix(tmp_path)
    (docs / "old.md").write_text(
        "# 旧记录\n\n> STATUS: HISTORICAL\n\n产品级 TC 10/10 全部通过。\n", encoding="utf-8"
    )
    errors = MODULE.check_doc_consistency(_verdict(), docs)
    assert not errors


def test_doc_consistency_rejects_production_deployed(tmp_path):
    docs = _docs_with_matrix(tmp_path)
    (docs / "claim.md").write_text("发布状态：PRODUCTION_DEPLOYED\n", encoding="utf-8")
    errors = MODULE.check_doc_consistency(_verdict(), docs)
    assert any("PRODUCTION_DEPLOYED" in item for item in errors)
