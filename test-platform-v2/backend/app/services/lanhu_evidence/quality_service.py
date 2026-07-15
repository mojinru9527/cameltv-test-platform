"""证据包质量评估 —— 纯函数，无副作用。

`success`（import_ready）的释义（§0 不可协商契约）：
  每个被发现的页面都必须满足：
    - 截图成功且至少 1 段（capture_status == "success" and segment_count >= 1）
    - 未因 max_segments 截断（capture_truncated == False）
    - 合并文本非空（merged_text.strip()）
    - OCR 成功，或存在显式人工审核批准（ocr_status == "success" or review_status == "approved"）
任一页不满足即 complete=False、import_ready=False，禁止导入需求/RAG/Wiki。
"""
from __future__ import annotations


def evaluate_job_quality(pages: list[dict]) -> dict:
    """根据页面事实字典列表计算可审计的质量报告。

    每个 page 字典需含：capture_status, segment_count, capture_truncated,
    merged_text, ocr_status, review_status。缺失键按最保守（不合格）处理。
    """
    missing_capture: list[int] = []
    truncated: list[int] = []
    missing_text: list[int] = []
    missing_ocr_review: list[int] = []
    for index, page in enumerate(pages):
        try:
            seg = int(page.get("segment_count") or 0)
        except (TypeError, ValueError):
            seg = 0
        if page.get("capture_status") != "success" or seg < 1:
            missing_capture.append(index)
        if page.get("capture_truncated"):
            truncated.append(index)
        if not str(page.get("merged_text") or "").strip():
            missing_text.append(index)
        if page.get("ocr_status") != "success" and page.get("review_status") != "approved":
            missing_ocr_review.append(index)
    complete = bool(pages) and not (
        missing_capture or truncated or missing_text or missing_ocr_review
    )
    return {
        "page_count": len(pages),
        "complete": complete,
        "import_ready": complete,
        "pages_missing_capture": missing_capture,
        "pages_truncated": truncated,
        "pages_missing_text": missing_text,
        "pages_missing_ocr_review": missing_ocr_review,
    }
