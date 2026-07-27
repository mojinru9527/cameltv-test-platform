"""证据包结构化 JSON 导出 —— 系统真源，保留每页可追溯来源引用。

每页带 source_refs(doc_id/version_id/page_id)，供 RAG/Wiki/需求导入回溯到蓝湖原页与截图。
"""
from __future__ import annotations

import json
from pathlib import Path


def export_json(output_path: Path, job: dict, pages: list[dict]) -> Path:
    doc_id = job.get("doc_id", "")
    version_id = job.get("version_id", "")

    out_pages = []
    for p in pages:
        out_pages.append({
            "page_id": p.get("page_id", ""),
            "page_name": p.get("page_name", ""),
            "page_path": p.get("page_path", ""),
            "merged_text": p.get("merged_text", ""),
            "screenshots": list(p.get("screenshots") or []),
            "quality": p.get("quality") or {},
            "source_refs": {
                "doc_id": doc_id,
                "version_id": version_id,
                "page_id": p.get("page_id", ""),
            },
        })

    data = {
        "job_id": job.get("job_id"),
        "source_type": "lanhu_evidence_pack",
        "source_url": job.get("source_url", ""),
        "doc_id": doc_id,
        "version_id": version_id,
        "page_count": len(out_pages),
        "pages": out_pages,
    }

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path
