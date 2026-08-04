"""FFmpeg/ffprobe 流媒体探测服务 — 子进程调用 ffprobe 解析流指标。"""
from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
from urllib.parse import urlparse
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
        "extract": lambda fmt, streams: _extract_bitrate(fmt, streams),
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

    # 6. HLS 码率实测（C74-1）：format.bit_rate 是 m3u8 播放列表值，需按分段大小/时长实测
    if protocol.upper() == "HLS":
        for m in metrics:
            if m["name"] == "码率" and (m["value"] is None or float(m["value"] or 0) < 100):
                measured = _measure_hls_bitrate(url)
                if measured:
                    m["value"] = measured
                    m["passed"] = _compare_metric(measured, m["threshold"], m["name"])
                    m["raw_value"] = f"hls-segments:{measured}"
                else:
                    m["raw_value"] = "hls-segments:unavailable"

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


def _extract_bitrate(fmt: dict, streams: list) -> float | None:
    """提取媒体码率（kbps）。

    口径（C74-1 修复）：
    1. 优先媒体流 bit_rate（视频流优先）——流媒体的真实值；
    2. HLS 场景的 format.bit_rate 是 m3u8 播放列表码率（实测 24bps），禁止作为媒体码率兜底，
       由 probe_stream 用分段大小/时长实测；
    3. 非 HLS 容器兜底 format.bit_rate。
    """
    for s in streams:
        if s.get("codec_type") == "video":
            br = s.get("bit_rate")
            if br:
                try:
                    return round(float(br) / 1000, 2)
                except (TypeError, ValueError):
                    # 非数字 bit_rate（如空串/占位）：跳过该流，继续尝试下一候选
                    pass
    fmt_name = (fmt.get("format_name") or "").lower()
    if fmt_name == "hls":
        return None
    val = fmt.get("bit_rate")
    if val is not None:
        try:
            return round(float(val) / 1000, 2)
        except (TypeError, ValueError):
            return None
    return None


def _measure_hls_bitrate(url: str, max_segments: int = 5, timeout: float = 15.0) -> float | None:
    """按 HLS 分段实测码率（kbps）：拉取媒体播放列表，取前 N 个分段的字节数与时长。"""
    try:
        import httpx
    except ImportError:
        return None

    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        parsed = urlparse(url)
        headers["Referer"] = f"{parsed.scheme}://{parsed.netloc}/"
        query_suffix = f"?{parsed.query}" if parsed.query else ""
        base = url[: url.rfind("/") + 1]

        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            lines = resp.text.splitlines()

            segments: list[tuple[str, float]] = []
            i = 0
            while i < len(lines) and len(segments) < max_segments * 2:
                line = lines[i].strip()
                if line.startswith("#EXTINF"):
                    duration = 0.0
                    m = re.search(r"#EXTINF:\s*([0-9.]+)", line)
                    if m:
                        duration = float(m.group(1))
                    if i + 1 < len(lines) and lines[i + 1].strip() and not lines[i + 1].strip().startswith("#"):
                        seg = lines[i + 1].strip()
                        if seg.startswith("http"):
                            seg_url = seg + (query_suffix if "?" not in seg else "")
                        else:
                            seg_url = base + seg + query_suffix
                        segments.append((seg_url, duration))
                        i += 2
                        continue
                i += 1

            if not segments:
                return None

            total_bytes = 0
            total_duration = 0.0
            for seg_url, duration in segments[:max_segments]:
                try:
                    with client.stream("GET", seg_url, headers={**headers, "Range": "bytes=0-0"}) as sr:
                        length = _content_length_from_range(sr.headers.get("content-range"))
                        if length is None:
                            data = sr.read()
                            length = len(data)
                    if length and duration:
                        total_bytes += length
                        total_duration += duration
                except Exception:
                    continue

            if not total_duration:
                return None
            kbps = (total_bytes * 8) / total_duration / 1000
            return round(kbps, 2) if kbps > 0 else None
    except Exception:
        return None


def _content_length_from_range(content_range: str | None) -> int | None:
    """从 Content-Range（bytes 0-0/12345）解析总长度。"""
    if not content_range:
        return None
    try:
        total = content_range.split("/")[-1].strip()
        if total.isdigit():
            return int(total)
    except Exception:
        # Content-Range 格式非预期（如缺失 total）：返回 None，由调用方走整段下载兜底
        pass
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

    if name in ("码率", "帧率", "分辨率", "编码格式", "流可用性"):
        return v >= t
    return v <= t
