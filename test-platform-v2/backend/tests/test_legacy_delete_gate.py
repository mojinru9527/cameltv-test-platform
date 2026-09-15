import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_legacy_files_remain_until_delete_gate_is_fully_satisfied() -> None:
    gate = json.loads((ROOT / "backend/tests/fixtures/legacy_delete_gate.json").read_text(encoding="utf-8"))
    if not all(gate.values()):
        assert (ROOT / "backend/app/services/api_task_worker.py").exists()
        assert (ROOT / "backend/app/services/plan_execution_queue.py").exists()
        assert (ROOT / "backend/app/modules/aitde/execution/legacy_bridge.py").exists()
