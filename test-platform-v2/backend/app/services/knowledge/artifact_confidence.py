"""AI 产物置信度计算（Batch 153 / C126-3）。

统一入口：
- severity_confidence(severity)          — 按严重度 P0-P3 映射
- artifact_confidence_from_output(output) — 从 LLM 结构化输出提取（显式 confidence 优先，
                                           其次 review_items 平均，兜底 0.6）
"""
from __future__ import annotations

from typing import Any

_SEVERITY_CONFIDENCE = {
    "P0": 0.9,
    "P1": 0.85,
    "P2": 0.75,
    "P3": 0.65,
}
_DEFAULT_OUTPUT_CONFIDENCE = 0.6


def severity_confidence(severity: str | None) -> float:
    """按严重度映射置信度；未知严重度用 P2 默认值。"""
    return _SEVERITY_CONFIDENCE.get((severity or "P2").upper(), _SEVERITY_CONFIDENCE["P2"])


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def artifact_confidence_from_output(output: dict[str, Any] | None, fallback: float = _DEFAULT_OUTPUT_CONFIDENCE) -> float:
    """从 AI 结构化输出提取置信度（0-1）。

    优先级：
    1. output.confidence（数值）——LLM 显式声明
    2. output.review_items[*].confidence 的平均值
    3. fallback
    """
    if not isinstance(output, dict):
        return _clamp01(fallback)

    explicit = output.get("confidence")
    if isinstance(explicit, (int, float)) and not isinstance(explicit, bool):
        return _clamp01(explicit)

    review_items = output.get("review_items")
    if isinstance(review_items, list) and review_items:
        values = [
            item.get("confidence")
            for item in review_items
            if isinstance(item, dict) and isinstance(item.get("confidence"), (int, float))
        ]
        if values:
            return _clamp01(sum(float(v) for v in values) / len(values))

    return _clamp01(fallback)
