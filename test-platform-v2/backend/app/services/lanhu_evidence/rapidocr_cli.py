"""内置 rapidocr OCR CLI —— 逐行 JSON 输出，兼容 local_ocr_provider.parse_command_output。

用法：
    python -m app.services.lanhu_evidence.rapidocr_cli --image <截图路径>

stdout 每行一个 JSON：{"text": "...", "confidence": 0.99, "bbox": [x1, y1, x2, y2]}
失败时错误信息写 stderr，退出码非 0。

模型随 rapidocr_onnxruntime wheel 打包（PP-OCRv4 det/rec/cls，约 16MB），
首次运行无需联网下载；模型缓存位置即包内 models 目录。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# 强制 UTF-8 输出，避免 Windows GBK 控制台在子进程管道中产生乱码/编码错误。
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):  # pragma: no cover - 非流式 stdout 的兜底
    pass


def _bbox_from_points(points: list[list[float]]) -> list[int]:
    """rapidocr 返回 4 点框 [[x1,y1],[x2,y2],[x3,y3],[x4,y4]] → [x1,y1,x2,y2] 整数框。"""
    xs = [float(p[0]) for p in points]
    ys = [float(p[1]) for p in points]
    return [int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))]


def recognize_image(image_path: Path) -> list[dict]:
    """执行 rapidocr 识别，返回逐行 dict 列表（保留全部识别块，不做置信度过滤）。"""
    from rapidocr_onnxruntime import RapidOCR

    engine = RapidOCR()
    result, _elapse = engine(str(image_path))
    blocks: list[dict] = []
    for item in result or []:
        points, text, confidence = item
        blocks.append(
            {
                "text": str(text),
                "confidence": float(confidence),
                "bbox": _bbox_from_points(points),
            }
        )
    return blocks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="rapidocr 内置 OCR CLI")
    parser.add_argument("--image", required=True, help="截图图片路径")
    args = parser.parse_args(argv)

    image = Path(args.image)
    if not image.exists():
        print(f"图片不存在: {image}", file=sys.stderr)
        return 2

    try:
        blocks = recognize_image(image)
    except Exception as exc:  # noqa: BLE001 — CLI 边界，任何异常转为失败退出
        print(f"OCR 识别失败: {exc}", file=sys.stderr)
        return 1

    for block in blocks:
        print(json.dumps(block, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
