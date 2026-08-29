"""Legacy API/UI bridge tests (V31-009/V31-010)."""
from __future__ import annotations

import pytest

from app.modules.aitde.execution import legacy_bridge, repository
from app.modules.aitde.execution.service import create_run

# Reuse the run-creation helpers so a legacy bridge lands on a real run.


def _make_run(db, scenario_graph):
    from app.modules.aitde.environment import snapshot_service

    snap = snapshot_service.capture_snapshot(
        db, environment_id=1, mission_id=scenario_graph["mission"].id, project_id=1,
        data={"build_label": "v3.1"},
    )
    return create_run(
        db,
        {
            "mission_id": scenario_graph["mission"].id,
            "scenario_id": scenario_graph["scenario"].id,
            "scenario_version_id": scenario_graph["scenario_version"].id,
            "contract_version_id": scenario_graph["contract_version"].id,
            "environment_id": 1,
            "environment_snapshot_id": snap.id,
        },
        project_id=1,
        user_id=9,
    )


def test_api_bridge_is_idempotent_and_does_not_hit_legacy(db, scenario_graph):
    run = _make_run(db, scenario_graph)
    legacy_id = 777
    result = legacy_bridge.bridge_api_item(
        db, project_id=1, run_id=run.id, legacy_id=legacy_id,
        request={"url": "https://api.example.com/x"}, response={"code": 0, "data": {}},
    )
    assert result["run_id"] == run.id
    assert len(result["artifacts"]) == 2  # REQUEST + RESPONSE

    # second registration must be a no-op (idempotent link)
    again = legacy_bridge.bridge_api_item(
        db, project_id=1, run_id=run.id, legacy_id=legacy_id,
        request={"url": "x"}, response={"code": 0},
    )
    assert again.get("already_linked") is True
    steps = repository.list_steps(db, run.id, 1)
    assert len(steps) == 1  # only one step created despite two calls


def test_ui_bridge_registers_screenshots_and_video(db, scenario_graph):
    run = _make_run(db, scenario_graph)
    result = legacy_bridge.bridge_ui_run(
        db, project_id=1, run_id=run.id, legacy_id=888,
        screenshots=["/art/shot1.png", "/art/shot2.png"],
        video_url="https://cdn/v.mp4", trace_id="trace-abc",
        result_summary={"pass": 3},
    )
    types = {a["type"] for a in result["artifacts"]}
    assert "SCREENSHOT" in types
    assert "VIDEO" in types
    assert "PW_TRACE" in types


# ── v331-gap A1/A3: deep wiring behaviour ───────────────────────────────────


def test_api_bridge_auto_creates_run_and_maps_assertions(db):
    """run_id=None 自动创建 LEGACY_BRIDGE Run：证据 + 断言映射 + Outcome 冻结。"""
    result = legacy_bridge.bridge_api_item(
        db, project_id=1, run_id=None, legacy_id=501,
        request={"method": "GET", "resolved_url": "https://api.example.com/x"},
        response={"status_code": 200, "body_preview": '{"code":0}'},
        assertions=[
            {"type": "status_code", "expected": 200, "actual": 200, "passed": True},
            {"type": "jsonpath", "expected": 0, "actual": 0, "passed": True},
        ],
    )
    assert "run_id" in result and "outcome" in result
    run_id = result["run_id"]
    run = repository.get_run(db, run_id, 1)
    assert run is not None
    assert run.trigger_type == "LEGACY_BRIDGE"
    assert run.runtime_status == "FINISHED"
    # 全部断言 PASS + REQUEST/RESPONSE 证据齐备 → 真实 PASS（不再是恒 INCONCLUSIVE）
    assert result["outcome"] == "PASS"

    assertions = repository.list_assertions(db, run_id, 1)
    assert len(assertions) == 2
    assert all(a.result == "PASS" for a in assertions)
    assert all(a.oracle_id == 0 for a in assertions)
    import json as _json
    snapshot = _json.loads(assertions[0].oracle_snapshot_json)
    assert snapshot["source"] == "legacy_bridge"
    assert snapshot["oracle_type"] == "API"

    types = {e.evidence_type for e in repository.list_evidence(db, run_id, 1)}
    assert {"REQUEST", "RESPONSE"} <= types

    # 幂等：重复桥接返回已链接且指向同一 Run
    again = legacy_bridge.bridge_api_item(
        db, project_id=1, run_id=None, legacy_id=501, request={"x": 1},
    )
    assert again["already_linked"] is True
    assert again["run_id"] == run_id


def test_api_bridge_missing_required_evidence_degrades_to_inconclusive(db):
    """缺少 REQUIRED 证据（无 RESPONSE）→ 不得 PASS，降级 INCONCLUSIVE。"""
    result = legacy_bridge.bridge_api_item(
        db, project_id=1, run_id=None, legacy_id=502,
        request={"method": "GET"},
        response=None,
        assertions=[{"type": "status_code", "expected": 200, "actual": 200, "passed": True}],
    )
    assert result["outcome"] == "INCONCLUSIVE"


def test_ui_bridge_reads_real_bytes_and_console(db, tmp_path):
    """artifact_dir 存在时读取真实文件字节注册证据，console 文本注册 CONSOLE。"""
    shot = tmp_path / "shot-1.png"
    shot_bytes = b"PNG-SCREENSHOT-BYTES"  # ASCII，避开 sanitizer 的替换编码
    shot.write_bytes(shot_bytes)
    result = legacy_bridge.bridge_ui_run(
        db, project_id=1, run_id=None, legacy_id=601,
        screenshots=["shot-1.png"], video_url=None, trace_id=None,
        artifact_dir=str(tmp_path), console_text="console log line",
        assertions=[{"type": "ui_result", "passed": True}],
    )
    assert result["outcome"] == "PASS"  # SCREENSHOT + CONSOLE 齐备 + 断言 PASS
    evidence = repository.list_evidence(db, result["run_id"], 1)
    by_type = {e.evidence_type: e for e in evidence}
    assert by_type["SCREENSHOT"].size_bytes == len(shot_bytes)
    assert by_type["SCREENSHOT"].content_type == "image/png"
    assert by_type["CONSOLE"].content_type == "text/plain"


def test_ui_bridge_failed_run_maps_fail_assertion(db):
    """UI 失败 → FAIL 断言 → BUSINESS_FAIL（自动化错误不吞业务结论）。"""
    result = legacy_bridge.bridge_ui_run(
        db, project_id=1, run_id=None, legacy_id=602,
        screenshots=[], step_status="FAILED",
        assertions=[{"type": "ui_result", "passed": False}],
    )
    assert result["outcome"] == "BUSINESS_FAIL"


def test_bridge_rejects_run_from_other_project(db, scenario_graph):
    """跨项目 run_id 写入必须被拒绝（租户边界）。"""
    run = _make_run(db, scenario_graph)
    from app.core.exceptions import APIException

    with pytest.raises(APIException) as exc:
        legacy_bridge.bridge_api_item(
            db, project_id=2, run_id=run.id, legacy_id=999, request={"x": 1},
        )
    assert exc.value.http_status == 404
