"""Batch 261 / B4-1 — 证据包定型：manifest sha256 + 完整性校验 + 篡改可见。

DoD（backlog B4-1）：改一字节 → 校验失败并显红。

本文件同时钉住两条**容易做错**的语义（Design §2）：
  1. 完整率判定**复用**既有 `EvidenceCompletenessPolicy`，不新建第二套口径；
  2. **被篡改/缺失的文件不算满足必需证据** —— 否则会出现"证据被改过、完整率仍 100%、放行照样成立"。
"""
from __future__ import annotations

import pytest

from app.core.config import settings
from app.modules.aitde.common.enums import AdapterType, EvidenceType, OracleType
from app.services import evidence_bundle_service as ebs
from app.services import execution_evidence_store as store


@pytest.fixture(autouse=True)
def _isolated_root(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "execution_evidence_storage_dir", str(tmp_path / "ev"))


def _api_bundle(job_id: int = 1, attempt: int = 1) -> dict:
    """一个完整的 API 任务证据包：REQUEST + RESPONSE。"""
    return store.save_bundle(
        job_id=job_id,
        attempt=attempt,
        files=[
            ("case-1.request.json", b'{"method":"GET","url":"/api/home"}'),
            ("case-1.response.json", b'{"status_code":200}'),
            ("results.json", b'{"total":1,"passed":1}'),
        ],
    )


class TestFileTypeMapping:
    def test_maps_known_suffixes(self):
        assert ebs.evidence_type_for("case-1.request.json") == EvidenceType.REQUEST.value
        assert ebs.evidence_type_for("case-1.response.json") == EvidenceType.RESPONSE.value
        assert ebs.evidence_type_for("case-1.png") == EvidenceType.SCREENSHOT.value
        assert ebs.evidence_type_for("case-1.console.json") == EvidenceType.CONSOLE.value
        assert ebs.evidence_type_for("run.trace.zip") == EvidenceType.PW_TRACE.value

    def test_summary_files_are_not_evidence(self):
        assert ebs.evidence_type_for("results.json") is None
        assert ebs.evidence_type_for("manifest.json") is None

    def test_unknown_suffix_is_not_silently_dropped(self):
        """未知类型必须显式可见（P3-1），否则"有新证据没被校验"会被 100% 完整率掩盖。"""
        assert ebs.evidence_type_for("weird.bin") is None

    @pytest.mark.parametrize(
        "kind,expected",
        [
            ("api", (AdapterType.API.value, OracleType.API.value)),
            ("web", (AdapterType.UI.value, OracleType.UI.value)),
        ],
    )
    def test_adapter_oracle_from_kind(self, kind, expected):
        assert ebs.adapter_oracle_for_kind(kind) == expected

    def test_unknown_kind_falls_back_conservatively(self):
        adapter, oracle = ebs.adapter_oracle_for_kind("soap")
        assert adapter == AdapterType.MANUAL.value
        assert oracle == OracleType.UI.value


class TestVerifyPassingBundle:
    def test_untouched_bundle_is_verified_and_complete(self):
        _api_bundle()
        result = ebs.verify_bundle(1, 1, kind="api")
        assert result["verdict"] == "verified"
        assert result["tampered"] == []
        assert result["missing"] == []
        assert result["completeness"]["complete"] is True
        assert result["completeness"]["required"] == [
            EvidenceType.REQUEST.value,
            EvidenceType.RESPONSE.value,
        ]
        assert {f["status"] for f in result["files"]} == {"ok"}

    def test_files_carry_evidence_type(self):
        _api_bundle()
        result = ebs.verify_bundle(1, 1, kind="api")
        by_name = {f["name"]: f for f in result["files"]}
        assert by_name["case-1.request.json"]["evidence_type"] == EvidenceType.REQUEST.value
        assert by_name["case-1.response.json"]["evidence_type"] == EvidenceType.RESPONSE.value


class TestTamperDetection:
    def test_one_byte_change_is_detected_and_breaks_completeness(self):
        """DoD 的核心：改一字节 → 校验失败，且该证据不再满足必需证据。"""
        _api_bundle()
        target = store.bundle_dir(1, 1) / "case-1.response.json"
        original = target.read_bytes()
        target.write_bytes(original[:-1] + b"9" if original[-1:] != b"9" else original[:-1] + b"8")

        result = ebs.verify_bundle(1, 1, kind="api")

        assert result["verdict"] == "tampered"
        assert result["tampered"] == ["case-1.response.json"]
        responsefile = next(f for f in result["files"] if f["name"] == "case-1.response.json")
        assert responsefile["status"] == "tampered"
        assert responsefile["expected_sha256"] != responsefile["actual_sha256"]
        # 关键语义：被改过的 RESPONSE 不再计入必需证据
        assert EvidenceType.RESPONSE.value not in result["completeness"]["present"]
        assert EvidenceType.RESPONSE.value in result["completeness"]["missing"]
        assert result["completeness"]["complete"] is False

    def test_deleted_file_is_reported_missing(self):
        _api_bundle()
        (store.bundle_dir(1, 1) / "case-1.request.json").unlink()
        result = ebs.verify_bundle(1, 1, kind="api")
        assert result["verdict"] == "missing"
        assert "case-1.request.json" in result["missing"]
        assert result["completeness"]["complete"] is False

    def test_extra_file_is_reported_but_not_fatal(self):
        _api_bundle()
        (store.bundle_dir(1, 1) / "sneaky.txt").write_bytes(b"x")
        result = ebs.verify_bundle(1, 1, kind="api")
        assert result["extra"] == ["sneaky.txt"]
        # 多余文件不改变完整率（必需证据仍齐），但要可见
        assert result["completeness"]["complete"] is True

    def test_missing_bundle_is_reported_not_crashed(self):
        result = ebs.verify_bundle(999, 1, kind="api")
        assert result["verdict"] == "missing"
        assert result["files"] == []
        assert result.get("reason")


class TestCompletenessPerKind:
    def test_web_bundle_requires_screenshot_and_console(self):
        store.save_bundle(
            job_id=2,
            attempt=1,
            files=[("case-1.png", b"\x89PNG"), ("case-1.console.json", b"[]")],
        )
        result = ebs.verify_bundle(2, 1, kind="web")
        assert result["completeness"]["required"] == [
            EvidenceType.SCREENSHOT.value,
            EvidenceType.CONSOLE.value,
        ]
        assert result["completeness"]["complete"] is True

    def test_web_bundle_missing_console_is_incomplete(self):
        store.save_bundle(job_id=3, attempt=1, files=[("case-1.png", b"\x89PNG")])
        result = ebs.verify_bundle(3, 1, kind="web")
        assert result["verdict"] == "incomplete"
        assert EvidenceType.CONSOLE.value in result["completeness"]["missing"]

    def test_completeness_reuses_existing_policy(self):
        """收敛断言：必需证据清单必须来自既有策略，而不是本服务另写一份。"""
        from app.modules.aitde.assertion import completeness

        for kind, (adapter, oracle) in (
            ("api", ebs.adapter_oracle_for_kind("api")),
            ("web", ebs.adapter_oracle_for_kind("web")),
        ):
            store.save_bundle(job_id=7, attempt=1, files=[("x.bin", b"x")])
            result = ebs.verify_bundle(7, 1, kind=kind)
            assert result["completeness"]["required"] == completeness.required_evidence(adapter, oracle)
