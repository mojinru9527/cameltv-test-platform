"""ELK / Kibana integration utilities."""
from __future__ import annotations

import re
from urllib.parse import quote

from app.core.config import settings


def build_kibana_link(trace_id: str, time_range_h: int = 24) -> str:
    """Generate Kibana Discover deep link for a trace_id."""
    base = (settings.elk_base_url or "").rstrip("/")
    if not base or not trace_id:
        return ""
    index = settings.elk_index or "*"
    time_from = f"now-{time_range_h}h"
    query = f'traceId:"{trace_id}"'
    return (
        f"{base}#/discover"
        f"?_g=(time:(from:'{time_from}',to:now))"
        f"&_a=(index:'{index}',query:(language:kuery,query:'{quote(query)}'))"
    )


def extract_trace_id(text: str) -> str | None:
    """Extract traceId from text (execution notes / actual_result)."""
    if not text:
        return None
    m = re.search(r'trace[_-]?id[=:\s"]+([a-zA-Z0-9\-]+)', text, re.IGNORECASE)
    return m.group(1) if m else None
