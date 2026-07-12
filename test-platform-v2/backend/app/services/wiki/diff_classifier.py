"""差异分类器 —— 对两份「需求契约」逐维度比对，输出结构化差异项（确定性，无 LLM）。

维度对齐落地方案 §6.6：需求范围/客户端/业务规则/字段/接口/异常路径/权限角色/
数据依赖/验收标准/测试覆盖。差异类型：missing_in_left/missing_in_right/conflict/
changed/ambiguous/coverage_gap/stale。级别 P0..P3。
"""
from __future__ import annotations


def _norm(s) -> str:
    return str(s or "").strip().lower()


def _rule_text(r) -> str:
    return r.get("rule", "") if isinstance(r, dict) else str(r)


def _field_key(f) -> str:
    return _norm(f.get("name")) if isinstance(f, dict) else _norm(f)


def _api_key(a) -> str:
    if isinstance(a, dict):
        return f"{_norm(a.get('method'))} {_norm(a.get('path'))}"
    return _norm(a)


def _item(dimension, diff_type, severity, title, left="", right="", evidence=None, suggestion=""):
    return {
        "dimension": dimension, "diff_type": diff_type, "severity": severity,
        "title": title, "left_value": str(left), "right_value": str(right),
        "evidence": evidence or [], "suggestion": suggestion,
    }


def classify(left: dict, right: dict) -> list[dict]:
    """比对两份契约，返回差异项列表。left/right 为需求契约 dict。"""
    items: list[dict] = []
    left = left or {}
    right = right or {}

    # 需求范围（标题）
    lt, rt = _norm(left.get("title")), _norm(right.get("title"))
    if lt and rt and lt != rt:
        items.append(_item("需求范围", "changed", "P2", "两侧需求标题不一致",
                           left.get("title"), right.get("title"),
                           suggestion="确认是否为同一需求，或对齐命名"))

    # 客户端范围
    ls, rs = set(map(_norm, left.get("client_scope") or [])), set(map(_norm, right.get("client_scope") or []))
    for miss in sorted(rs - ls):
        items.append(_item("客户端", "missing_in_left", "P2", f"左侧缺少客户端范围「{miss}」",
                           "", miss, suggestion=f"补充 {miss} 端的需求与测试覆盖"))
    for miss in sorted(ls - rs):
        items.append(_item("客户端", "missing_in_right", "P2", f"右侧缺少客户端范围「{miss}」",
                           miss, "", suggestion=f"补充 {miss} 端的需求与测试覆盖"))

    # 业务规则
    lr = {_norm(_rule_text(r)): _rule_text(r) for r in (left.get("business_rules") or [])}
    rr = {_norm(_rule_text(r)): _rule_text(r) for r in (right.get("business_rules") or [])}
    for k in rr.keys() - lr.keys():
        items.append(_item("业务规则", "missing_in_left", "P1", f"左侧缺少业务规则：{rr[k]}",
                           "", rr[k], suggestion="确认该规则是否遗漏，或补充对应用例"))
    for k in lr.keys() - rr.keys():
        items.append(_item("业务规则", "missing_in_right", "P1", f"右侧缺少业务规则：{lr[k]}",
                           lr[k], "", suggestion="确认该规则是否遗漏，或补充对应用例"))

    # 字段
    lf = {_field_key(f): f for f in (left.get("fields") or []) if _field_key(f)}
    rf = {_field_key(f): f for f in (right.get("fields") or []) if _field_key(f)}
    for k in rf.keys() - lf.keys():
        items.append(_item("字段", "missing_in_left", "P1", f"左侧缺少字段「{k}」", "", str(rf[k]),
                           suggestion="补充字段定义与边界用例"))
    for k in lf.keys() - rf.keys():
        items.append(_item("字段", "missing_in_right", "P1", f"右侧缺少字段「{k}」", str(lf[k]), "",
                           suggestion="补充字段定义与边界用例"))
    for k in lf.keys() & rf.keys():
        a, b = lf[k], rf[k]
        if isinstance(a, dict) and isinstance(b, dict):
            if _norm(a.get("type")) != _norm(b.get("type")) or bool(a.get("required")) != bool(b.get("required")):
                items.append(_item("字段", "conflict", "P1", f"字段「{k}」类型/必填不一致",
                                   f"type={a.get('type')},required={a.get('required')}",
                                   f"type={b.get('type')},required={b.get('required')}",
                                   suggestion="对齐字段类型与必填约束，补充边界/类型用例"))

    # 接口
    la = {_api_key(a): a for a in (left.get("apis") or []) if _api_key(a).strip()}
    ra = {_api_key(a): a for a in (right.get("apis") or []) if _api_key(a).strip()}
    for k in ra.keys() - la.keys():
        items.append(_item("接口", "missing_in_left", "P0", f"左侧缺少关联接口「{k}」", "", k,
                           suggestion="绑定接口资产并补充接口用例"))
    for k in la.keys() - ra.keys():
        items.append(_item("接口", "missing_in_right", "P0", f"右侧缺少关联接口「{k}」", k, "",
                           suggestion="绑定接口资产并补充接口用例"))

    # 异常路径
    le = {_norm(x) for x in (left.get("exception_paths") or [])}
    re_ = {_norm(x) for x in (right.get("exception_paths") or [])}
    for miss in sorted(re_ - le):
        items.append(_item("异常路径", "missing_in_left", "P1", f"左侧缺少异常路径「{miss}」", "", miss,
                           suggestion="补充负向/异常场景用例"))
    for miss in sorted(le - re_):
        items.append(_item("异常路径", "missing_in_right", "P1", f"右侧缺少异常路径「{miss}」", miss, "",
                           suggestion="补充负向/异常场景用例"))

    # 验收标准
    lac = {_norm(x) for x in (left.get("acceptance_criteria") or [])}
    rac = {_norm(x) for x in (right.get("acceptance_criteria") or [])}
    if lac != rac and (lac or rac):
        items.append(_item("验收标准", "ambiguous", "P2", "两侧验收标准不一致或缺失",
                           "; ".join(left.get("acceptance_criteria") or []),
                           "; ".join(right.get("acceptance_criteria") or []),
                           suggestion="对齐 Done 定义，生成需求评审问题单"))

    # 测试覆盖缺口：一侧有规则/接口但无测试用例
    for side, label, dtype in ((left, "左", "missing_in_left"), (right, "右", "missing_in_right")):
        has_subject = bool(side.get("business_rules") or side.get("apis") or side.get("fields"))
        if has_subject and not (side.get("test_cases") or []):
            items.append(_item("测试覆盖", "coverage_gap", "P1", f"{label}侧有需求但缺少测试用例",
                               suggestion="从规则/字段/接口生成待审测试用例"))

    return items


def summarize(items: list[dict]) -> dict:
    """按 diff_type / severity / dimension 计数。"""
    def _count(key):
        out: dict[str, int] = {}
        for it in items:
            out[it[key]] = out.get(it[key], 0) + 1
        return out
    return {
        "total": len(items),
        "by_type": _count("diff_type"),
        "by_severity": _count("severity"),
        "by_dimension": _count("dimension"),
    }
