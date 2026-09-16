"""内置 rapidocr OCR CLI —— 逐行 JSON 输出，兼容 local_ocr_provider.parse_command_output。

用法：
    python -m app.services.lanhu_evidence.rapidocr_cli --image <截图路径>

stdout 每行一个 JSON：{"text": "...", "confidence": 0.99, "bbox": [x1, y1, x2, y2]}
失败时错误信息写 stderr，退出码非 0。

模型随 rapidocr_onnxruntime wheel 打包（PP-OCRv4 det/rec/cls），首次运行无需联网下载。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

def _configure_utf8(stream) -> None:
    """强制 UTF-8 输出，避免 Windows GBK 控制台在子进程管道中产生乱码/编码错误。"""
    reconfigure = getattr(stream, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8")


_configure_utf8(sys.stdout)
_configure_utf8(sys.stderr)


def _bbox_from_points(points: list[list[float]]) -> list[int]:
    """rapidocr 返回 4 点框 [[x1,y1],[x2,y2],[x3,y3],[x4,y4]] → [x1,y1,x2,y2] 整数框。"""
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
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
        sys.stderr.write(f"图片不存在: {image}\n")
        return 2

    try:
        blocks = recognize_image(image)
    except Exception as exc:  # CLI 边界，任何异常转为失败退出
        sys.stderr.write(f"OCR 识别失败: {exc}\n")
        return 1

    for block in blocks:
        sys.stdout.write(json.dumps(block, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
