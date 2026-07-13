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
