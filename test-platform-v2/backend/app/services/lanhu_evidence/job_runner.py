"""证据包任务编排 —— 发现→截图→OCR→合并→导出→(导入)→完整性校验。

状态机：pending → running(discovering/capturing/ocr/merging/exporting/importing)
        → success / success_with_warnings / failed / cancelled

设计要点：
  - session 可注入（session_factory）以便单测；生产默认用 app.core.db.SessionLocal。
  - discover_pages 以模块属性方式调用，便于 monkeypatch。
  - 任一页面缺截图或缺合并文本 → complete=false，整体降级为 success_with_warnings。
  - 支持协作式取消：逐页检查 job.cancel_requested。
  - 截图/OCR 失败以页面级 error 记录，不中断整份任务（除非发现阶段即失败）。
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path

from app.core.config import settings
from app.core.db import SessionLocal
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


class JobCancelled(Exception):
    """协作式取消信号。"""


def _dom_text_for(local_url: str) -> str:
    """尽力从本地 Axure html 提取纯文本（DOM/MCP 辅助）。失败返回空串。"""
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


def _check_cancelled(db, job: LanhuEvidenceJob) -> None:
    db.refresh(job)
    if job.cancel_requested:
        raise JobCancelled()


def run_job_in_new_session(job_id: int, project_id: int, session_factory=None) -> None:
    """入口：创建（或注入）会话并运行任务，异常统一落库为 failed/cancelled。

    注入 session_factory（单测）时视为调用方持有会话，运行结束不关闭。
    """
    owns_session = session_factory is None
    factory = session_factory or SessionLocal
    db = factory()
    try:
        _run_job(db, job_id, project_id)
    finally:
        if owns_session:
            try:
                db.close()
            except Exception:  # noqa: BLE001
                pass


def _run_job(db, job_id: int, project_id: int) -> None:
    job = db.get(LanhuEvidenceJob, job_id)
    if job is None:
        return
    # 尊重创建时序列化的请求选项（capture_all_pages / include_word / include_json / import_to_*）
    try:
        options = json.loads(job.requested_options_json or "{}")
    except (json.JSONDecodeError, TypeError):
        options = {}
    capture_all_pages = bool(options.get("capture_all_pages", True))
    include_word = bool(options.get("include_word", True))
    include_json = bool(options.get("include_json", True))

    job.status = "running"
    job.stage = "discovering"
    job.started_at = datetime.now()
    job.heartbeat_at = datetime.now()
    job.error_message = ""
    db.commit()

    try:
        pages = page_discovery.discover_pages(job.source_url, capture_all_pages=capture_all_pages)
        base = page_discovery.parse_lanhu_url(job.source_url)
        job.doc_id = base.doc_id
        job.version_id = base.version_id
        job.root_page_id = base.page_id
        job.total_pages = len(pages)
        job.heartbeat_at = datetime.now()
        db.commit()

        storage_dir = Path(job.storage_dir)
        pages_dir = storage_dir / "pages"
        ocr = get_ocr_provider()

        page_rows: list[LanhuEvidencePage] = []
        word_pages: list[WordPage] = []
        json_pages: list[dict] = []
        page_dicts: list[dict] = []
        captured = 0
        ocr_done = 0
        failed = 0

        job.stage = "capturing"
        db.commit()

        for order, dp in enumerate(pages):
            _check_cancelled(db, job)
            page_key = (dp.page_id or f"page-{order:03d}").replace("/", "_")
            out_dir = pages_dir / page_key

            row = LanhuEvidencePage(
                job_id=job.id,
                project_id=project_id,
                page_id=dp.page_id,
                page_name=dp.page_name,
                page_path=dp.page_path,
                folder=dp.folder,
                order_index=order,
                page_url=dp.page_url,
                local_url=dp.local_url,
            )
            db.add(row)
            db.flush()

            # ── 截图 ──
            target_url = dp.local_url or dp.page_url
            shot_paths: list[Path] = []
            try:
                cap = asyncio.run(
                    screenshot_service.capture_page_segments(target_url, out_dir, page_key)
                )
            except Exception as e:  # noqa: BLE001
                cap = screenshot_service.CaptureResult(error=str(e)[:300])

            if cap.error and not cap.segments:
                row.capture_status = "failed"
                row.error_message = cap.error
                failed += 1
            else:
                row.capture_status = "success" if cap.segments else "skipped"
                if cap.segments:
                    captured += 1
                for seg in cap.segments:
                    shot_paths.append(seg.path)
                    asset = LanhuEvidenceAsset(
                        job_id=job.id,
                        page_id=row.id,
                        project_id=project_id,
                        asset_type="screenshot",
                        file_path=str(seg.path),
                        relative_path=str(seg.path.relative_to(storage_dir)) if _is_rel(seg.path, storage_dir) else seg.path.name,
                        mime_type="image/png",
                        scroll_top=seg.scroll_top,
                        viewport_height=seg.viewport_height,
                        sha256=seg.sha256,
                    )
                    db.add(asset)
                    db.flush()
                    # ── OCR ──
                    ocr_res = ocr.recognize(seg.path)
                    if ocr_res.status == "success":
                        for oi, blk in enumerate(ocr_res.blocks):
                            db.add(LanhuOcrBlock(
                                job_id=job.id,
                                page_id=row.id,
                                asset_id=asset.id,
                                project_id=project_id,
                                text=blk.text,
                                confidence=blk.confidence,
                                bbox_json=json.dumps(blk.bbox),
                                order_index=oi,
                            ))
            row.segment_count = len(shot_paths)
            row.capture_truncated = bool(getattr(cap, "truncated", False))

            # ── OCR 文本聚合 + DOM 文本 + 合并 ──
            ocr_text = _collect_ocr_text(db, row.id)
            dom_text = _dom_text_for(dp.local_url)
            merged = merge_page_text(dp.page_name, dom_text, ocr_text)
            row.ocr_text = ocr_text
            row.dom_text = dom_text
            row.merged_text = merged.merged_text
            row.quality_json = json.dumps(merged.quality, ensure_ascii=False)
            row.ocr_status = "success" if ocr_text else "unavailable"
            if ocr_text:
                ocr_done += 1

            page_rows.append(row)
            word_pages.append(WordPage(
                page_name=dp.page_name,
                page_path=dp.page_path,
                merged_text=merged.merged_text,
                quality=merged.quality,
                screenshots=shot_paths,
            ))
            json_pages.append({
                "page_id": dp.page_id,
                "page_name": dp.page_name,
                "page_path": dp.page_path,
                "merged_text": merged.merged_text,
                "screenshots": [
                    str(sp.relative_to(storage_dir)) if _is_rel(sp, storage_dir) else sp.name
                    for sp in shot_paths
                ],
                "quality": merged.quality,
            })
            page_dicts.append({
                "capture_status": row.capture_status,
                "segment_count": row.segment_count,
                "capture_truncated": row.capture_truncated,
                "merged_text": row.merged_text,
                "ocr_status": row.ocr_status,
                "review_status": row.review_status,
            })

            # 逐页短事务提交：缩短写锁持有时长（避免长事务饿死 login 等写者），并刷新心跳
            job.captured_pages = captured
            job.ocr_pages = ocr_done
            job.failed_pages = failed
            job.heartbeat_at = datetime.now()
            db.commit()

        job.captured_pages = captured
        job.ocr_pages = ocr_done
        job.failed_pages = failed
        db.commit()

        # ── 导出 Word / JSON（尊重请求选项） ──
        job.stage = "exporting"
        db.commit()
        title = f"蓝湖证据包 {job.document_name or job.doc_id or ''}".strip()
        if include_word:
            word_path = storage_dir / "lanhu.docx"
            export_word(word_path, title, job.source_url, word_pages)
            job.word_path = str(word_path)
        if include_json:
            json_path = storage_dir / "lanhu.json"
            export_json(json_path, {
                "job_id": job.id,
                "source_url": job.source_url,
                "doc_id": job.doc_id,
                "version_id": job.version_id,
            }, json_pages)
            job.json_path = str(json_path)

        # ── 质量门禁：严格判定 complete / import_ready ──
        quality = evaluate_job_quality(page_dicts)
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

        # ── 仅在质量达标后执行请求的自动导入 ──
        if quality["import_ready"] and job.status == "success":
            _run_auto_import(db, job, project_id, options)

    except JobCancelled:
        db.rollback()
        job = db.get(LanhuEvidenceJob, job_id)
        if job:
            job.status = "cancelled"
            job.stage = "done"
            job.finished_at = datetime.now()
            db.commit()
    except Exception as e:  # noqa: BLE001
        db.rollback()
        job = db.get(LanhuEvidenceJob, job_id)
        if job:
            job.status = "failed"
            job.stage = "done"
            job.error_message = str(e)[:1000]
            job.finished_at = datetime.now()
            db.commit()


def _run_auto_import(db, job: LanhuEvidenceJob, project_id: int, options: dict) -> None:
    """质量达标后执行请求中开启的自动导入；结果记入 import_result_json，异常不致任务失败。"""
    from app.services.lanhu_evidence import import_service

    result: dict = {}
    try:
        if options.get("import_to_requirement"):
            result["requirement"] = import_service.import_to_requirement(
                db, project_id=project_id, job_id=job.id, creator_id=job.creator_id,
            )
        if options.get("import_to_knowledge"):
            result["knowledge_source_id"] = import_service.import_to_knowledge(
                db, project_id=project_id, job_id=job.id,
            )
        if options.get("import_to_wiki"):
            result["wiki_raw_source_id"] = import_service.import_to_wiki(
                db, project_id=project_id, job_id=job.id,
            )
    except Exception as e:  # noqa: BLE001
        db.rollback()
        result = {"error": str(e)[:500]}
    job.import_result_json = json.dumps(result, ensure_ascii=False, default=str)
    db.commit()


def _collect_ocr_text(db, page_pk: int) -> str:
    from sqlalchemy import select

    rows = db.execute(
        select(LanhuOcrBlock.text)
        .where(LanhuOcrBlock.page_id == page_pk)
        .order_by(LanhuOcrBlock.asset_id, LanhuOcrBlock.order_index)
    ).all()
    return "\n".join(r[0] for r in rows if r[0])


def _is_rel(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False
