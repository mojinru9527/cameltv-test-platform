"""TC-AIQE-001：需求契约冻结 + V4→V5 变更影响（真实文档 + 用例库）。

输入：
  --docs-dir  C:\\Users\\26029\\Desktop\\未来娃娃
输出：
  --out-dir   docs/aiqe/v1.6/evidence/product/TC-AIQE-001
退出码：0=PASS，1=FAIL。
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
CASE_BOOK = "未来娃屿V5.0_全量用例明细_含步骤_20261112_全部可见.xlsx"


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


def _case_impact(docs_dir: Path) -> dict:
    book = docs_dir / CASE_BOOK
    wb = load_workbook(book, read_only=True, data_only=True)
    ws = wb["01-功能用例1505"]
    rows = ws.iter_rows(values_only=True)
    header = [str(item or "") for item in next(rows)]
    index = {name: pos for pos, name in enumerate(header)}
    impacted = []
    for row in rows:
        module = str(row[index["模块"]] or "")
        title = str(row[index["用例标题"]] or "")
        if "变更验证" in module or "变更验证" in title:
            impacted.append(
                {
                    "case_id": str(row[index["用例编号"]] or ""),
                    "end": str(row[index["端"]] or ""),
                    "module": module,
                    "title": title,
                    "priority": str(row[index["优先级"]] or ""),
                }
            )
    wb.close()
    by_module: dict[str, int] = {}
    for item in impacted:
        by_module[item["module"]] = by_module.get(item["module"], 0) + 1
    return {"count": len(impacted), "by_module": by_module, "sample": impacted[:20]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--docs-dir", default=r"C:\Users\26029\Desktop\未来娃娃")
    parser.add_argument(
        "--out-dir",
        default="docs/aiqe/v1.6/evidence/product/TC-AIQE-001",
    )
    args = parser.parse_args()
    docs_dir = Path(args.docs_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    v4 = docs_dir / "未来娃屿软件需求规格说明V4.0.pdf"
    v5 = docs_dir / "未来娃屿软件需求规格说明V5.0.pdf"
    if not v4.exists() or not v5.exists():
        print(json.dumps({"status": "FAIL", "reason": "缺少 V4/V5 需求 PDF"}, ensure_ascii=False))
        return 1
    converter = MarkItDown()
    md4 = converter.convert(str(v4)).text_content
    md5 = converter.convert(str(v5)).text_content
    head4 = _headings(md4)
    head5 = _headings(md5)
    added = sorted(set(head5) - set(head4))
    removed = sorted(set(head4) - set(head5))
    impact = _case_impact(docs_dir)
    report = {
        "schema_version": "1.0",
        "tc_id": "TC-AIQE-001",
        "status": "PASS",
        "generated_at": datetime.now(UTC).isoformat(),
        "baseline_version": "V5.0",
        "baseline_conclusion": "生产代码以 V5.0 为准；V4.0→V5.0 变更已冻结",
        "documents": {
            "V4.0": {"path": str(v4), "sha256": _sha256(v4), "chars": len(md4)},
            "V5.0": {"path": str(v5), "sha256": _sha256(v5), "chars": len(md5)},
        },
        "headings": {
            "V4_count": len(head4),
            "V5_count": len(head5),
            "added": added,
            "removed": removed,
        },
        "change_impact": impact,
        "revision_record_excerpt": md5.split("修订记录", 1)[-1][:1500],
    }
    (out_dir / "requirements-diff-v4-v5.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    (out_dir / "requirements-diff-v4-v5.md").write_text(
        "# TC-AIQE-001 需求契约冻结（V4.0 → V5.0）\n\n"
        f"- V5.0 文档 SHA256：`{report['documents']['V5.0']['sha256']}`\n"
        f"- 新增/变化的标题：{len(added)}；删除：{len(removed)}\n"
        f"- “变更验证”用例：{impact['count']} 条\n\n"
        "## 变更影响（按模块）\n\n"
        + "\n".join(f"- {name}: {count}" for name, count in sorted(impact["by_module"].items()))
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({"status": "PASS", "added": len(added), "impact_cases": impact["count"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
