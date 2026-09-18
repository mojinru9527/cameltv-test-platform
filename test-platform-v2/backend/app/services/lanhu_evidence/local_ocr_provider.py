"""本地命令 OCR provider —— 以 argv 数组调用可配置 OCR 命令（不经 shell）。

`lanhu_ocr_command` 为命令模板：{image} 占位图片路径，{python} 占位当前解释器
（默认模板即内置 rapidocr CLI），例如：
    paddleocr --image {image} --json
命令须逐行输出 JSON：{"text":"...","confidence":0.96,"bbox":[x1,y1,x2,y2]}。
未配置命令时返回 status="unavailable"（不视为失败，交由合并/质量步骤降级处理）。

Batch 258 / B1-3：模板经 `build_command()` 用哨兵占位 + `shlex.split` 解析为参数数组，
`shell=False` 执行，路径含空格/分号时不会被切分或变形（关闭审计基线 S3）。
"""
from __future__ import annotations

import json
import shlex
import subprocess
import sys
from pathlib import Path

from app.core.config import settings
from app.core.process_tree import run_supervised
from app.services.lanhu_evidence.ocr_provider import (
    OcrProvider,
    OcrResult,
    OcrTextBlock,
)

_PYTHON_SENTINEL = "__CAMELTV_PYTHON__"
_IMAGE_SENTINEL = "__CAMELTV_IMAGE__"


def build_command(template: str, *, image_path: Path, python_executable: str) -> list[str]:
    """把命令模板解析为 argv 数组。

    先用哨兵 token 占位、分词、再回填真实值：若先插值后 `shlex.split`，
    `/tmp/a b.png` 会被切成两个 argv（命令语义变形）；哨兵法把「分词」与
    「插值」彻底解耦，路径始终是单一 argv 元素。
    """
    templated = template.replace("{python}", _PYTHON_SENTINEL).replace("{image}", _IMAGE_SENTINEL)
    argv = shlex.split(templated)
    replacements = {_PYTHON_SENTINEL: python_executable, _IMAGE_SENTINEL: str(image_path)}
    return [replacements.get(token, token) for token in argv]


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
        cmd = build_command(
            settings.lanhu_ocr_command,
            image_path=image_path,
            python_executable=sys.executable,
        )
        try:
            run_process = run_supervised if settings.heavy_task_budget_enabled else subprocess.run
            result = run_process(
                cmd,
                shell=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
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
        # 保留全部识别块；置信度仅作为块元数据，由合并/质量层决定是否提示人工复核。
        return OcrResult(
            status="success",
            blocks=blocks,
            raw_json={"stdout": result.stdout[:2000]},
        )
