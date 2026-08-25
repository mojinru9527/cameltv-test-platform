"""Batch 112 — response_structure 断言引擎测试（worktree 落点校验 OK）。

与历史接口用例执行脚本的 _assert_structure 语义对齐：
- envelope 键缺失 → 失败
- data.* 缺失（200 信封动态数据）→ warning（passed=True，不判失败）
- records[0].* 记录字段以键存在为准（值可为空）
- len_lte 超界 → 失败；hint 型为信息提示不参与判定
"""

from __future__ import annotations

from app.services.api_execution_service import _assert_response_structure
from app.services.api_execution_service import _run_assertions


def _run(rules: list[dict], body: dict) -> list[dict]:
    return _run_assertions(
        rules,
        status_code=200,
        response_data=body,
        raw_body="",
        duration_ms=100,
    )


def test_envelope_key_exists_passes() -> None:
    results = _run(
        [{"type": "response_structure", "path": "status", "assert": "exists"}],
        {"status": 200, "data": {"records": []}},
    )
    assert results[0]["passed"] is True
    assert results[0]["type"] == "response_structure"


def test_envelope_key_missing_fails() -> None:
    """信封键缺失必须判失败（与脚本一致，login/anonymous 信封漂移即此场景）。"""
    results = _run(
        [{"type": "response_structure", "path": "code", "assert": "exists"}],
        {"timestamp": 1, "status": 400, "msg": "x"},
    )
    assert results[0]["passed"] is False


def test_data_missing_is_warning_not_fail() -> None:
    """200 信封下 data.* 动态缺失 → warning，用例不判失败（B110-5 口径）。"""
    results = _run(
        [
            {"type": "response_structure", "path": "data", "assert": "is_object_or_array"},
            {"type": "response_structure", "path": "data.team", "assert": "exists"},
            {"type": "response_structure", "path": "data.records", "assert": "not_empty"},
        ],
        {"status": 200, "msg": ""},
    )
    assert all(r["passed"] for r in results)
    assert all(r.get("warning") for r in results)


def test_data_list_present_is_object_or_array_passes() -> None:
    results = _run(
        [{"type": "response_structure", "path": "data", "assert": "is_object_or_array"}],
        {"status": 200, "data": [{"id": 1}]},
    )
    assert results[0]["passed"] is True


def test_is_object_or_array_scalar_fails() -> None:
    results = _run(
        [{"type": "response_structure", "path": "data", "assert": "is_object_or_array"}],
        {"status": 200, "data": "plain-string"},
    )
    assert results[0]["passed"] is False


def test_record_path_resolution_works() -> None:
    body = {"status": 200, "data": {"records": [{"id": "a", "score": ""}]}}
    results = _run(
        [
            {"type": "response_structure", "path": "data.records[0].id", "assert": "exists"},
            {"type": "response_structure", "path": "data.records[0].id", "assert": "not_empty"},
        ],
        body,
    )
    assert all(r["passed"] for r in results)


def test_record_field_empty_value_passes_with_not_empty() -> None:
    """records[0].* 记录字段以键存在为准，值为空字符串也通过。"""
    body = {"status": 200, "data": {"records": [{"score": ""}]}}
    results = _run(
        [{"type": "response_structure", "path": "data.records[0].score", "assert": "not_empty"}],
        body,
    )
    assert results[0]["passed"] is True


def test_not_empty_empty_list_fails() -> None:
    body = {"status": 200, "data": {"records": []}}
    results = _run(
        [{"type": "response_structure", "path": "data.records", "assert": "not_empty"}],
        body,
    )
    assert results[0]["passed"] is False


def test_len_lte_within_bound_passes() -> None:
    body = {"status": 200, "data": {"records": list(range(5))}}
    results = _run(
        [{"type": "response_structure", "path": "data.records", "assert": "len_lte", "expected": 10}],
        body,
    )
    assert results[0]["passed"] is True


def test_len_lte_over_bound_fails() -> None:
    body = {"status": 200, "data": {"records": list(range(5))}}
    results = _run(
        [{"type": "response_structure", "path": "data.records", "assert": "len_lte", "expected": 3}],
        body,
    )
    assert results[0]["passed"] is False


def test_hint_rule_is_informational() -> None:
    results = _run(
        [{"type": "response_structure", "assert": "hint", "note": "响应结构与真实调用一致"}],
        {"status": 200},
    )
    assert results[0]["passed"] is True


def test_mixed_status_and_structure_dispatch() -> None:
    results = _run(
        [
            {"type": "status_code", "expected": 200},
            {"type": "response_structure", "path": "status", "assert": "exists"},
            {"type": "response_structure", "path": "data.total", "assert": "exists"},
        ],
        {"status": 200, "data": {"total": 0}},
    )
    assert all(r["passed"] for r in results)


def test_unknown_assertion_type_still_fails() -> None:
    results = _run([{"type": "unknown_assert_xyz"}], {"status": 200})
    assert results[0]["passed"] is False


def test_direct_assert_data_shape_absent() -> None:
    """data 整体缺失（非对象/数组）→ warning 而非失败。"""
    r = _assert_response_structure(
        {"type": "response_structure", "path": "data", "assert": "is_object_or_array"},
        {"status": 200},
    )
    assert r["passed"] is True
    assert r.get("warning")
