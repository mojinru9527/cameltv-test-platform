"""Batch 153 需求覆盖率口径 + AI 产物置信度回归。"""
from __future__ import annotations

import pytest

from app.models.requirement import RequirementDocument
from app.models.wiki import WikiDiffItem
from app.services.knowledge.artifact_confidence import (
    artifact_confidence_from_output,
    severity_confidence,
)
from app.services.wiki.compare_service import create_artifact_from_item


def _create_doc(db_session, title="B153TMP-需求", status="imported") -> RequirementDocument:
    doc = RequirementDocument(
        project_id=1, title=title, status=status, imported_count=0,
    )
    db_session.add(doc)
    db_session.flush()
    return doc


def _create_case(db_session, doc_id, title="B153TMP-用例"):
    """经 service 层创建（与 AI 生成路径一致：写入 source_doc_id）。"""
    from app.services.test_case_service import create_case

    create_case(db_session, {
        "project_id": 1,
        "title": title,
        "case_type": "manual",
        "source_doc_id": doc_id,
    }, commit=False)
    db_session.commit()


class TestRequirementCoverageCaliber:
    """C126-2：覆盖率以 source_doc_id 实际关联为锚（不依赖 imported_count）。"""

    def test_project_coverage_counts_docs_with_actual_cases(self, db_session, client, auth_headers):
        doc = _create_doc(db_session)
        _create_case(db_session, doc.id)

        trace = client.get("/api/v1/trace/coverage", headers=auth_headers).json()["data"]
        assert trace["requirement_count"] == 1
        assert trace["requirements_with_cases"] == 1
        assert trace["requirement_coverage_rate"] == 100.0

    def test_project_coverage_excludes_docs_without_cases(self, db_session, client, auth_headers):
        _create_doc(db_session, title="B153TMP-已覆盖")
        _create_doc(db_session, title="B153TMP-未覆盖")
        _create_case(db_session, 1)  # doc id 1

        trace = client.get("/api/v1/trace/coverage", headers=auth_headers).json()["data"]
        assert trace["requirement_count"] == 2
        assert trace["requirements_with_cases"] == 1
        assert trace["requirement_coverage_rate"] == 50.0

    def test_ai_generated_cases_without_imported_count_still_covered(self, db_session, client, auth_headers):
        """AI 生成路径只写 source_doc_id、不更新 imported_count —— 覆盖率不应为 0。"""
        doc = _create_doc(db_session, status="generated")  # imported_count=0
        _create_case(db_session, doc.id, title="B153TMP-AI用例")

        trace = client.get("/api/v1/trace/coverage", headers=auth_headers).json()["data"]
        assert trace["requirements_with_cases"] >= 1
        assert trace["requirement_coverage_rate"] > 0


class TestArtifactConfidence:
    """C126-3：AI 产物置信度计算。"""

    def test_severity_confidence_mapping(self):
        assert severity_confidence("P0") == 0.9
        assert severity_confidence("P1") == 0.85
        assert severity_confidence("P2") == 0.75
        assert severity_confidence("P3") == 0.65
        assert severity_confidence(None) == 0.75
        assert severity_confidence("unknown") == 0.75

    def test_confidence_from_explicit_output(self):
        assert artifact_confidence_from_output({"confidence": 0.42}) == 0.42
        assert artifact_confidence_from_output({"confidence": 1.5}) == 1.0
        assert artifact_confidence_from_output({"confidence": -1}) == 0.0

    def test_confidence_from_review_items_mean(self):
        output = {
            "review_items": [
                {"title": "a", "confidence": 0.4},
                {"title": "b", "confidence": 0.8},
                {"title": "c"},  # 无 confidence 不计入
            ],
        }
        assert artifact_confidence_from_output(output) == pytest.approx(0.6)

    def test_confidence_fallback(self):
        assert artifact_confidence_from_output({}) == 0.6
        assert artifact_confidence_from_output(None, fallback=0.5) == 0.5

    def test_diff_item_artifact_uses_severity_confidence(self, db_session):
        item = WikiDiffItem(
            task_id=1, project_id=1, dimension="接口", diff_type="conflict",
            severity="P0", title="B153TMP-差异项",
        )
        db_session.add(item)
        db_session.flush()

        art = create_artifact_from_item(db_session, 1, item)
        assert art.confidence == 0.9
        assert item.resolved_artifact_id == art.id
        assert art.review_status == "pending"
