"""Batch 48 Lanhu attachment fallback contract (no network access)."""
from __future__ import annotations

import asyncio

from sqlalchemy import func, select

from app.models.knowledge import KnowledgeEntity
from app.models.lanhu_evidence import LanhuEvidencePage
from app.models.release_bundle import ReleaseBundle
from app.models.requirement_module import RequirementModule
from app.services.knowledge import attachment_extractor


def test_mixed_attachment_result_keeps_success_and_flags_missing_text_for_manual_handling(
    db_session, monkeypatch,
):
    bundle = ReleaseBundle(
        project_id=1,
        name="Batch48 Lanhu",
        client_version="14.1.0",
    )
    db_session.add(bundle)
    db_session.flush()
    valid = RequirementModule(
        project_id=1,
        release_bundle_id=bundle.id,
        name="有效附件",
        node_type="attachment",
        platform="APP",
        lanhu_page_id="page-valid",
        description="",
    )
    damaged = RequirementModule(
        project_id=1,
        release_bundle_id=bundle.id,
        name="待人工附件",
        node_type="attachment",
        platform="APP",
        lanhu_page_id="page-damaged",
        description="原始说明",
    )
    db_session.add_all([valid, damaged])
    db_session.flush()
    db_session.add(
        LanhuEvidencePage(
            job_id=1,
            project_id=1,
            page_id="page-valid",
            page_name="有效附件",
            merged_text="清晰可用的附件正文",
        )
    )
    db_session.flush()

    async def fake_analyze(raw_text: str, attachment_name: str):
        return attachment_extractor.AttachmentContent(
            summary=f"{attachment_name} 已提取",
            raw_text=raw_text,
            business_rules=[
                attachment_extractor.BusinessRule(
                    rule="仅认证用户可查看",
                    condition="authenticated",
                    action="show",
                    confidence=0.9,
                )
            ],
            extraction_confidence=0.9,
        )

    monkeypatch.setattr(
        attachment_extractor,
        "_ai_analyze_attachment",
        fake_analyze,
    )

    first = asyncio.run(
        attachment_extractor.extract_all_attachments(
            db_session,
            release_bundle_id=bundle.id,
            project_id=1,
            version="14.1.0",
        )
    )
    second = asyncio.run(
        attachment_extractor.extract_all_attachments(
            db_session,
            release_bundle_id=bundle.id,
            project_id=1,
            version="14.1.0",
        )
    )

    assert first.total_attachments == 2
    assert first.processed == 1
    assert first.failed == 1
    assert any("待人工附件" in error and "请人工处理" in error for error in first.errors)
    assert second.processed == 1
    assert second.failed == 1
    assert valid.description == "有效附件 已提取"
    assert damaged.description == "原始说明"
    assert db_session.scalar(
        select(func.count(KnowledgeEntity.id)).where(
            KnowledgeEntity.project_id == 1,
            KnowledgeEntity.entity_type == "business_rule",
        )
    ) == 1
