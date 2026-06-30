"""GET /api/reports  — 报告查询。"""
import json
from pathlib import Path

from fastapi import APIRouter

from core.config_loader import ROOT

router = APIRouter(tags=["report"])


@router.get("/reports")
def list_reports(limit: int = 20):
    summary_dir = ROOT / "data" / "reports" / "summary"
    if not summary_dir.exists():
        return {"reports": [], "total": 0}

    files = sorted(summary_dir.glob("run-*.json"), reverse=True)[:limit]
    reports = []
    for fp in files:
        try:
            reports.append(json.loads(fp.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            continue
    return {"reports": reports, "total": len(reports)}


@router.get("/reports/{run_id}/summary")
def get_report_summary(run_id: int):
    fp = ROOT / "data" / "reports" / "summary" / f"run-{run_id}.json"
    if not fp.exists():
        return {"error": "not found"}
    return json.loads(fp.read_text(encoding="utf-8"))
