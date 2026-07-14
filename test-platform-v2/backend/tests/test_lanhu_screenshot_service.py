"""滚动截图规划测试 —— compute_scroll_positions 纯函数确定性。"""
from __future__ import annotations


def test_scroll_positions_cover_page_without_exceeding_limit():
    from app.services.lanhu_evidence.screenshot_service import compute_scroll_positions

    positions = compute_scroll_positions(
        scroll_height=3000,
        viewport_height=1000,
        step_ratio=0.85,
        max_segments=10,
    )

    assert positions[0] == 0
    assert positions[-1] >= 2000
    assert len(positions) <= 10
    # 单调递增，无重复
    assert positions == sorted(positions)
    assert len(positions) == len(set(positions))


def test_scroll_positions_for_short_page_is_single_segment():
    from app.services.lanhu_evidence.screenshot_service import compute_scroll_positions

    assert compute_scroll_positions(900, 1000, 0.85, 10) == [0]


def test_scroll_positions_respects_max_segments():
    from app.services.lanhu_evidence.screenshot_service import compute_scroll_positions

    positions = compute_scroll_positions(100000, 1000, 0.85, 5)
    assert len(positions) == 5


def test_scroll_positions_last_position_bounded_by_scroll_height():
    from app.services.lanhu_evidence.screenshot_service import compute_scroll_positions

    positions = compute_scroll_positions(2500, 1000, 0.85, 30)
    assert positions[-1] <= 2500 - 1000


# ── Task 3: 截断检测 ──

def test_capture_marks_truncated_when_max_segments_cannot_reach_last_position():
    from app.services.lanhu_evidence.screenshot_service import capture_plan

    plan = capture_plan(scroll_height=10000, viewport_height=1000, step_ratio=0.85, max_segments=3)
    assert plan.truncated is True
    assert plan.positions == [0, 850, 1700]


def test_capture_plan_not_truncated_when_last_position_reaches_bottom():
    from app.services.lanhu_evidence.screenshot_service import capture_plan

    plan = capture_plan(scroll_height=2500, viewport_height=1000, step_ratio=0.85, max_segments=30)
    assert plan.truncated is False
    assert plan.positions[-1] == 1500


def test_capture_plan_short_page_not_truncated():
    from app.services.lanhu_evidence.screenshot_service import capture_plan

    plan = capture_plan(scroll_height=900, viewport_height=1000, step_ratio=0.85, max_segments=30)
    assert plan.truncated is False
    assert plan.positions == [0]


def test_actual_scroll_position_must_reach_bottom():
    from app.services.lanhu_evidence.screenshot_service import scroll_reached_bottom

    # A page script that forces the viewport back to the first screen must not
    # be treated as complete merely because the requested position was last.
    assert scroll_reached_bottom(actual_top=0, last_required=2000) is False
    assert scroll_reached_bottom(actual_top=1999, last_required=2000) is True


# ── P0: 内部滚动容器判定 ──

def test_hidden_overflow_element_is_not_an_inner_scroll_container():
    from app.services.lanhu_evidence.screenshot_service import select_inner_scroll_candidate

    candidate = select_inner_scroll_candidate([
        {
            "overflowY": "hidden",
            "scrollHeight": 5000,
            "clientHeight": 800,
            "scrollTopChanged": True,
        },
    ])

    assert candidate is None


def test_inner_scroll_container_must_accept_a_scroll_top_change():
    from app.services.lanhu_evidence.screenshot_service import select_inner_scroll_candidate

    candidate = select_inner_scroll_candidate([
        {
            "overflowY": "auto",
            "scrollHeight": 5000,
            "clientHeight": 800,
            "scrollTopChanged": False,
        },
    ])

    assert candidate is None


def test_largest_working_scrollable_overflow_container_is_selected():
    from app.services.lanhu_evidence.screenshot_service import select_inner_scroll_candidate

    candidate = select_inner_scroll_candidate([
        {
            "overflowY": "scroll",
            "scrollHeight": 3000,
            "clientHeight": 800,
            "scrollTopChanged": True,
        },
        {
            "overflowY": "overlay",
            "scrollHeight": 6000,
            "clientHeight": 900,
            "scrollTopChanged": True,
        },
    ])

    assert candidate is not None
    assert candidate["overflowY"] == "overlay"
    assert candidate["scrollHeight"] == 6000


def test_no_valid_inner_container_keeps_short_document_complete():
    from app.services.lanhu_evidence.screenshot_service import (
        capture_plan,
        select_inner_scroll_candidate,
    )

    candidate = select_inner_scroll_candidate([
        {
            "overflowY": "hidden",
            "scrollHeight": 6000,
            "clientHeight": 900,
            "scrollTopChanged": False,
        },
    ])
    plan = capture_plan(
        scroll_height=900,
        viewport_height=1000,
        step_ratio=0.85,
        max_segments=30,
    )

    assert candidate is None
    assert plan.positions == [0]
    assert plan.truncated is False


def test_inner_scroll_probe_checks_overflow_and_observed_scroll_top_change():
    from app.services.lanhu_evidence.screenshot_service import _INNER_SCROLL_JS

    assert "getComputedStyle(el).overflowY" in _INNER_SCROLL_JS
    assert "['auto', 'scroll', 'overlay']" in _INNER_SCROLL_JS
    assert "scrollTopChanged" in _INNER_SCROLL_JS
