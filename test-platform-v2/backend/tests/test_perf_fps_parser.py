"""SurfaceFlinger latency 解析器单元测试（B99：Android 14 fps=0 缺陷回归）。"""
from __future__ import annotations

from app.services.perf_collector_service import (
    _parse_surfaceflinger_latency,
    _select_fps_layers,
)


def _raw(refresh_ns: int, frames: list[tuple[int, int]]) -> str:
    lines = ["---- TIME: 2026-08-05 20:49:18.527 ----", str(refresh_ns)]
    for desired, actual in frames:
        lines.append(f"{desired} {actual} {actual}")
    return "\n".join(lines)


def test_android14_time_header_is_skipped() -> None:
    """Android 12+ 的 `---- TIME:` 头行不得破坏解析（SoloX 2.9.3 在此崩溃）。"""
    refresh = 16_666_666
    base = 1_000_000_000_000
    frames = [(base + i * refresh, base + i * refresh) for i in range(60)]
    result = _parse_surfaceflinger_latency(_raw(refresh, frames))
    assert "error" not in result
    assert result["frame_count"] == 60
    assert 59 <= result["fps"] <= 61
    assert result["jank"] == 0


def test_fps_counts_last_second_window() -> None:
    """fps 只统计最近 1 秒窗口内的帧，不把历史帧计入。"""
    refresh = 16_666_666
    base = 1_000_000_000_000
    old = [(base - 2_000_000_000 + i * refresh, base - 2_000_000_000 + i * refresh) for i in range(60)]
    recent = [(base + i * refresh, base + i * refresh) for i in range(30)]
    result = _parse_surfaceflinger_latency(_raw(refresh, old + recent))
    assert result["frame_count"] == 90
    assert result["fps"] == 30


def test_jank_detection() -> None:
    """帧间隔超过 2×刷新周期（且非空闲边界）计为一次 jank。"""
    refresh = 16_666_666
    base = 1_000_000_000_000
    frames = [(base, base), (base + 80_000_000, base + 80_000_000)]
    result = _parse_surfaceflinger_latency(_raw(refresh, frames))
    assert result["jank"] >= 1


def test_idle_gap_is_not_counted_as_jank() -> None:
    """超过 500ms 的帧间隔视为空闲/切换边界，不计入 jank。"""
    refresh = 16_666_666
    base = 1_000_000_000_000
    frames = [(base, base), (base + 700_000_000, base + 700_000_000)]
    result = _parse_surfaceflinger_latency(_raw(refresh, frames))
    assert result["jank"] == 0


def test_jank_only_counts_window_frames() -> None:
    """窗口（最近 1 秒）之外的旧帧空隙不参与 jank 统计。"""
    refresh = 16_666_666
    base = 1_000_000_000_000
    # 2 秒前的一段密集帧 + 窗口内 2 帧（间隔 80ms → 计 1 jank）
    old = [(base - 2_000_000_000 + i * refresh, base - 2_000_000_000 + i * refresh) for i in range(60)]
    recent = [(base, base), (base + 80_000_000, base + 80_000_000)]
    result = _parse_surfaceflinger_latency(_raw(refresh, old + recent))
    assert result["fps"] == 2
    assert result["jank"] == 1


def test_garbage_input_returns_zero_with_error() -> None:
    result = _parse_surfaceflinger_latency("not a latency dump at all")
    assert result["fps"] == 0
    assert result["jank"] == 0
    assert "error" in result


def test_zero_timestamps_are_ignored() -> None:
    """未提交帧（时间戳为 0）不参与 fps/jank 统计。"""
    refresh = 16_666_666
    base = 1_000_000_000_000
    frames = [(0, 0)] * 20 + [(base + i * refresh, base + i * refresh) for i in range(30)]
    result = _parse_surfaceflinger_latency(_raw(refresh, frames))
    assert result["frame_count"] == 30
    assert result["fps"] == 30


def test_layer_selection_skips_input_sink_and_activity_record() -> None:
    layers = [
        "e8b4571 ActivityRecordInputSink com.camelrn/.MainActivity#538",
        "ActivityRecord{ed1c718 u0 com.camelrn/.MainActivity t417}#534",
        "240a46f com.camelrn/com.camelrn.MainActivity#542",
        "com.camelrn/com.camelrn.MainActivity#543",
        "StatusBar#0",
    ]
    selected = _select_fps_layers(layers, "com.camelrn")
    assert len(selected) == 2
    assert all("InputSink" not in ln and "ActivityRecord{" not in ln for ln in selected)
    assert selected[0].startswith("240a46f")
