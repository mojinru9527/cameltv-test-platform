"""证据包任务编排与导入测试。"""
from __future__ import annotations

import json


def test_job_runner_marks_job_failed_when_discovery_fails(db_session, monkeypatch):
    from app.models.lanhu_evidence import LanhuEvidenceJob
    from app.services.lanhu_evidence.job_runner import run_job_in_new_session

    job = LanhuEvidenceJob(project_id=1, source_url="bad", status="pending", storage_dir="x")
    db_session.add(job)
    db_session.commit()
    job_id = job.id

    def _boom(*args, **kwargs):
        raise ValueError("invalid url")

    monkeypatch.setattr(
        "app.services.lanhu_evidence.page_discovery.discover_pages", _boom
    )

    run_job_in_new_session(job_id, project_id=1, session_factory=lambda: db_session)

    refreshed = db_session.get(LanhuEvidenceJob, job_id)
    assert refreshed.status == "failed"
    assert "invalid url" in refreshed.error_message


def test_job_runner_marks_cancelled_when_cancel_requested(db_session, monkeypatch):
    from app.models.lanhu_evidence import LanhuEvidenceJob
    from app.services.lanhu_evidence.job_runner import run_job_in_new_session
    from app.services.lanhu_evidence.page_discovery import DiscoveredLanhuPage

    job = LanhuEvidenceJob(
        project_id=1, source_url="https://lanhuapp.com/x?docId=d",
        status="pending", storage_dir="x", cancel_requested=True,
    )
    db_session.add(job)
    db_session.commit()
    job_id = job.id

    monkeypatch.setattr(
        "app.services.lanhu_evidence.page_discovery.discover_pages",
        lambda *a, **k: [DiscoveredLanhuPage("p1", "页", "页", "", 0)],
    )

    run_job_in_new_session(job_id, project_id=1, session_factory=lambda: db_session)

    refreshed = db_session.get(LanhuEvidenceJob, job_id)
    assert refreshed.status == "cancelled"


# ── API ──

def test_create_job_returns_503_when_disabled(client, auth_headers, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.lanhu_evidence_enabled", False)
    resp = client.post(
        "/api/v1/lanhu-evidence/jobs",
        headers=auth_headers,
        json={"url": "https://lanhuapp.com/x?docId=d"},
    )
    assert resp.status_code == 503


def test_create_and_get_job_when_enabled(client, auth_headers, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.lanhu_evidence_enabled", True)
    # 阻断后台真实采集
    monkeypatch.setattr(
        "app.services.lanhu_evidence.job_runner.run_job_in_new_session",
        lambda *a, **k: None,
    )
    resp = client.post(
        "/api/v1/lanhu-evidence/jobs",
        headers=auth_headers,
        json={"url": "https://lanhuapp.com/x?docId=d"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "pending"
    assert "word_path" not in data
    assert "json_path" not in data
    job_id = data["id"]

    got = client.get(f"/api/v1/lanhu-evidence/jobs/{job_id}", headers=auth_headers)
    assert got.status_code == 200
    assert got.json()["data"]["id"] == job_id


def test_create_job_persists_every_requested_flag(client, auth_headers, db_session, monkeypatch):
    from app.models.lanhu_evidence import LanhuEvidenceJob

    monkeypatch.setattr("app.core.config.settings.lanhu_evidence_enabled", True)
    monkeypatch.setattr(
        "app.services.lanhu_evidence.job_runner.run_job_in_new_session",
        lambda *a, **k: None,
    )
    requested = {
        "url": "https://lanhuapp.com/x?docId=d",
        "capture_all_pages": False,
        "include_word": False,
        "include_json": True,
        "import_to_requirement": False,
        "import_to_knowledge": True,
        "import_to_wiki": False,
    }

    response = client.post(
        "/api/v1/lanhu-evidence/jobs", headers=auth_headers, json=requested,
    )

    assert response.status_code == 200
    job = db_session.get(LanhuEvidenceJob, response.json()["data"]["id"])
    assert json.loads(job.requested_options_json) == requested


def test_create_job_import_flags_require_import_permission(db_session, monkeypatch):
    import pytest
    from types import SimpleNamespace

    from app.api.v1.lanhu_evidence import create_job
    from app.core.deps import CurrentUser
    from app.core.exceptions import APIException
    from app.schemas.lanhu_evidence import LanhuEvidenceCreateRequest

    monkeypatch.setattr("app.core.config.settings.lanhu_evidence_enabled", True)
    current = CurrentUser(
        user=SimpleNamespace(id=99),
        permissions=["lanhu_evidence:run"],
        project_id=1,
    )

    with pytest.raises(APIException) as exc_info:
        create_job(
            LanhuEvidenceCreateRequest(
                url="https://lanhuapp.com/x?docId=d",
                import_to_wiki=True,
            ),
            current,
            db_session,
        )

    assert exc_info.value.http_status == 403


def test_legacy_requirement_lanhu_upload_cannot_bypass_evidence_gate(
    client, auth_headers,
):
    response = client.post(
        "/api/v1/requirements/upload",
        headers=auth_headers,
        data={"lanhu_url": "https://lanhuapp.com/x?docId=a&pageId=b"},
    )

    assert response.status_code == 409
    assert "证据包质量门禁" in response.json()["msg"]


def test_get_job_isolated_by_project(client, auth_headers, db_session, monkeypatch):
    from app.models.lanhu_evidence import LanhuEvidenceJob

    # 属于项目 999 的任务，当前请求头项目为 1 → 404
    other = LanhuEvidenceJob(project_id=999, source_url="x", status="success", storage_dir="x")
    db_session.add(other)
    db_session.commit()

    resp = client.get(f"/api/v1/lanhu-evidence/jobs/{other.id}", headers=auth_headers)
    assert resp.status_code == 404


def test_asset_list_uses_safe_dto_without_file_path(
    client, auth_headers, db_session, tmp_path,
):
    from app.models.lanhu_evidence import LanhuEvidenceAsset, LanhuEvidenceJob

    job = LanhuEvidenceJob(project_id=1, storage_dir=str(tmp_path))
    db_session.add(job)
    db_session.flush()
    asset = LanhuEvidenceAsset(
        job_id=job.id,
        project_id=1,
        asset_type="json",
        file_path=str(tmp_path / "lanhu.json"),
        relative_path="lanhu.json",
        mime_type="application/json",
    )
    db_session.add(asset)
    db_session.commit()

    response = client.get(
        f"/api/v1/lanhu-evidence/jobs/{job.id}/assets", headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data[0]["relative_path"] == "lanhu.json"
    assert "file_path" not in data[0]


def test_asset_download_rejects_prefix_sibling_path(
    client, auth_headers, db_session, tmp_path,
):
    from app.models.lanhu_evidence import LanhuEvidenceAsset, LanhuEvidenceJob

    base = tmp_path / "attempt-1"
    sibling = tmp_path / "attempt-1-foreign"
    sibling.mkdir()
    file_path = sibling / "foreign.json"
    file_path.write_text("{}", encoding="utf-8")
    job = LanhuEvidenceJob(project_id=1, storage_dir=str(base))
    db_session.add(job)
    db_session.flush()
    asset = LanhuEvidenceAsset(
        job_id=job.id,
        project_id=1,
        asset_type="json",
        file_path=str(file_path),
    )
    db_session.add(asset)
    db_session.commit()

    response = client.get(
        f"/api/v1/lanhu-evidence/assets/{asset.id}", headers=auth_headers,
    )

    assert response.status_code == 403


def test_asset_download_rejects_asset_with_missing_job(
    client, auth_headers, db_session, tmp_path,
):
    from app.models.lanhu_evidence import LanhuEvidenceAsset

    file_path = tmp_path / "orphan.json"
    file_path.write_text("{}", encoding="utf-8")
    asset = LanhuEvidenceAsset(
        job_id=999999,
        project_id=1,
        asset_type="json",
        file_path=str(file_path),
    )
    db_session.add(asset)
    db_session.commit()

    response = client.get(
        f"/api/v1/lanhu-evidence/assets/{asset.id}", headers=auth_headers,
    )

    assert response.status_code == 404


# ── Import to requirement / RAG / Wiki ──

def _make_job_with_pages(db_session, *, project_id=1):
    from app.models.lanhu_evidence import LanhuEvidenceJob, LanhuEvidencePage

    job = LanhuEvidenceJob(
        project_id=project_id,
        source_url="https://lanhuapp.com/x?docId=d&versionId=v",
        doc_id="d",
        version_id="v",
        document_name="CamelTv 需求",
        status="success",
        quality_json='{"import_ready": true, "complete": true}',
        word_path="storage/lanhu-evidence/1/lanhu.docx",
        json_path="storage/lanhu-evidence/1/lanhu.json",
        storage_dir="storage/lanhu-evidence/1",
    )
    db_session.add(job)
    db_session.flush()
    db_session.add(LanhuEvidencePage(
        job_id=job.id, project_id=project_id, page_id="p1",
        page_name="比赛推送", page_path="App/赛事/比赛推送", folder="App/赛事",
        order_index=0, merged_text="# 比赛推送\nmatchId 必填",
    ))
    db_session.commit()
    return job


def test_import_evidence_to_requirement_creates_doc(db_session):
    from app.services.lanhu_evidence.import_service import import_to_requirement

    job = _make_job_with_pages(db_session)
    doc = import_to_requirement(db_session, project_id=1, job_id=job.id, creator_id=1)

    assert doc["file_type"] == "docx"
    assert "蓝湖证据包" in doc["title"]


def test_import_evidence_to_knowledge_preserves_source_refs(db_session):
    from app.services.lanhu_evidence.import_service import import_to_knowledge

    job = _make_job_with_pages(db_session)
    source_id = import_to_knowledge(db_session, project_id=1, job_id=job.id)

    assert source_id is not None


def test_import_metadata_uses_asset_ids_without_physical_paths(db_session):
    from app.models.knowledge import KnowledgeSource
    from app.models.lanhu_evidence import LanhuEvidenceAsset
    from app.services.lanhu_evidence.import_service import import_to_knowledge

    job = _make_job_with_pages(db_session)
    word = LanhuEvidenceAsset(
        job_id=job.id,
        project_id=1,
        asset_type="word",
        file_path="C:/private/evidence/lanhu.docx",
    )
    exported_json = LanhuEvidenceAsset(
        job_id=job.id,
        project_id=1,
        asset_type="json",
        file_path="C:/private/evidence/lanhu.json",
    )
    db_session.add_all([word, exported_json])
    db_session.commit()

    source_id = import_to_knowledge(db_session, project_id=1, job_id=job.id)
    metadata = json.loads(db_session.get(KnowledgeSource, source_id).metadata_json)

    assert metadata["word_asset_id"] == word.id
    assert metadata["json_asset_id"] == exported_json.id
    assert "word_path" not in metadata
    assert "json_path" not in metadata
    assert "C:/private" not in json.dumps(metadata)


def test_import_evidence_to_wiki_creates_raw_source(db_session):
    from app.services.lanhu_evidence.import_service import import_to_wiki

    job = _make_job_with_pages(db_session)
    raw_id = import_to_wiki(db_session, project_id=1, job_id=job.id)

    assert raw_id is not None


# ── Task 2: 质量门禁 ──

def test_quality_is_not_import_ready_when_any_page_has_no_ocr_or_review():
    from app.services.lanhu_evidence.quality_service import evaluate_job_quality

    report = evaluate_job_quality([
        {"capture_status": "success", "segment_count": 1, "capture_truncated": False,
         "merged_text": "x" * 50, "ocr_status": "success", "review_status": "pending"},
        {"capture_status": "success", "segment_count": 1, "capture_truncated": False,
         "merged_text": "x" * 50, "ocr_status": "unavailable", "review_status": "pending"},
    ])

    assert report["complete"] is False
    assert report["import_ready"] is False
    assert report["pages_missing_ocr_review"] == [1]


def test_quality_import_ready_when_ocr_unavailable_but_page_approved():
    from app.services.lanhu_evidence.quality_service import evaluate_job_quality

    report = evaluate_job_quality([
        {"capture_status": "success", "segment_count": 1, "capture_truncated": False,
         "merged_text": "x" * 50, "ocr_status": "unavailable", "review_status": "approved"},
    ])
    assert report["import_ready"] is True


def test_import_rejects_warning_job(client, auth_headers, db_session, monkeypatch):
    from app.models.lanhu_evidence import LanhuEvidenceJob

    monkeypatch.setattr("app.core.config.settings.lanhu_evidence_enabled", True)
    job = LanhuEvidenceJob(
        project_id=1, status="success_with_warnings",
        quality_json='{"import_ready":false}', storage_dir="x",
    )
    db_session.add(job)
    db_session.commit()
    job_id = job.id
    response = client.post(
        f"/api/v1/lanhu-evidence/jobs/{job_id}/import",
        headers=auth_headers, json={"import_to_requirement": True},
    )
    assert response.status_code == 409


def test_import_rejects_warning_job_even_if_quality_json_claims_ready(
    client, auth_headers, db_session,
):
    from app.models.lanhu_evidence import LanhuEvidenceJob

    job = LanhuEvidenceJob(
        project_id=1,
        status="success_with_warnings",
        quality_json='{"import_ready": true, "complete": true}',
    )
    db_session.add(job)
    db_session.commit()

    response = client.post(
        f"/api/v1/lanhu-evidence/jobs/{job.id}/import",
        headers=auth_headers,
        json={"import_to_requirement": True},
    )

    assert response.status_code == 409


def test_service_rejects_warning_job_even_if_quality_json_claims_ready(db_session):
    import pytest

    from app.models.lanhu_evidence import LanhuEvidenceJob
    from app.services.lanhu_evidence.import_service import import_to_requirement

    job = LanhuEvidenceJob(
        project_id=1,
        status="success_with_warnings",
        quality_json='{"import_ready": true, "complete": true}',
    )
    db_session.add(job)
    db_session.commit()

    with pytest.raises(ValueError):
        import_to_requirement(db_session, project_id=1, job_id=job.id, creator_id=1)


def test_review_cannot_hide_discovered_page_missing_from_database(
    client, auth_headers, db_session,
):
    from app.models.lanhu_evidence import LanhuEvidenceJob, LanhuEvidencePage

    job = LanhuEvidenceJob(
        project_id=1,
        status="success_with_warnings",
        total_pages=2,
        quality_json='{"import_ready": false}',
    )
    db_session.add(job)
    db_session.flush()
    page = LanhuEvidencePage(
        job_id=job.id,
        project_id=1,
        page_id="persisted",
        order_index=0,
        capture_status="success",
        segment_count=1,
        merged_text="reviewable text",
        ocr_status="unavailable",
    )
    db_session.add(page)
    db_session.commit()

    response = client.post(
        f"/api/v1/lanhu-evidence/pages/{page.id}/review",
        headers=auth_headers,
        json={"approved": True, "comment": "manual OCR verification"},
    )

    assert response.status_code == 200
    db_session.expire_all()
    refreshed = db_session.get(LanhuEvidenceJob, job.id)
    quality = json.loads(refreshed.quality_json)
    assert refreshed.status == "success_with_warnings"
    assert quality["import_ready"] is False
    assert quality["pages_missing_capture"] == [1]


def test_final_review_completes_previously_requested_imports(
    client, auth_headers, db_session, monkeypatch,
):
    from app.models.lanhu_evidence import LanhuEvidenceJob, LanhuEvidencePage
    from app.services.lanhu_evidence import import_service

    job = LanhuEvidenceJob(
        project_id=1,
        creator_id=1,
        status="success_with_warnings",
        total_pages=1,
        quality_json=json.dumps({"import_ready": False}),
        requested_options_json=json.dumps({"import_to_wiki": True}),
    )
    db_session.add(job)
    db_session.flush()
    page = LanhuEvidencePage(
        job_id=job.id,
        project_id=1,
        page_id="reviewable",
        order_index=0,
        capture_status="success",
        segment_count=1,
        capture_truncated=False,
        merged_text="verified design evidence",
        ocr_status="unavailable",
        review_status="pending",
    )
    db_session.add(page)
    db_session.commit()
    calls: list[dict] = []
    monkeypatch.setattr(
        import_service,
        "execute_requested_imports",
        lambda db, **kwargs: calls.append(kwargs["options"]) or {"wiki_raw_source_id": 7},
    )

    response = client.post(
        f"/api/v1/lanhu-evidence/pages/{page.id}/review",
        headers=auth_headers,
        json={"approved": True, "comment": "verified against the source design"},
    )

    assert response.status_code == 200
    db_session.expire_all()
    refreshed = db_session.get(LanhuEvidenceJob, job.id)
    assert refreshed.status == "success"
    assert calls == [{"import_to_wiki": True}]
    assert json.loads(refreshed.import_result_json) == {"wiki_raw_source_id": 7}


def test_service_import_guard_blocks_non_import_ready(db_session):
    """非 HTTP 调用方也不能绕过质量门禁。"""
    import pytest
    from app.models.lanhu_evidence import LanhuEvidenceJob
    from app.services.lanhu_evidence.import_service import import_to_requirement

    job = LanhuEvidenceJob(
        project_id=1, status="success_with_warnings",
        quality_json='{"import_ready": false}', storage_dir="x",
    )
    db_session.add(job)
    db_session.commit()
    with pytest.raises(ValueError):
        import_to_requirement(db_session, project_id=1, job_id=job.id, creator_id=1)


# ── Task 3: 导出资产登记 + 截断标记 ──

def _run_mocked_job(db_session, monkeypatch, tmp_path, *, options: str):
    from app.models.lanhu_evidence import LanhuEvidenceJob
    from app.services.lanhu_evidence import job_runner, screenshot_service
    from app.services.lanhu_evidence.ocr_provider import MockOcrProvider
    from app.services.lanhu_evidence.page_discovery import DiscoveredLanhuPage

    job = LanhuEvidenceJob(
        project_id=1, source_url="https://lanhuapp.com/x?docId=d&versionId=v",
        status="pending", storage_dir=str(tmp_path), requested_options_json=options,
    )
    db_session.add(job)
    db_session.commit()
    job_id = job.id

    monkeypatch.setattr(
        "app.services.lanhu_evidence.page_discovery.discover_pages",
        lambda *a, **k: [DiscoveredLanhuPage("p1", "比赛推送", "App/比赛推送", "App", 0)],
    )

    async def _fake_capture(target_url, out_dir, page_key):
        out_dir.mkdir(parents=True, exist_ok=True)
        p = out_dir / f"{page_key}-segment-001.png"
        p.write_bytes(b"\x89PNG fake-bytes")
        seg = screenshot_service.CaptureSegment(
            path=p, scroll_top=0, viewport_height=1000, sha256="abc123",
        )
        return screenshot_service.CaptureResult(
            segments=[seg], scroll_height=1000, viewport_height=1000, truncated=False,
        )

    monkeypatch.setattr(screenshot_service, "capture_page_segments", _fake_capture)
    monkeypatch.setattr(
        "app.services.lanhu_evidence.ocr_provider.get_ocr_provider",
        lambda: MockOcrProvider(),
    )
    monkeypatch.setattr(
        "app.services.lanhu_evidence.job_runner.get_ocr_provider",
        lambda: MockOcrProvider(),
    )

    job_runner.run_job_in_new_session(job_id, project_id=1, session_factory=lambda: db_session)
    return job_id


def test_runner_registers_word_and_json_assets(db_session, monkeypatch, tmp_path):
    from app.models.lanhu_evidence import LanhuEvidenceAsset

    job_id = _run_mocked_job(
        db_session, monkeypatch, tmp_path,
        options='{"capture_all_pages": true, "include_word": true, "include_json": true}',
    )
    assets = db_session.query(LanhuEvidenceAsset).filter_by(job_id=job_id).all()
    types = {a.asset_type for a in assets}
    assert "screenshot" in types
    assert "word" in types
    assert "json" in types
    # 资产 relative_path 不得为绝对路径
    for a in assets:
        assert not a.relative_path.startswith("/")


def test_runner_skips_exports_when_options_disabled(db_session, monkeypatch, tmp_path):
    from app.models.lanhu_evidence import LanhuEvidenceAsset

    job_id = _run_mocked_job(
        db_session, monkeypatch, tmp_path,
        options='{"capture_all_pages": true, "include_word": false, "include_json": false}',
    )
    types = {
        a.asset_type
        for a in db_session.query(LanhuEvidenceAsset).filter_by(job_id=job_id).all()
    }
    assert "word" not in types
    assert "json" not in types


def test_runner_passes_capture_all_pages_flag_to_discovery(db_session, monkeypatch, tmp_path):
    from app.models.lanhu_evidence import LanhuEvidenceJob
    from app.services.lanhu_evidence import job_runner

    received: list[bool] = []

    def _discover(_url, *, capture_all_pages):
        received.append(capture_all_pages)
        return []

    monkeypatch.setattr(
        "app.services.lanhu_evidence.page_discovery.discover_pages", _discover,
    )
    job = LanhuEvidenceJob(
        project_id=1,
        source_url="https://lanhuapp.com/x?docId=d",
        storage_dir=str(tmp_path),
        requested_options_json='{"capture_all_pages": false}',
    )
    db_session.add(job)
    db_session.commit()
    job_id = job.id

    job_runner.run_job_in_new_session(
        job_id, project_id=1, session_factory=lambda: db_session,
    )

    assert received == [False]


def test_runner_only_executes_requested_auto_imports(db_session, monkeypatch, tmp_path):
    from app.models.lanhu_evidence import LanhuEvidenceJob
    from app.services.lanhu_evidence import import_service

    calls: list[str] = []
    monkeypatch.setattr(
        import_service,
        "import_to_requirement",
        lambda *a, **k: calls.append("requirement") or {"id": 1},
    )
    monkeypatch.setattr(
        import_service,
        "import_to_knowledge",
        lambda *a, **k: calls.append("knowledge") or 2,
    )
    monkeypatch.setattr(
        import_service,
        "import_to_wiki",
        lambda *a, **k: calls.append("wiki") or 3,
    )

    job_id = _run_mocked_job(
        db_session,
        monkeypatch,
        tmp_path,
        options=(
            '{"capture_all_pages": true, "include_word": false, "include_json": false, '
            '"import_to_requirement": false, "import_to_knowledge": true, '
            '"import_to_wiki": false}'
        ),
    )

    db_session.expire_all()
    job = db_session.get(LanhuEvidenceJob, job_id)
    assert calls == ["knowledge"]
    assert json.loads(job.import_result_json) == {"knowledge_source_id": 2}


def test_zero_capture_job_does_not_export_or_register_documents(
    db_session, monkeypatch, tmp_path,
):
    from app.models.lanhu_evidence import LanhuEvidenceAsset, LanhuEvidenceJob
    from app.services.lanhu_evidence import job_runner, screenshot_service
    from app.services.lanhu_evidence.page_discovery import DiscoveredLanhuPage

    job = LanhuEvidenceJob(
        project_id=1,
        source_url="https://lanhuapp.com/x?docId=d",
        storage_dir=str(tmp_path),
        requested_options_json='{"include_word": true, "include_json": true}',
    )
    db_session.add(job)
    db_session.commit()
    job_id = job.id
    monkeypatch.setattr(
        "app.services.lanhu_evidence.page_discovery.discover_pages",
        lambda *a, **k: [DiscoveredLanhuPage("p1", "Page", "Page", "", 0)],
    )

    async def _capture_failed(*_args, **_kwargs):
        return screenshot_service.CaptureResult(error="capture failed")

    monkeypatch.setattr(screenshot_service, "capture_page_segments", _capture_failed)

    job_runner.run_job_in_new_session(
        job_id, project_id=1, session_factory=lambda: db_session,
    )

    db_session.expire_all()
    refreshed = db_session.get(LanhuEvidenceJob, job_id)
    assert refreshed.status == "failed"
    assert refreshed.word_path == ""
    assert refreshed.json_path == ""
    assert not (tmp_path / "lanhu.docx").exists()
    assert not (tmp_path / "lanhu.json").exists()
    assert db_session.query(LanhuEvidenceAsset).filter_by(job_id=job_id).count() == 0


def test_runner_closes_every_short_session_before_capture(
    db_session, monkeypatch, tmp_path,
):
    from sqlalchemy.orm import Session, sessionmaker

    from app.models.lanhu_evidence import LanhuEvidenceJob
    from app.services.lanhu_evidence import job_runner, screenshot_service
    from app.services.lanhu_evidence.ocr_provider import MockOcrProvider
    from app.services.lanhu_evidence.page_discovery import DiscoveredLanhuPage

    job = LanhuEvidenceJob(
        project_id=1,
        source_url="https://lanhuapp.com/x?docId=d",
        storage_dir=str(tmp_path),
        requested_options_json='{"include_word": false, "include_json": false}',
    )
    db_session.add(job)
    db_session.commit()

    sessions = []

    class TrackingSession(Session):
        was_closed = False

        def close(self):
            self.was_closed = True
            super().close()

    make_session = sessionmaker(bind=db_session.get_bind(), class_=TrackingSession)

    def session_factory():
        session = make_session()
        sessions.append(session)
        return session

    monkeypatch.setattr(
        "app.services.lanhu_evidence.page_discovery.discover_pages",
        lambda *a, **k: [DiscoveredLanhuPage("p1", "Page", "Page", "", 0)],
    )

    async def _capture(*_args, **_kwargs):
        assert sessions
        assert all(session.was_closed for session in sessions)
        path = tmp_path / "p1.png"
        path.write_bytes(b"png")
        return screenshot_service.CaptureResult(
            segments=[screenshot_service.CaptureSegment(path, 0, 100, "sha")],
            scroll_height=100,
            viewport_height=100,
        )

    monkeypatch.setattr(screenshot_service, "capture_page_segments", _capture)
    monkeypatch.setattr(job_runner, "get_ocr_provider", lambda: MockOcrProvider())

    job_runner.run_job_in_new_session(
        job.id, project_id=1, session_factory=session_factory,
    )

    db_session.expire_all()
    assert db_session.get(LanhuEvidenceJob, job.id).status == "success"
    assert len(sessions) >= 3
    assert len({id(session) for session in sessions}) == len(sessions)
    assert all(session.was_closed for session in sessions)


def test_page_transaction_failure_does_not_rollback_or_stop_other_pages(
    db_session, monkeypatch, tmp_path,
):
    from sqlalchemy.orm import Session, sessionmaker

    from app.models.lanhu_evidence import LanhuEvidenceJob, LanhuEvidencePage
    from app.services.lanhu_evidence import job_runner, screenshot_service
    from app.services.lanhu_evidence.ocr_provider import MockOcrProvider
    from app.services.lanhu_evidence.page_discovery import DiscoveredLanhuPage

    job = LanhuEvidenceJob(
        project_id=1,
        source_url="https://lanhuapp.com/x?docId=d",
        storage_dir=str(tmp_path),
        requested_options_json='{"include_word": false, "include_json": false}',
    )
    db_session.add(job)
    db_session.commit()
    job_id = job.id

    failed_once = {"value": False}

    class FailMiddlePageSession(Session):
        def commit(self):
            middle_page = any(
                isinstance(value, LanhuEvidencePage) and value.order_index == 1
                for value in (*self.new, *self.identity_map.values())
            )
            if middle_page and not failed_once["value"]:
                failed_once["value"] = True
                raise RuntimeError("simulated page transaction failure")
            return super().commit()

    make_session = sessionmaker(
        bind=db_session.get_bind(), class_=FailMiddlePageSession,
    )
    monkeypatch.setattr(
        "app.services.lanhu_evidence.page_discovery.discover_pages",
        lambda *a, **k: [
            DiscoveredLanhuPage(f"p{index}", f"Page {index}", f"Page {index}", "", index)
            for index in range(3)
        ],
    )

    async def _capture(_target_url, out_dir, page_key):
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{page_key}.png"
        path.write_bytes(b"png")
        return screenshot_service.CaptureResult(
            segments=[screenshot_service.CaptureSegment(path, 0, 100, page_key)],
            scroll_height=100,
            viewport_height=100,
        )

    monkeypatch.setattr(screenshot_service, "capture_page_segments", _capture)
    monkeypatch.setattr(job_runner, "get_ocr_provider", lambda: MockOcrProvider())

    job_runner.run_job_in_new_session(
        job_id, project_id=1, session_factory=make_session,
    )

    db_session.expire_all()
    persisted_orders = [
        page.order_index
        for page in db_session.query(LanhuEvidencePage)
        .filter_by(job_id=job_id)
        .order_by(LanhuEvidencePage.order_index)
    ]
    refreshed = db_session.get(LanhuEvidenceJob, job_id)
    assert failed_once["value"] is True
    assert persisted_orders == [0, 2]
    assert refreshed.status == "success_with_warnings"
    assert refreshed.failed_pages == 1
