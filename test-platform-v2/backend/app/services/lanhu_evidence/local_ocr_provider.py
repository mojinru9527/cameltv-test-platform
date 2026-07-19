"""本地命令 OCR provider —— shell 调用可配置 OCR 命令。

`lanhu_ocr_command` 为命令模板，用 {image} 占位图片路径，例如：
    paddleocr --image {image} --json
命令须逐行输出 JSON：{"text":"...","confidence":0.96,"bbox":[x1,y1,x2,y2]}。
未配置命令时返回 status="unavailable"（不视为失败，交由合并/质量步骤降级处理）。
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from app.core.config import settings
from app.services.lanhu_evidence.ocr_provider import (
    OcrProvider,
    OcrResult,
    OcrTextBlock,
)


def parse_command_output(stdout: str) -> list[OcrTextBlock]:
    """解析逐行 JSON OCR 输出为 OcrTextBlock 列表。忽略非 JSON 行。"""
    blocks: list[OcrTextBlock] = []
    for idx, line in enumerate(stdout.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(obj, dict):
            continue
        text = str(obj.get("text", "")).strip()
        if not text:
            continue
        bbox = obj.get("bbox") or [0, 0, 0, 0]
        try:
            bbox = [int(x) for x in bbox]
        except (TypeError, ValueError):
            bbox = [0, 0, 0, 0]
        blocks.append(
            OcrTextBlock(
                text=text,
                confidence=float(obj.get("confidence", 0.0)),
                bbox=bbox,
                order_index=idx,
            )
        )
    return blocks


class LocalCommandOcrProvider(OcrProvider):
    def recognize(self, image_path: Path) -> OcrResult:
        if not settings.lanhu_ocr_command:
            return OcrResult(
                status="unavailable",
                raw_json={},
                error_message="lanhu_ocr_command 未配置",
            )
        cmd = settings.lanhu_ocr_command.replace("{image}", str(image_path))
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=120,
            )
        except subprocess.TimeoutExpired:
            return OcrResult(status="failed", raw_json={}, error_message="OCR 命令超时")
        if result.returncode != 0:
            return OcrResult(
                status="failed",
                raw_json={"stderr": result.stderr[:2000]},
                error_message=(result.stderr or "OCR 命令非零退出")[:500],
            )
        blocks = parse_command_output(result.stdout)
        # 按最小置信度过滤
        min_conf = settings.lanhu_ocr_min_confidence
        kept = [b for b in blocks if b.confidence >= min_conf] or blocks
        return OcrResult(
            status="success",
            blocks=kept,
            raw_json={"stdout": result.stdout[:2000]},
        )
