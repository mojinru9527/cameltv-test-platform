"""Tests for ffmpeg_service metric extraction (C74-1 bitrate calibration)."""
from __future__ import annotations

import httpx

from app.services import ffmpeg_service


class TestExtractBitrate:
    def test_video_stream_bitrate_is_preferred(self) -> None:
        fmt = {"bit_rate": "24", "format_name": "hls"}
        streams = [
            {"codec_type": "video", "bit_rate": "2500000"},
            {"codec_type": "audio", "bit_rate": "128000"},
        ]
        assert ffmpeg_service._extract_bitrate(fmt, streams) == 2500.0

    def test_hls_format_bitrate_is_not_used_as_fallback(self) -> None:
        """HLS 的 format.bit_rate 是播放列表值，禁止作为媒体码率兜底。"""
        fmt = {"bit_rate": "24", "format_name": "hls"}
        streams = [{"codec_type": "video", "bit_rate": None}]
        assert ffmpeg_service._extract_bitrate(fmt, streams) is None

    def test_non_hls_format_bitrate_fallback(self) -> None:
        fmt = {"bit_rate": "1500000", "format_name": "mp4"}
        streams = [{"codec_type": "video", "bit_rate": None}]
        assert ffmpeg_service._extract_bitrate(fmt, streams) == 1500.0


class TestMeasureHlsBitrate:
    PLAYLIST = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:11
#EXTINF:10.000000,
main_0.ts
#EXTINF:10.000000,
main_1.ts
"""

    def test_segment_based_bitrate_computation(self, monkeypatch) -> None:
        requested: list[str] = []

        class FakeResponse:
            text = TestMeasureHlsBitrate.PLAYLIST

            def raise_for_status(self) -> None:
                return None

        class FakeStream:
            headers = {"content-range": "bytes 0-0/1250000"}

            def __enter__(self):
                return self

            def __exit__(self, *args) -> None:
                return None

            def read(self) -> bytes:
                return b"x"

        class FakeClient:
            def __init__(self, **kwargs) -> None:
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args) -> None:
                return None

            def get(self, url: str, headers=None):
                requested.append(url)
                return FakeResponse()

            def stream(self, method: str, url: str, headers=None):
                requested.append(url)
                return FakeStream()

        monkeypatch.setattr(httpx, "Client", FakeClient)
        url = "https://liveplay2.camel4.live/hls/main.m3u8?Expires=1&KeyName=k&Signature=s"
        kbps = ffmpeg_service._measure_hls_bitrate(url, max_segments=2)
        assert kbps == 1000.0
        # 分段 URL 必须继承签名查询串
        assert any(u.endswith("main_0.ts?Expires=1&KeyName=k&Signature=s") for u in requested)
        assert any(u.endswith("main_1.ts?Expires=1&KeyName=k&Signature=s") for u in requested)

    def test_unavailable_on_http_error(self, monkeypatch) -> None:
        class BrokenClient:
            def __init__(self, **kwargs) -> None:
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args) -> None:
                return None

            def get(self, url: str, headers=None):
                raise RuntimeError("network down")

            def stream(self, method: str, url: str, headers=None):
                raise RuntimeError("network down")

        monkeypatch.setattr(httpx, "Client", BrokenClient)
        assert ffmpeg_service._measure_hls_bitrate("https://example.com/main.m3u8") is None


class TestCompareMetric:
    def test_probe_score_uses_greater_equal(self) -> None:
        """流可用性 score=100 ≥ 阈值 50 应判通过（C74-1 口径修正）。"""
        assert ffmpeg_service._compare_metric(100, 50, "流可用性") is True
        assert ffmpeg_service._compare_metric(49, 50, "流可用性") is False

    def test_latency_uses_less_equal(self) -> None:
        assert ffmpeg_service._compare_metric(1453, 2000, "起播时延") is True
