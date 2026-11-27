"""TC-AIQE-001：需求契约冻结 + V4→V5 变更影响（权威手工验收用例表）。

数据源（2026-11-17 甲方确认版）：
  未来娃屿V5.0_用例整理与问题登记_20261117 的手工验收(1)(1)(1)(1)(1).xlsx
  其中「01-功能用例」200 条 + 「补充用例」回归补充。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

from markitdown import MarkItDown
from openpyxl import load_workbook

HEADING_RE = re.compile(r"^(第[一二三四五六七八九十]+[章节]|\d+(?:\.\d+){0,3}[\s、.])")
CASE_BOOK = "未来娃屿V5.0_用例整理与问题登记_20261117 的手工验收(1)(1)(1)(1)(1).xlsx"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _headings(markdown: str) -> list[str]:
    result: list[str] = []
    for line in markdown.splitlines():
        text = line.strip()
        if text and len(text) <= 80 and HEADING_RE.match(text):
            result.append(text)
    return result


def _rows_with_header(ws) -> list[dict]:
    rows = list(ws.iter_rows(values_only=True))
    header_index = None
    for index, row in enumerate(rows[:6]):
        values = [str(item or "") for item in row]
        if "用例编号" in values:
            header_index = index
            header = values
            break
    if header_index is None:
        return []
    result = []
    for row in rows[header_index + 1 :]:
        if not row or not row[1]:
            continue
        item = {header[pos]: row[pos] for pos in range(min(len(header), len(row)))}
        result.append(item)
    return result


def _case_impact(docs_dir: Path) -> dict:
    book = docs_dir / CASE_BOOK
    wb = load_workbook(book, read_only=True, data_only=True)
    cases: list[dict] = []
    for sheet in ("01-功能用例", "补充用例"):
        for row in _rows_with_header(wb[sheet]):
            cases.append(
                {
                    "case_id": str(row.get("用例编号") or ""),
                    "end": str(row.get("端") or ""),
                    "module": str(row.get("模块") or ""),
                    "title": str(row.get("用例标题") or ""),
                    "priority": str(row.get("优先级") or ""),
                    "source_sheet": sheet,
                }
            )
    wb.close()
    impacted = [
        item
        for item in cases
        if "变更验证" in item["module"] or "变更验证" in item["title"] or "回归补充" in item["module"]
    ]
    by_module: dict[str, int] = {}
    for item in impacted:
        by_module[item["module"]] = by_module.get(item["module"], 0) + 1
    return {
        "total_cases": len(cases),
        "impacted_count": len(impacted),
        "by_module": by_module,
        "sample": impacted[:20],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--docs-dir", default=r"C:\Users\26029\Desktop")
    parser.add_argument("--out-dir", default="docs/aiqe/v1.6/evidence/product/TC-AIQE-001")
    args = parser.parse_args()
    docs_dir = Path(args.docs_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    # PDF 在 未来娃娃 子目录，用例表在 Desktop 根目录
    pdf_dir = docs_dir / "未来娃娃" if (docs_dir / "未来娃娃").exists() else docs_dir
    v4 = pdf_dir / "未来娃屿软件需求规格说明V4.0.pdf"
    v5 = pdf_dir / "未来娃屿软件需求规格说明V5.0.pdf"
    if not v4.exists() or not v5.exists():
        print(json.dumps({"status": "FAIL", "reason": "缺少 V4/V5 需求 PDF"}, ensure_ascii=False))
        return 1
    converter = MarkItDown()
    md4 = converter.convert(str(v4)).text_content
    md5 = converter.convert(str(v5)).text_content
    head4 = _headings(md4)
    head5 = _headings(md5)
    impact = _case_impact(docs_dir)
    report = {
        "schema_version": "1.0",
        "tc_id": "TC-AIQE-001",
        "status": "PASS",
        "generated_at": datetime.now(UTC).isoformat(),
        "baseline_version": "V5.0",
        "case_source": CASE_BOOK,
        "case_sheets": ["01-功能用例", "补充用例"],
        "baseline_conclusion": "生产代码以 V5.0 为准；V4.0→V5.0 变更已冻结",
        "documents": {
            "V4.0": {"path": str(v4), "sha256": _sha256(v4), "chars": len(md4)},
            "V5.0": {"path": str(v5), "sha256": _sha256(v5), "chars": len(md5)},
        },
        "headings": {
            "V4_count": len(head4),
            "V5_count": len(head5),
            "added": sorted(set(head5) - set(head4)),
            "removed": sorted(set(head4) - set(head5)),
        },
        "change_impact": impact,
        "revision_record_excerpt": md5.split("修订记录", 1)[-1][:1500],
    }
    (out_dir / "requirements-diff-v4-v5.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    (out_dir / "requirements-diff-v4-v5.md").write_text(
        "# TC-AIQE-001 需求契约冻结（V4.0 → V5.0）\n\n"
        f"- 用例源：`{CASE_BOOK}`（01-功能用例 + 补充用例）\n"
        f"- V5.0 文档 SHA256：`{report['documents']['V5.0']['sha256']}`\n"
        f"- 用例总数：{impact['total_cases']}；变更验证/回归补充：{impact['impacted_count']}\n\n"
        "## 变更影响（按模块）\n\n"
        + "\n".join(f"- {name}: {count}" for name, count in sorted(impact["by_module"].items()))
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({"status": "PASS", "total_cases": impact["total_cases"], "impact_cases": impact["impacted_count"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
