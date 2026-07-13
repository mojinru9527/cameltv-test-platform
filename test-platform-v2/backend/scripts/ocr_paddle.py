#!/usr/bin/env python
"""PaddleOCR 封装脚本 —— 供蓝湖证据包 local OCR provider 调用。

用法（由 LANHU_OCR_COMMAND 触发，{image} 会被替换为截图路径）：
    LANHU_OCR_PROVIDER=local
    LANHU_OCR_COMMAND=python F:/CamelTv/test-platform-v2/backend/scripts/ocr_paddle.py {image}

契约（见 app/services/lanhu_evidence/local_ocr_provider.py::parse_command_output）：
    stdout **逐行**输出一个 JSON 对象，每个文本块一行：
        {"text": "比赛推送", "confidence": 0.96, "bbox": [x1, y1, x2, y2]}
    - 非 JSON 行会被解析器忽略，因此 PaddleOCR 自身日志/进度即使落到 stdout 也无害；
      但本脚本仍把日志强制导向 stderr，保持 stdout 干净。
    - bbox 为轴对齐外接矩形 [x1, y1, x2, y2]（整数像素）。
    - confidence 为 0~1 浮点；低于 LANHU_OCR_MIN_CONFIDENCE 的块由 provider 侧过滤。

依赖：
    pip install paddleocr paddlepaddle
    （首次运行会自动下载中英文识别/检测模型，需联网，约数百 MB。）

兼容 PaddleOCR 2.x（ocr.ocr）与 3.x（ocr.predict）两套返回结构。
退出码 0 表示成功（即使 0 个文本块）；非 0 表示 OCR 失败，provider 会记为 failed。
"""
from __future__ import annotations

import json
import sys
from typing import Any


def _bbox_from_quad(quad: Any) -> list[int]:
    """把四点多边形 [[x,y],[x,y],[x,y],[x,y]] 或扁平坐标压成轴对齐矩形 [x1,y1,x2,y2]。"""
    try:
        pts = list(quad)
        # 扁平形式 [x1,y1,x2,y2,...] → 两两成点
        if pts and not isinstance(pts[0], (list, tuple)):
            pts = [(pts[i], pts[i + 1]) for i in range(0, len(pts) - 1, 2)]
        xs = [float(p[0]) for p in pts]
        ys = [float(p[1]) for p in pts]
        return [int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))]
    except Exception:
        return [0, 0, 0, 0]


def _emit(text: str, conf: float, quad: Any) -> None:
    text = (text or "").strip()
    if not text:
        return
    line = json.dumps(
        {"text": text, "confidence": round(float(conf), 4), "bbox": _bbox_from_quad(quad)},
        ensure_ascii=False,
    )
    sys.stdout.write(line + "\n")


def _run_v3(ocr: Any, image_path: str) -> bool:
    """PaddleOCR 3.x：ocr.predict(...) 返回 [dict(...)]，含 rec_texts/rec_scores/rec_polys。"""
    predict = getattr(ocr, "predict", None)
    if predict is None:
        return False
    results = predict(image_path)
    emitted = False
    for res in results or []:
        data = getattr(res, "json", None)
        if isinstance(data, dict) and "res" in data:
            data = data["res"]
        if not isinstance(data, dict):
            # 某些版本 res 直接就是可下标 dict-like
            try:
                data = dict(res)
            except Exception:
                continue
        texts = data.get("rec_texts") or []
        scores = data.get("rec_scores") or []
        polys = data.get("rec_polys") or data.get("dt_polys") or []
        for i, text in enumerate(texts):
            conf = scores[i] if i < len(scores) else 0.0
            quad = polys[i] if i < len(polys) else [0, 0, 0, 0]
            _emit(text, conf, quad)
            emitted = True
    return emitted or bool(results)


def _run_v2(ocr: Any, image_path: str) -> None:
    """PaddleOCR 2.x：ocr.ocr(img, cls=True) 返回 [[ [box, (text, score)], ... ]]。"""
    try:
        results = ocr.ocr(image_path, cls=True)
    except TypeError:
        results = ocr.ocr(image_path)
    for page in results or []:
        for line in page or []:
            try:
                box, (text, score) = line[0], line[1]
            except Exception:
                continue
            _emit(text, score, box)


def main() -> int:
    if len(sys.argv) < 2:
        sys.stderr.write("usage: ocr_paddle.py <image_path>\n")
        return 2
    image_path = sys.argv[1]

    try:
        from paddleocr import PaddleOCR
    except Exception as e:  # noqa: BLE001
        sys.stderr.write(f"paddleocr import failed: {e}\n(pip install paddleocr paddlepaddle)\n")
        return 3

    # 构造 OCR（尽量静默日志到 stderr；不同版本参数不同，逐步降级）。
    ocr = None
    for kwargs in (
        {"use_angle_cls": True, "lang": "ch", "show_log": False},
        {"use_angle_cls": True, "lang": "ch"},
        {"lang": "ch"},
        {},
    ):
        try:
            ocr = PaddleOCR(**kwargs)
            break
        except Exception:  # noqa: BLE001
            continue
    if ocr is None:
        sys.stderr.write("PaddleOCR 初始化失败\n")
        return 4

    try:
        if not _run_v3(ocr, image_path):
            _run_v2(ocr, image_path)
    except Exception as e:  # noqa: BLE001
        sys.stderr.write(f"OCR 执行异常: {e}\n")
        return 5

    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
