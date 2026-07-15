from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.services.ui_test_service import _run_to_dict


def _run(**overrides):
    values = {
        "id": 1,
        "job_id": 2,
        "status": "running",
        "result": "{}",
        "screenshots": "[]",
        "video_url": "",
        "trace_id": "",
        "base_url": "https://www.camel1.tv",
        "started_at": datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=2),
        "finished_at": None,
        "error_message": "",
        "stdout": "",
        "stderr": "",
        "artifact_dir": "",
        "report_json_path": "",
        "html_report_path": "",
        "process_id": None,
        "cancel_requested": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_running_duration_accepts_sqlite_naive_started_at():
    result = _run_to_dict(_run())
    assert result["duration"] >= 0


def test_finished_duration_accepts_mixed_timezone_timestamps():
    started = datetime(2026, 7, 15, 6, 0, 0)
    finished = datetime(2026, 7, 15, 6, 0, 5, tzinfo=timezone.utc)
    result = _run_to_dict(_run(status="done", started_at=started, finished_at=finished))
    assert result["duration"] == 5.0
