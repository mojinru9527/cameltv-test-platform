"""录制流量的统一读写格式（JSONL，每行一个请求/响应对）。

被 traffic_monitor（写）、api_diff（回放）、mock_server（转 stub）共用。

单条结构:
{
  "request":  {"method","url","path","query":{},"headers":{},"body":<json或字符串>},
  "response": {"status","headers":{},"body":<json或字符串>}
}
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def append_entry(path: str | Path, entry: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_entries(path: str | Path) -> list[dict[str, Any]]:
    """支持 JSONL（每行一对象）与 JSON 数组两种格式。"""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"录制/用例文件不存在: {p}")
    text = p.read_text(encoding="utf-8").strip()
    if not text:
        return []
    # JSON 数组
    if text[0] == "[":
        return json.loads(text)
    # JSONL
    return [json.loads(line) for line in text.splitlines() if line.strip()]
