"""Lanhu evidence orchestration with page-scoped short transactions.

No database session is held while page discovery, screenshot capture, OCR, or
document export performs external I/O. Discovery, every page, every exported
asset, and final state each use their own short-lived session and commit. A
failed page transaction therefore cannot roll back evidence already committed
for another page.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterator

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.core.config import settings
from app.models.lanhu_evidence import (
    LanhuEvidenceAsset,
    LanhuEvidenceJob,
    LanhuEvidencePage,
    LanhuOcrBlock,
)
from app.services.lanhu_evidence import page_discovery, screenshot_service
from app.services.lanhu_evidence.json_export_service import export_json
from app.services.lanhu_evidence.merge_service import merge_page_text
from app.services.lanhu_evidence.ocr_provider import get_ocr_provider
from app.services.lanhu_evidence.quality_service import evaluate_job_quality
from app.services.lanhu_evidence.word_export_service import WordPage, export_word


SessionFactory = Callable[[], Session]


class JobCancelled(Exception):
    """Cooperative cancellation signal."""


class JobStopped(Exception):
    """The job was already moved to another terminal state."""


@contextmanager
def _short_session(factory: SessionFactory) -> Iterator[Session]:
    """Open one transaction owner and always rollback/close at the boundary."""
    db = factory()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _scoped_job(db: Session, job_id: int, project_id: int) -> LanhuEvidenceJob | None:
    return db.scalar(select(LanhuEvidenceJob).where(
        LanhuEvidenceJob.id == job_id,
        LanhuEvidenceJob.project_id == project_id,
    ))


def _require_active_job(db: Session, job_id: int, project_id: int) -> LanhuEvidenceJob:
    job = _scoped_job(db, job_id, project_id)
    if job is None:
        raise JobStopped()
    if job.status == "cancelled" or job.cancel_requested:
        raise JobCancelled()
    if job.status not in ("pending", "running"):
        raise JobStopped()
    return job


def _dom_text_for(local_url: str) -> str:
    """Best-effort extraction from a local Axure document."""
    if not local_url:
        return ""
    try:
        from urllib.parse import unquote, urlparse

        from app.services.external.lanhu_provider import _extract_page_text

        parsed = urlparse(local_url)
        path = Path(unquote(parsed.path.lstrip("/"))) if parsed.scheme == "file" else Path(local_url)
        if path.exists():
            return _extract_page_text(path) or ""
    except Exception:  # noqa: BLE001
        return ""
    return ""


def run_job_in_new_session(
    job_id: int,
    project_id: int,
    session_factory: SessionFactory | None = None,
) -> None:
    """Run a job using a fresh, closed session for every persistence boundary."""
    factory = session_factory or SessionLocal
    heartbeat_stop = threading.Event()
    heartbeat_thread: threading.Thread | None = None
    if session_factory is None:
        heartbeat_thread = threading.Thread(
            target=_heartbeat_loop,
            args=(factory, job_id, project_id, heartbeat_stop),
            daemon=True,
            name=f"lanhu-evidence-heartbeat-{job_id}",
        )
        heartbeat_thread.start()
    try:
        _run_job(factory, job_id, project_id)
    except JobCancelled:
        _mark_cancelled(factory, job_id, project_id)
    except JobStopped:
        # A cancellation or stale-worker recovery may win while external I/O is
        # in flight. Never overwrite that terminal state on return.
        return
    except Exception as exc:  # noqa: BLE001
        _mark_failed(factory, job_id, project_id, str(exc)[:1000])
    finally:
        heartbeat_stop.set()
        if heartbeat_thread is not None:
            heartbeat_thread.join(timeout=1.0)


def _heartbeat_loop(
    factory: SessionFactory,
    job_id: int,
    project_id: int,
    stop: threading.Event,
) -> None:
    """Refresh liveness with independent short transactions during slow I/O."""
    interval = heartbeat_interval(settings.lanhu_evidence_stale_after_seconds)
    while not stop.wait(interval):
        try:
            with _short_session(factory) as db:
                job = _scoped_job(db, job_id, project_id)
                if job is None or job.status != "running":
                    return
                job.heartbeat_at = datetime.now()
                db.commit()
        except Exception:  # noqa: BLE001
            # Page commits remain authoritative; a transient heartbeat writer
            # collision must not terminate evidence collection.
            continue


def heartbeat_interval(stale_after_seconds: int) -> float:
    """Keep at least two durable liveness opportunities inside a stale window."""
    return max(1.0, min(30.0, float(stale_after_seconds) / 3.0))


def _run_job(factory: SessionFactory, job_id: int, project_id: int) -> None:
    with _short_session(factory) as db:
        job = _scoped_job(db, job_id, project_id)
        if job is None or job.status == "cancelled":
            return
        if job.cancel_requested:
            job.status = "cancelled"
            job.stage = "done"
            job.finished_at = datetime.now()
            db.commit()
            return
        if job.status not in ("pending", "running"):
            return
        try:
            options = json.loads(job.requested_options_json or "{}")
        except (json.JSONDecodeError, TypeError):
            options = {}
        options = options if isinstance(options, dict) else {}
        source_url = job.source_url
        storage_dir = Path(job.storage_dir)
        creator_id = job.creator_id
        job.status = "running"
        job.stage = "discovering"
        job.started_at = job.started_at or datetime.now()
        job.heartbeat_at = datetime.now()
        job.error_message = ""
        db.commit()

    # Request flags are the effective job contract; defaults preserve legacy
    # jobs created before requested_options_json existed.
    capture_all_pages = bool(options.get("capture_all_pages", True))
    include_word = bool(options.get("include_word", True))
    include_json = bool(options.get("include_json", True))

    pages = page_discovery.discover_pages(
        source_url, capture_all_pages=capture_all_pages,
    )
    base = page_discovery.parse_lanhu_url(source_url)

    with _short_session(factory) as db:
        job = _require_active_job(db, job_id, project_id)
        job.doc_id = base.doc_id
        job.version_id = base.version_id
        job.root_page_id = base.page_id
        job.total_pages = len(pages)
        job.stage = "capturing"
        job.heartbeat_at = datetime.now()
        db.commit()

    pages_dir = storage_dir / "pages"
    ocr = get_ocr_provider()
    word_pages: list[WordPage] = []
    json_pages: list[dict] = []
    page_dicts: list[dict] = []
    captured = 0
    ocr_done = 0
    failed = 0

    for order, discovered in enumerate(pages):
        # Check the persisted request signal without carrying a session into I/O.
        with _short_session(factory) as db:
            _require_active_job(db, job_id, project_id)

        page_key = (discovered.page_id or f"page-{order:03d}").replace("/", "_")
        output_dir = pages_dir / page_key
        target_url = discovered.local_url or discovered.page_url
        try:
            capture = asyncio.run(
                screenshot_service.capture_page_segments(target_url, output_dir, page_key)
            )
        except Exception as exc:  # noqa: BLE001
            capture = screenshot_service.CaptureResult(error=str(exc)[:300])

        if capture.segments:
            capture_status = "success"
            capture_error = capture.error or ""
        elif capture.error:
            capture_status = "failed"
            capture_error = capture.error
        else:
            capture_status = "skipped"
            capture_error = ""

        segment_blocks: list[tuple[screenshot_service.CaptureSegment, list]] = []
        ocr_lines: list[str] = []
        for segment in capture.segments:
            try:
                ocr_result = ocr.recognize(segment.path)
                blocks = list(ocr_result.blocks) if ocr_result.status == "success" else []
            except Exception:  # noqa: BLE001
                blocks = []
            segment_blocks.append((segment, blocks))
            ocr_lines.extend(
                block.text for block in sorted(blocks, key=lambda block: block.order_index)
                if block.text
            )

        ocr_text = "\n".join(ocr_lines)
        dom_text = _dom_text_for(discovered.local_url)
        merged = merge_page_text(discovered.page_name, dom_text, ocr_text)
        ocr_status = "success" if ocr_text else "unavailable"
        page_fact = {
            "capture_status": capture_status,
            "segment_count": len(capture.segments),
            "capture_truncated": bool(capture.truncated),
            "merged_text": merged.merged_text,
            "ocr_status": ocr_status,
            "review_status": "pending",
        }

        next_captured = captured + int(capture_status == "success")
        next_ocr_done = ocr_done + int(bool(ocr_text))
        next_failed = failed + int(capture_status != "success")
        try:
            with _short_session(factory) as db:
                job = _require_active_job(db, job_id, project_id)
                row = LanhuEvidencePage(
                    job_id=job_id,
                    project_id=project_id,
                    page_id=discovered.page_id,
                    page_name=discovered.page_name,
                    page_path=discovered.page_path,
                    folder=discovered.folder,
                    order_index=order,
                    page_url=discovered.page_url,
                    local_url=discovered.local_url,
                    capture_status=capture_status,
                    ocr_status=ocr_status,
                    dom_text=dom_text,
                    ocr_text=ocr_text,
                    merged_text=merged.merged_text,
                    segment_count=len(capture.segments),
                    capture_truncated=bool(capture.truncated),
                    quality_json=json.dumps(merged.quality, ensure_ascii=False),
                    error_message=capture_error,
                )
                db.add(row)
                db.flush()
                for segment, blocks in segment_blocks:
                    asset = LanhuEvidenceAsset(
                        job_id=job_id,
                        page_id=row.id,
                        project_id=project_id,
                        asset_type="screenshot",
                        file_path=str(segment.path),
                        relative_path=_relative_asset_path(segment.path, storage_dir),
                        mime_type="image/png",
                        scroll_top=segment.scroll_top,
                        viewport_height=segment.viewport_height,
                        sha256=segment.sha256,
                    )
                    db.add(asset)
                    db.flush()
                    for block_order, block in enumerate(blocks):
                        db.add(LanhuOcrBlock(
                            job_id=job_id,
                            page_id=row.id,
                            asset_id=asset.id,
                            project_id=project_id,
                            text=block.text,
                            confidence=block.confidence,
                            bbox_json=json.dumps(block.bbox),
                            order_index=block_order,
                        ))
                job.captured_pages = next_captured
                job.ocr_pages = next_ocr_done
                job.failed_pages = next_failed
                job.heartbeat_at = datetime.now()
                db.commit()
        except (JobCancelled, JobStopped):
            raise
        except Exception:  # noqa: BLE001
            # Only this page transaction is rolled back. Keep processing later
            # pages so a single persistence failure cannot erase prior evidence.
            failed += 1
            page_dicts.append({
                "capture_status": "failed",
                "segment_count": 0,
                "capture_truncated": True,
                "merged_text": "",
                "ocr_status": "unavailable",
                "review_status": "pending",
            })
            _update_progress(factory, job_id, project_id, captured, ocr_done, failed)
            continue

        captured = next_captured
        ocr_done = next_ocr_done
        failed = next_failed
        page_dicts.append(page_fact)
        screenshot_paths = [segment.path for segment in capture.segments]
        word_pages.append(WordPage(
            page_name=discovered.page_name,
            page_path=discovered.page_path,
            merged_text=merged.merged_text,
            quality=merged.quality,
            screenshots=screenshot_paths,
        ))
        json_pages.append({
            "page_id": discovered.page_id,
            "page_name": discovered.page_name,
            "page_path": discovered.page_path,
            "merged_text": merged.merged_text,
            "screenshots": [
                _relative_asset_path(path, storage_dir) for path in screenshot_paths
            ],
            "quality": merged.quality,
        })

    quality = evaluate_job_quality(page_dicts)

    # Zero captured pages are a hard failure and produce no formal documents.
    if captured > 0 and (include_word or include_json):
        with _short_session(factory) as db:
            job = _require_active_job(db, job_id, project_id)
            job.stage = "exporting"
            job.heartbeat_at = datetime.now()
            title = f"蓝湖证据包 {job.document_name or job.doc_id or ''}".strip()
            db.commit()

        if include_word:
            word_path = storage_dir / "lanhu.docx"
            export_word(word_path, title, source_url, word_pages)
            _persist_export_asset(
                factory,
                job_id,
                project_id,
                word_path,
                "word",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        if include_json:
            with _short_session(factory) as db:
                job = _require_active_job(db, job_id, project_id)
                job_meta = {
                    "job_id": job.id,
                    "source_url": job.source_url,
                    "doc_id": job.doc_id,
                    "version_id": job.version_id,
                }
            json_path = storage_dir / "lanhu.json"
            export_json(json_path, job_meta, json_pages)
            _persist_export_asset(
                factory, job_id, project_id, json_path, "json", "application/json",
            )

    with _short_session(factory) as db:
        job = _require_active_job(db, job_id, project_id)
        job.captured_pages = captured
        job.ocr_pages = ocr_done
        job.failed_pages = failed
        job.quality_json = json.dumps(quality, ensure_ascii=False)
        if quality["complete"]:
            job.status = "success"
        elif captured == 0:
            job.status = "failed"
            job.error_message = "No Lanhu page screenshot was captured"
        else:
            job.status = "success_with_warnings"
        job.stage = "done"
        job.finished_at = datetime.now()
        job.heartbeat_at = datetime.now()
        db.commit()

    # ── Version diff (batch-26): compare against previous version after job completion ──
    try:
        from app.services.lanhu_evidence.diff_service import run_diff_after_job_completion
        run_diff_after_job_completion(
            job_id=job_id,
            project_id=project_id,
            source_url=job_meta.get("source_url", ""),
            doc_id=job_meta.get("doc_id", ""),
        )
    except Exception:
        logger.exception("Version diff after job #%s failed (non-fatal)", job_id)

    if quality["import_ready"]:
        _run_auto_import(factory, job_id, project_id, creator_id, options)


def _update_progress(
    factory: SessionFactory,
    job_id: int,
    project_id: int,
    captured: int,
    ocr_done: int,
    failed: int,
) -> None:
    with _short_session(factory) as db:
        job = _require_active_job(db, job_id, project_id)
        job.captured_pages = captured
        job.ocr_pages = ocr_done
        job.failed_pages = failed
        job.heartbeat_at = datetime.now()
        db.commit()


def _persist_export_asset(
    factory: SessionFactory,
    job_id: int,
    project_id: int,
    path: Path,
    asset_type: str,
    mime_type: str,
) -> None:
    with _short_session(factory) as db:
        job = _require_active_job(db, job_id, project_id)
        register_job_asset(db, job, path, asset_type, mime_type)
        if asset_type == "word":
            job.word_path = str(path)
        elif asset_type == "json":
            job.json_path = str(path)
        job.heartbeat_at = datetime.now()
        db.commit()


def register_job_asset(
    db: Session,
    job: LanhuEvidenceJob,
    path: Path,
    asset_type: str,
    mime_type: str,
) -> LanhuEvidenceAsset:
    """Register an exported file without exposing its physical path in DTOs."""
    path = Path(path)
    asset = LanhuEvidenceAsset(
        job_id=job.id,
        page_id=None,
        project_id=job.project_id,
        asset_type=asset_type,
        file_path=str(path),
        relative_path=_relative_asset_path(path, Path(job.storage_dir)),
        mime_type=mime_type,
        sha256=_sha256_file(path),
    )
    db.add(asset)
    return asset


def _run_auto_import(
    factory: SessionFactory,
    job_id: int,
    project_id: int,
    creator_id: int,
    options: dict,
) -> None:
    """Execute exactly the requested downstream imports after the quality gate."""
    from app.services.lanhu_evidence import import_service

    result: dict = {}
    try:
        with _short_session(factory) as db:
            job = _scoped_job(db, job_id, project_id)
            if job is None or job.status != "success":
                return
            result = import_service.execute_requested_imports(
                db,
                job=job,
                options=options,
                creator_id=creator_id,
            )
            job = _scoped_job(db, job_id, project_id)
            if job is not None:
                job.import_result_json = json.dumps(result, ensure_ascii=False, default=str)
                db.commit()
    except Exception as exc:  # noqa: BLE001
        with _short_session(factory) as db:
            job = _scoped_job(db, job_id, project_id)
            if job is not None:
                job.import_result_json = json.dumps(
                    {"error": str(exc)[:500]}, ensure_ascii=False,
                )
                db.commit()


def _mark_cancelled(factory: SessionFactory, job_id: int, project_id: int) -> None:
    with _short_session(factory) as db:
        job = _scoped_job(db, job_id, project_id)
        if job is None or job.status not in ("pending", "running", "cancelled"):
            return
        job.status = "cancelled"
        job.stage = "done"
        job.finished_at = datetime.now()
        job.heartbeat_at = datetime.now()
        db.commit()


def _mark_failed(
    factory: SessionFactory,
    job_id: int,
    project_id: int,
    error_message: str,
) -> None:
    with _short_session(factory) as db:
        job = _scoped_job(db, job_id, project_id)
        if job is None or job.status not in ("pending", "running"):
            return
        job.status = "failed"
        job.stage = "done"
        job.error_message = error_message
        job.finished_at = datetime.now()
        job.heartbeat_at = datetime.now()
        db.commit()


def _relative_asset_path(path: Path, base: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(Path(base).resolve()))
    except ValueError:
        return Path(path).name


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
