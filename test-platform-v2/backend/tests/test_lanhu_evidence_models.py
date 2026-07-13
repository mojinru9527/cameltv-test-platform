"""蓝湖证据包模型测试 —— 表结构 round-trip 与关系字段。

使用仓库既有的 db_session fixture（内存 SQLite，每测试函数独立）。
"""
from __future__ import annotations


def test_evidence_job_model_roundtrip(db_session):
    from app.models.lanhu_evidence import LanhuEvidenceJob

    job = LanhuEvidenceJob(
        project_id=1,
        source_url="https://lanhuapp.com/web/#/item/project/product?docId=d&versionId=v&pageId=p",
        doc_id="d",
        version_id="v",
        root_page_id="p",
        status="pending",
        storage_dir="storage/lanhu-evidence/1",
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    assert job.id > 0
    assert job.project_id == 1
    assert job.status == "pending"
    assert job.stage == "queued"
    assert job.created_at is not None


def test_page_asset_and_ocr_block_relationship_fields(db_session):
    from app.models.lanhu_evidence import (
        LanhuEvidenceAsset,
        LanhuEvidencePage,
        LanhuOcrBlock,
    )

    page = LanhuEvidencePage(
        job_id=1,
        project_id=1,
        page_id="p1",
        page_name="比赛推送",
        page_path="赛事/App/比赛推送",
        capture_status="success",
    )
    db_session.add(page)
    db_session.flush()
    asset = LanhuEvidenceAsset(
        job_id=1,
        page_id=page.id,
        project_id=1,
        asset_type="screenshot",
        file_path="storage/lanhu-evidence/1/pages/p1/segment-001.png",
        sha256="abc",
    )
    db_session.add(asset)
    db_session.flush()
    block = LanhuOcrBlock(
        job_id=1,
        page_id=page.id,
        asset_id=asset.id,
        project_id=1,
        text="matchId 必填",
        confidence=0.96,
        bbox_json="[0,0,100,20]",
    )
    db_session.add(block)
    db_session.commit()
    assert block.asset_id == asset.id
    assert block.page_id == page.id
    assert asset.asset_type == "screenshot"
