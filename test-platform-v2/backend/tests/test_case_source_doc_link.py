"""C68-2 — TestCaseUpdate.source_doc_id 与校验（batch-69）。"""
from __future__ import annotations

from unittest.mock import MagicMock

from app.schemas import test_case as test_case_schema
from app.services.test_case_service import validate_source_doc


class TestCaseUpdateSchema:
    def test_source_doc_id_optional(self):
        # 不传 source_doc_id 不报错（向后兼容）
        u = test_case_schema.TestCaseUpdate(title="x")
        assert u.source_doc_id is None

    def test_source_doc_id_accepted(self):
        u = test_case_schema.TestCaseUpdate(source_doc_id=4)
        assert u.source_doc_id == 4

    def test_source_doc_id_nullable(self):
        u = test_case_schema.TestCaseUpdate(source_doc_id=None)
        assert u.source_doc_id is None


class TestValidateSourceDoc:
    def test_none_passes(self):
        assert validate_source_doc(MagicMock(), None, 1) is None

    def test_existing_doc_passes(self, monkeypatch):
        db = MagicMock()
        from app.services import requirement_service
        monkeypatch.setattr(requirement_service, "get_requirement", lambda *a, **k: {"id": 4})
        assert validate_source_doc(db, 4, 1) is None

    def test_missing_doc_rejected(self, monkeypatch):
        db = MagicMock()
        from app.services import requirement_service
        monkeypatch.setattr(requirement_service, "get_requirement", lambda *a, **k: None)
        msg = validate_source_doc(db, 999, 1)
        assert msg is not None
        assert "不存在" in msg
