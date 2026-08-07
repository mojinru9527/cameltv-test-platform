"""生产页面 vs 需求原型差异标注（Batch 118, C102-4）。

对比需求模块树（RequirementModule）与生产页面清单，输出三类差异：
- new：生产已上线但需求原型未收录（如 World Cup / Replays 等新模块）
- matched：两边一致
- missing：需求原型有但本次生产清单未见（可能未上线/已下线/采集未覆盖）
"""
from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.requirement_module import RequirementModule


def _normalize(text: str) -> str:
    """Lowercase + keep CJK/alnum + strip common filler words."""
    s = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", "", (text or "").lower())
    for token in ("home", "page", "页", "列表", "详情", "管理"):
        s = s.replace(token, "")
    return s


def _token_overlap(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    a_tokens = set(_normalize(a)) - {"", " "}
    b_tokens = set(_normalize(b)) - {"", " "}
    if not a_tokens or not b_tokens:
        return 0.0
    return len(a_tokens & b_tokens) / max(len(a_tokens), len(b_tokens))


def _match(prod_label: str, requirement_names: list[str]) -> str | None:
    """Return the best-matching requirement name or None."""
    best: str | None = None
    best_score = 0.0
    pn = _normalize(prod_label)
    for name in requirement_names:
        nn = _normalize(name)
        if not nn:
            continue
        if pn == nn or pn in nn or nn in pn:
            return name
        score = _token_overlap(prod_label, name)
        if score > best_score:
            best_score = score
            best = name
    return best if best_score >= 0.5 else None


def compute_production_diff(
    db: Session,
    *,
    release_bundle_id: int,
    project_id: int,
    production_pages: list[dict],
) -> dict:
    """Compute annotated diff between requirement module tree and production pages."""
    warnings: list[str] = []
    req_rows = list(
        db.scalars(
            select(RequirementModule).where(
                RequirementModule.project_id == project_id,
                RequirementModule.release_bundle_id == release_bundle_id,
                RequirementModule.node_type.in_(("module", "page")),
            )
        ).all()
    )
    req_names = [r.name for r in req_rows if r.name]
    if not req_rows:
        warnings.append("发布包暂无模块树，请先执行模块树直建或证据包提取")

    items: list[dict] = []
    matched_requirement: set[str] = set()

    for prod in production_pages or []:
        if not isinstance(prod, dict):
            continue
        label = str(prod.get("label") or prod.get("title") or prod.get("url") or "").strip()
        if not label:
            continue
        match = _match(label, req_names) if req_names else None
        if match:
            matched_requirement.add(match)
            items.append({
                "name": label,
                "change_type": "matched",
                "matched_with": match,
                "source": "production",
            })
        else:
            items.append({
                "name": label,
                "change_type": "new",
                "matched_with": "",
                "source": "production",
            })

    # Requirement-side missing items (not matched by any production page)
    for name in req_names:
        if name not in matched_requirement:
            items.append({
                "name": name,
                "change_type": "missing",
                "matched_with": "",
                "source": "requirement",
            })

    new_count = sum(1 for i in items if i["change_type"] == "new")
    matched_count = sum(1 for i in items if i["change_type"] == "matched")
    missing_count = sum(1 for i in items if i["change_type"] == "missing")

    return {
        "summary": {
            "production_total": len(production_pages or []),
            "requirement_total": len(req_names),
            "new_count": new_count,
            "matched_count": matched_count,
            "missing_count": missing_count,
        },
        "items": items,
        "warnings": warnings,
    }
