"""FFmpeg/ffprobe 流媒体探测服务 — 子进程调用 ffprobe 解析流指标。"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from typing import Any

logger = logging.getLogger("ffmpeg")

# ── 配置 ──
DEFAULT_TIMEOUT = 30  # seconds per stream probe
SUPPORTED_PROTOCOLS = {"HLS", "FLV", "RTMP", "DASH", "HTTP", "HTTPS"}

# 指标定义: (名称, ffprobe 提取函数, 阈值, 单位)
METRIC_DEFS = [
    {
        "name": "起播时延",
        "unit": "ms",
        "threshold": 2000,
        "extract": lambda fmt, streams: _extract_start_time(fmt),
        "recommended": "<= 2000",
    },
    {
        "name": "码率",
        "unit": "kbps",
        "threshold": 500,
        "extract": lambda fmt, streams: _extract_bitrate(fmt),
        "recommended": ">= 500",
    },
    {
        "name": "帧率",
        "unit": "fps",
        "threshold": 24,
        "extract": lambda fmt, streams: _extract_framerate(streams),
        "recommended": ">= 24",
    },
    {
        "name": "分辨率",
        "unit": "px",
        "threshold": 1280 * 720,
        "extract": lambda fmt, streams: _extract_resolution(streams),
        "recommended": ">= 1280×720",
    },
    {
        "name": "流可用性",
        "unit": "score",
        "threshold": 50,
        "extract": lambda fmt, streams: _extract_probe_score(fmt),
        "recommended": ">= 50",
    },
    {
        "name": "编码格式",
        "unit": "",
        "threshold": 1,
        "extract": lambda fmt, streams: _check_codec(streams, ["h264", "aac", "hevc", "av1"]),
        "recommended": "H.264/AAC/HEVC/AV1",
    },
]


def _check_ffmpeg_installed() -> tuple[bool, str]:
    """检查 ffprobe 是否可用。"""
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return False, "ffprobe 命令不可用，请安装 FFmpeg (apt install ffmpeg 或 brew install ffmpeg)"
    try:
        result = subprocess.run(
            [ffprobe, "-version"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            version_line = result.stdout.split("\n")[0] if result.stdout else "ffprobe"
            return True, version_line.strip()
        return False, "ffprobe 未正确安装"
    except subprocess.TimeoutExpired:
        return False, "检查 ffprobe 版本超时"
    except Exception as e:
        return False, f"检查 ffprobe 失败: {e}"


def probe_stream(url: str, protocol: str = "HLS", timeout: int = DEFAULT_TIMEOUT) -> dict:
    """探测一个流媒体 URL，返回结构化指标。

    Args:
        url: 流媒体地址 (HLS .m3u8, RTMP, HTTP 等)
        protocol: 协议类型
        timeout: 超时秒数

    Returns:
        {"ok": bool, "metrics": [...], "raw": {...}, "error": str | None}
    """
    # 1. 验证
    if not url or not url.strip():
        return {"ok": False, "metrics": [], "raw": {}, "error": "流地址为空"}

    if not url.startswith(("http://", "https://", "rtmp://", "rtmps://", "hls://")):
        return {"ok": False, "metrics": [], "raw": {}, "error": f"不支持的流协议: {url[:50]}..."}

    # 2. 检查 ffprobe
    ok, version = _check_ffmpeg_installed()
    if not ok:
        return {"ok": False, "metrics": [], "raw": {}, "error": f"FFmpeg 不可用: {version}"}

    # 3. 执行 ffprobe
    ffprobe = shutil.which("ffprobe") or "ffprobe"
    cmd = [
        ffprobe,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        "-analyzeduration", "10000000",   # 10s max for analysis
        "-probesize", "50000000",          # 50MB max probe data
        url,
    ]

    logger.info(f"Probing: {' '.join(cmd[:-1])} <url>")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True, text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "metrics": [], "raw": {}, "error": f"ffprobe 超时 ({timeout}s)"}
    except Exception as e:
        return {"ok": False, "metrics": [], "raw": {}, "error": f"ffprobe 执行失败: {e}"}

    if result.returncode != 0:
        stderr = (result.stderr or "")[:500]
        return {"ok": False, "metrics": [], "raw": {}, "error": f"ffprobe 错误: {stderr}"}

    # 4. 解析 JSON
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        return {"ok": False, "metrics": [], "raw": {}, "error": f"ffprobe 输出解析失败: {e}"}

    fmt = data.get("format", {})
    streams = data.get("streams", [])

    # 5. 提取指标
    metrics = []
    for mdef in METRIC_DEFS:
        try:
            raw_value = mdef["extract"](fmt, streams)
        except Exception as e:
            raw_value = None
            logger.warning(f"Failed to extract {mdef['name']}: {e}")

        value = _normalize_value(raw_value)
        threshold = mdef["threshold"]
        passed = _compare_metric(value, threshold, mdef["name"])

        metrics.append({
            "name": mdef["name"],
            "unit": mdef["unit"],
            "value": value,
            "threshold": threshold,
            "passed": passed,
            "raw_value": raw_value,
            "recommended": mdef.get("recommended", ""),
        })

    return {
        "ok": True,
        "metrics": metrics,
        "raw": {
            "format_name": fmt.get("format_name", ""),
            "duration": fmt.get("duration", ""),
            "size": fmt.get("size", ""),
            "stream_count": len(streams),
            "ffprobe_version": version,
        },
        "error": None,
    }


# ── Metric extraction helpers ──

def _extract_start_time(fmt: dict) -> float | None:
    val = fmt.get("start_time")
    if val is not None:
        return float(val) * 1000  # seconds → ms
    return None


def _extract_bitrate(fmt: dict) -> float | None:
    val = fmt.get("bit_rate")
    if val is not None:
        return round(float(val) / 1000, 2)  # bps → kbps
    return None


def _extract_framerate(streams: list) -> float | None:
    for s in streams:
        if s.get("codec_type") == "video":
            fps_str = s.get("r_frame_rate", "")
            if fps_str and "/" in fps_str:
                parts = fps_str.split("/")
                if int(parts[1]) != 0:
                    return round(float(parts[0]) / float(parts[1]), 2)
            avg_fps = s.get("avg_frame_rate", "")
            if avg_fps and "/" in avg_fps:
                parts = avg_fps.split("/")
                if int(parts[1]) != 0:
                    return round(float(parts[0]) / float(parts[1]), 2)
    return None


def _extract_resolution(streams: list) -> int | None:
    for s in streams:
        if s.get("codec_type") == "video" and s.get("width") and s.get("height"):
            return int(s["width"]) * int(s["height"])  # total pixels
    return None


def _extract_probe_score(fmt: dict) -> int | None:
    val = fmt.get("probe_score")
    if val is not None:
        return int(val)
    # Fallback: if we have streams and duration, score = 100
    if fmt.get("duration") and fmt.get("format_name"):
        return 100
    return 0


def _check_codec(streams: list, acceptable: list[str]) -> int | None:
    """1 如果有可接受的编码，0 否则。"""
    codecs = []
    for s in streams:
        codec = (s.get("codec_name") or "").lower()
        if codec:
            codecs.append(codec)
    if not codecs:
        return None
    match = any(any(acc in c for acc in acceptable) for c in codecs)
    return 1 if match else 0


def _normalize_value(val: Any) -> Any:
    """标准化值为可序列化的类型。"""
    if val is None:
        return 0
    if isinstance(val, (int, float)):
        return val
    if isinstance(val, bool):
        return 1 if val else 0
    return str(val)


def _compare_metric(value: Any, threshold: Any, name: str) -> bool:
    """将指标值与阈值比较。"""
    if value is None or value == 0:
        return False

    try:
        v = float(value)
        t = float(threshold)
    except (TypeError, ValueError):
        return False

    if name in ("码率", "帧率", "分辨率", "编码格式"):
        return v >= t
    return v <= t
