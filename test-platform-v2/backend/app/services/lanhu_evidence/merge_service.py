"""OCR + DOM/MCP 文本合并 —— 确定性、不丢原始证据。

合并策略：以页面标题为骨架，OCR 文本优先展示，DOM/MCP 文本在其不冗余时附加。
不使用 LLM（LLM 摘要发生在后续导入步骤且永不覆盖证据）。质量字段用于完整性校验：
merged 过短（<30 字）标记 needs_review。
"""
from __future__ import annotations

import re
from dataclasses import dataclass


def normalize_text(text: str) -> str:
    """去除多余空白与空行，保持可读的多行结构。"""
    if not text:
        return ""
    lines = [ln.strip() for ln in text.replace("\r\n", "\n").split("\n")]
    lines = [ln for ln in lines if ln]
    # 折叠行内多空格
    lines = [re.sub(r"[ \t]{2,}", " ", ln) for ln in lines]
    return "\n".join(lines).strip()


@dataclass
class MergeResult:
    merged_text: str
    quality: dict


def merge_page_text(page_name: str, dom_text: str, ocr_text: str) -> MergeResult:
    dom = normalize_text(dom_text)
    ocr = normalize_text(ocr_text)
    parts = [f"# {page_name}"]
    if ocr:
        parts.extend(["", "## OCR识别文本", ocr])
    if dom and dom not in ocr:
        parts.extend(["", "## DOM/MCP文本", dom])
    merged = "\n".join(parts).strip()
    status = "success" if len(merged) >= 30 else "needs_review"
    return MergeResult(
        merged_text=merged,
        quality={
            "status": status,
            "ocr_chars": len(ocr),
            "dom_chars": len(dom),
            "merged_chars": len(merged),
            "has_ocr": bool(ocr),
            "has_dom": bool(dom),
        },
    )
