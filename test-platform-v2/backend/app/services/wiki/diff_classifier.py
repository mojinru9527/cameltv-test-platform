"""差异分类器 —— 对两份「需求契约」逐维度比对，输出结构化差异项（确定性，无 LLM）。

维度对齐落地方案 §6.6（12 维）：
  需求范围 / 客户端 / 业务规则 / 字段 / 接口 / 异常路径 / 权限角色 /
  数据依赖 / 验收标准 / 测试覆盖 / 版本 / 证据

差异类型：missing_in_left / missing_in_right / conflict / changed / ambiguous / coverage_gap / stale
严重级别：critical（P0=阻断）/ high（P1=高）/ medium（P2=中）/ low（P3=低）

每条差异项必须附带 evidence 列表，引用来源（wiki_page / knowledge_chunk / knowledge_source 等）。
"""
from __future__ import annotations

from typing import Any


# ═══════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════

def _norm(s: Any) -> str:
    return str(s or "").strip().lower()


def _rule_text(r: Any) -> str:
    return r.get("rule", "") if isinstance(r, dict) else str(r)


def _field_key(f: Any) -> str:
    return _norm(f.get("name")) if isinstance(f, dict) else _norm(f)


def _api_key(a: Any) -> str:
    if isinstance(a, dict):
        return f"{_norm(a.get('method'))} {_norm(a.get('path'))}"
    return _norm(a)


def _ensure_list(val: Any) -> list:
    if val is None:
        return []
    if isinstance(val, list):
        return val
    return [val]


def _safe_str(val: Any, max_len: int = 500) -> str:
    s = str(val) if val is not None else ""
    return s[:max_len]


def _derived_evidence(left_ev: list, right_ev: list, diff_type: str) -> list:
    """根据差异方向选择相关证据来源。

    - missing_in_left → 右侧有该内容，用右侧证据证明其存在
    - missing_in_right → 左侧有该内容，用左侧证据证明其存在
    - conflict / changed / ambiguous → 两侧证据都相关
    - coverage_gap → 两侧证据都相关（需补充）
    """
    left_ev = _ensure_list(left_ev)
    right_ev = _ensure_list(right_ev)
    if diff_type == "missing_in_left":
        return right_ev if right_ev else left_ev
    if diff_type == "missing_in_right":
        return left_ev if left_ev else right_ev
    # conflict / changed / ambiguous / coverage_gap / stale
    combined = list(left_ev)
    for r in right_ev:
        if r not in combined:
            combined.append(r)
    return combined


# ═══════════════════════════════════════════════════════
# 差异项工厂
# ═══════════════════════════════════════════════════════

def _item(
    dimension: str,
    diff_type: str,
    severity: str,
    title: str,
    left: Any = "",
    right: Any = "",
    evidence: list | None = None,
    suggestion: str = "",
) -> dict:
    return {
        "dimension": dimension,
        "diff_type": diff_type,
        "severity": severity,
        "title": title,
        "left_value": _safe_str(left),
        "right_value": _safe_str(right),
        "evidence": evidence or [],
        "suggestion": suggestion,
    }


# ═══════════════════════════════════════════════════════
# 逐维度比对
# ═══════════════════════════════════════════════════════

def _compare_requirement_scope(left: dict, right: dict, lev: list, rev: list) -> list[dict]:
    """需求范围 —— 标题、模块、需求 Key。"""
    items: list[dict] = []
    lt, rt = _norm(left.get("title")), _norm(right.get("title"))
    if lt and rt and lt != rt:
        items.append(_item("需求范围", "changed", "P2",
                           "两侧需求标题不一致",
                           left.get("title"), right.get("title"),
                           evidence=_derived_evidence(lev, rev, "changed"),
                           suggestion="确认是否为同一需求，或对齐命名"))
    lm, rm = _norm(left.get("module")), _norm(right.get("module"))
    if lm and rm and lm != rm:
        items.append(_item("需求范围", "conflict", "P2",
                           "两侧归属模块不一致",
                           left.get("module"), right.get("module"),
                           evidence=_derived_evidence(lev, rev, "conflict"),
                           suggestion="确认需求所属模块，统一模块划分"))
    return items


def _compare_client_scope(left: dict, right: dict, lev: list, rev: list) -> list[dict]:
    """客户端 —— 涉及哪些端（app / web / admin / h5 / miniprogram）。"""
    items: list[dict] = []
    ls = set(map(_norm, _ensure_list(left.get("client_scope"))))
    rs = set(map(_norm, _ensure_list(right.get("client_scope"))))
    for miss in sorted(rs - ls):
        items.append(_item("客户端", "missing_in_left", "P2",
                           f"左侧缺少客户端范围「{miss}」",
                           "", miss,
                           evidence=_derived_evidence(lev, rev, "missing_in_left"),
                           suggestion=f"补充 {miss} 端的需求与测试覆盖"))
    for miss in sorted(ls - rs):
        items.append(_item("客户端", "missing_in_right", "P2",
                           f"右侧缺少客户端范围「{miss}」",
                           miss, "",
                           evidence=_derived_evidence(lev, rev, "missing_in_right"),
                           suggestion=f"补充 {miss} 端的需求与测试覆盖"))
    return items


def _compare_business_rules(left: dict, right: dict, lev: list, rev: list) -> list[dict]:
    """业务规则 —— 先按 id 匹配（同名规则），再按文本去重补漏。

    策略：
    1. 按 rule.id 做 key → 同 id 不同文本 = conflict
    2. 剩余未匹配的按归一化 rule 文本去重 → 缺失/新增
    """
    items: list[dict] = []

    def _rule_id(r: Any) -> str:
        if isinstance(r, dict):
            return _norm(r.get("id") or "")
        return ""

    lr_raw = _ensure_list(left.get("business_rules"))
    rr_raw = _ensure_list(right.get("business_rules"))

    # -- 按 id 匹配 --
    lr_by_id: dict[str, dict] = {}
    rr_by_id: dict[str, dict] = {}
    for r in lr_raw:
        rid = _rule_id(r)
        if rid:
            lr_by_id[rid] = r
    for r in rr_raw:
        rid = _rule_id(r)
        if rid:
            rr_by_id[rid] = r

    # 同 id 冲突
    for rid in lr_by_id.keys() & rr_by_id.keys():
        lt = _rule_text(lr_by_id[rid])
        rt = _rule_text(rr_by_id[rid])
        if _norm(lt) != _norm(rt):
            items.append(_item("业务规则", "conflict", "P1",
                               f"业务规则「{rid}」内容不一致",
                               lt, rt,
                               evidence=_derived_evidence(lev, rev, "conflict"),
                               suggestion="对齐业务规则描述，统一理解"))

    # id 缺失
    for rid in rr_by_id.keys() - lr_by_id.keys():
        rt = _rule_text(rr_by_id[rid])
        items.append(_item("业务规则", "missing_in_left", "P1",
                           f"左侧缺少业务规则「{rid}」：{rt}",
                           "", rt,
                           evidence=_derived_evidence(lev, rev, "missing_in_left"),
                           suggestion="确认该规则是否遗漏，或补充对应用例"))
    for rid in lr_by_id.keys() - rr_by_id.keys():
        lt = _rule_text(lr_by_id[rid])
        items.append(_item("业务规则", "missing_in_right", "P1",
                           f"右侧缺少业务规则「{rid}」：{lt}",
                           lt, "",
                           evidence=_derived_evidence(lev, rev, "missing_in_right"),
                           suggestion="确认该规则是否遗漏，或补充对应用例"))

    # -- 按文本去重补充（无 id 的规则） --
    lr_no_id = [r for r in lr_raw if not _rule_id(r)]
    rr_no_id = [r for r in rr_raw if not _rule_id(r)]
    lr_text = {_norm(_rule_text(r)): _rule_text(r) for r in lr_no_id}
    rr_text = {_norm(_rule_text(r)): _rule_text(r) for r in rr_no_id}

    for k in rr_text.keys() - lr_text.keys():
        items.append(_item("业务规则", "missing_in_left", "P1",
                           f"左侧缺少业务规则：{rr_text[k]}",
                           "", rr_text[k],
                           evidence=_derived_evidence(lev, rev, "missing_in_left"),
                           suggestion="确认该规则是否遗漏，或补充对应用例"))
    for k in lr_text.keys() - rr_text.keys():
        items.append(_item("业务规则", "missing_in_right", "P1",
                           f"右侧缺少业务规则：{lr_text[k]}",
                           lr_text[k], "",
                           evidence=_derived_evidence(lev, rev, "missing_in_right"),
                           suggestion="确认该规则是否遗漏，或补充对应用例"))
    for k in lr_text.keys() & rr_text.keys():
        if lr_text[k] != rr_text[k]:
            items.append(_item("业务规则", "conflict", "P1",
                               f"业务规则「{k[:40]}」内容不一致",
                               lr_text[k], rr_text[k],
                               evidence=_derived_evidence(lev, rev, "conflict"),
                               suggestion="对齐业务规则描述，统一理解"))

    return items


def _compare_fields(left: dict, right: dict, lev: list, rev: list) -> list[dict]:
    """字段 —— 按 name 去重后对比缺失 / 类型必填冲突。"""
    items: list[dict] = []
    lf = {_field_key(f): f for f in _ensure_list(left.get("fields")) if _field_key(f)}
    rf = {_field_key(f): f for f in _ensure_list(right.get("fields")) if _field_key(f)}
    # 缺失
    for k in rf.keys() - lf.keys():
        items.append(_item("字段", "missing_in_left", "P1",
                           f"左侧缺少字段「{k}」",
                           "", str(rf[k]),
                           evidence=_derived_evidence(lev, rev, "missing_in_left"),
                           suggestion="补充字段定义与边界用例"))
    for k in lf.keys() - rf.keys():
        items.append(_item("字段", "missing_in_right", "P1",
                           f"右侧缺少字段「{k}」",
                           str(lf[k]), "",
                           evidence=_derived_evidence(lev, rev, "missing_in_right"),
                           suggestion="补充字段定义与边界用例"))
    # 冲突：type / required 不一致
    for k in lf.keys() & rf.keys():
        a, b = lf[k], rf[k]
        if isinstance(a, dict) and isinstance(b, dict):
            diffs: list[str] = []
            if _norm(a.get("type")) != _norm(b.get("type")):
                diffs.append(f"type: {a.get('type')} vs {b.get('type')}")
            if _norm(a.get("location")) != _norm(b.get("location")):
                diffs.append(f"location: {a.get('location')} vs {b.get('location')}")
            if bool(a.get("required")) != bool(b.get("required")):
                diffs.append(f"required: {a.get('required')} vs {b.get('required')}")
            if diffs:
                items.append(_item("字段", "conflict", "P1",
                                   f"字段「{k}」定义不一致",
                                   str(a), str(b),
                                   evidence=_derived_evidence(lev, rev, "conflict"),
                                   suggestion=f"对齐字段定义（{'，'.join(diffs)}），补充边界/类型用例"))
    return items


def _compare_apis(left: dict, right: dict, lev: list, rev: list) -> list[dict]:
    """接口 —— 按 method+path 去重后对比缺失和 method 冲突。"""
    items: list[dict] = []
    la = {_api_key(a): a for a in _ensure_list(left.get("apis")) if _api_key(a).strip()}
    ra = {_api_key(a): a for a in _ensure_list(right.get("apis")) if _api_key(a).strip()}
    for k in ra.keys() - la.keys():
        items.append(_item("接口", "missing_in_left", "P0",
                           f"左侧缺少关联接口「{k}」",
                           "", k,
                           evidence=_derived_evidence(lev, rev, "missing_in_left"),
                           suggestion="绑定接口资产并补充接口用例"))
    for k in la.keys() - ra.keys():
        items.append(_item("接口", "missing_in_right", "P0",
                           f"右侧缺少关联接口「{k}」",
                           k, "",
                           evidence=_derived_evidence(lev, rev, "missing_in_right"),
                           suggestion="绑定接口资产并补充接口用例"))
    # 同 path 但 method 不同的视为 ambiguous
    lpath = {_norm(a.get("path")): a for a in _ensure_list(left.get("apis")) if isinstance(a, dict)}
    rpath = {_norm(a.get("path")): a for a in _ensure_list(right.get("apis")) if isinstance(a, dict)}
    for path in lpath.keys() & rpath.keys():
        la_m, ra_m = _norm(lpath[path].get("method")), _norm(rpath[path].get("method"))
        if la_m and ra_m and la_m != ra_m:
            items.append(_item("接口", "ambiguous", "P1",
                               f"同一路径「{path}」HTTP 方法不一致",
                               f"{la_m.upper()} {path}", f"{ra_m.upper()} {path}",
                               evidence=_derived_evidence(lev, rev, "ambiguous"),
                               suggestion="确认正确 HTTP 方法，可能有 GET/POST 双接口"))
    return items


def _compare_exception_paths(left: dict, right: dict, lev: list, rev: list) -> list[dict]:
    """异常路径 —— 归一化后集合对比。"""
    items: list[dict] = []
    le = {_norm(x) for x in _ensure_list(left.get("exception_paths")) if x}
    re_ = {_norm(x) for x in _ensure_list(right.get("exception_paths")) if x}
    for miss in sorted(re_ - le):
        items.append(_item("异常路径", "missing_in_left", "P1",
                           f"左侧缺少异常路径「{miss}」",
                           "", miss,
                           evidence=_derived_evidence(lev, rev, "missing_in_left"),
                           suggestion="补充负向/异常场景用例"))
    for miss in sorted(le - re_):
        items.append(_item("异常路径", "missing_in_right", "P1",
                           f"右侧缺少异常路径「{miss}」",
                           miss, "",
                           evidence=_derived_evidence(lev, rev, "missing_in_right"),
                           suggestion="补充负向/异常场景用例"))
    return items


def _compare_permissions(left: dict, right: dict, lev: list, rev: list) -> list[dict]:
    """权限角色 —— 按角色名称归一化后对比。契约字段：permissions[{role, actions[]}]。"""
    items: list[dict] = []
    lp_raw = _ensure_list(left.get("permissions"))
    rp_raw = _ensure_list(right.get("permissions"))
    if not lp_raw and not rp_raw:
        return items  # 两侧均无权限信息，跳过

    def _perm_key(p: Any) -> str:
        if isinstance(p, dict):
            return _norm(p.get("role") or p.get("name") or "")
        return _norm(p)

    def _perm_text(p: Any) -> str:
        if isinstance(p, dict):
            role = p.get("role") or p.get("name") or ""
            actions = p.get("actions") or p.get("permissions") or []
            if isinstance(actions, list):
                return f"{role}: {', '.join(actions)}"
            return f"{role}: {actions}"
        return str(p)

    lp = {_perm_key(p): _perm_text(p) for p in lp_raw if _perm_key(p)}
    rp = {_perm_key(p): _perm_text(p) for p in rp_raw if _perm_key(p)}

    for k in rp.keys() - lp.keys():
        items.append(_item("权限角色", "missing_in_left", "P1",
                           f"左侧缺少权限角色「{k}」",
                           "", rp[k],
                           evidence=_derived_evidence(lev, rev, "missing_in_left"),
                           suggestion="确认角色是否存在，补充权限测试用例"))
    for k in lp.keys() - rp.keys():
        items.append(_item("权限角色", "missing_in_right", "P1",
                           f"右侧缺少权限角色「{k}」",
                           lp[k], "",
                           evidence=_derived_evidence(lev, rev, "missing_in_right"),
                           suggestion="确认角色是否存在，补充权限测试用例"))
    # 两侧都有但 action 不同的，视为冲突
    for k in lp.keys() & rp.keys():
        if _norm(lp[k]) != _norm(rp[k]):
            items.append(_item("权限角色", "conflict", "P1",
                               f"权限角色「{k}」配置不一致",
                               lp[k], rp[k],
                               evidence=_derived_evidence(lev, rev, "conflict"),
                               suggestion="对齐角色权限定义"))
    return items


def _compare_data_dependencies(left: dict, right: dict, lev: list, rev: list) -> list[dict]:
    """数据依赖 —— 系统间数据依赖关系。契约字段：data_dependencies[{name, source, type}]。"""
    items: list[dict] = []
    ld_raw = _ensure_list(left.get("data_dependencies"))
    rd_raw = _ensure_list(right.get("data_dependencies"))
    if not ld_raw and not rd_raw:
        return items

    def _dep_key(d: Any) -> str:
        if isinstance(d, dict):
            return _norm(d.get("name") or f"{d.get('source')}_{d.get('type')}")
        return _norm(d)

    def _dep_text(d: Any) -> str:
        if isinstance(d, dict):
            return f"{d.get('name', '')} (source={d.get('source', '')}, type={d.get('type', '')})"
        return str(d)

    ld = {_dep_key(d): _dep_text(d) for d in ld_raw if _dep_key(d)}
    rd = {_dep_key(d): _dep_text(d) for d in rd_raw if _dep_key(d)}

    for k in rd.keys() - ld.keys():
        items.append(_item("数据依赖", "missing_in_left", "P2",
                           f"左侧缺少数据依赖「{k}」",
                           "", rd[k],
                           evidence=_derived_evidence(lev, rev, "missing_in_left"),
                           suggestion="补充数据依赖说明与边界用例（数据不存在 / 格式异常）"))
    for k in ld.keys() - rd.keys():
        items.append(_item("数据依赖", "missing_in_right", "P2",
                           f"右侧缺少数据依赖「{k}」",
                           ld[k], "",
                           evidence=_derived_evidence(lev, rev, "missing_in_right"),
                           suggestion="补充数据依赖说明与边界用例"))
    for k in ld.keys() & rd.keys():
        if _norm(ld[k]) != _norm(rd[k]):
            items.append(_item("数据依赖", "conflict", "P2",
                               f"数据依赖「{k}」描述不一致",
                               ld[k], rd[k],
                               evidence=_derived_evidence(lev, rev, "conflict"),
                               suggestion="对齐数据依赖描述"))
    return items


def _compare_acceptance_criteria(left: dict, right: dict, lev: list, rev: list) -> list[dict]:
    """验收标准 —— 归一化后按集合对比，并对缺失单独列项。"""
    items: list[dict] = []
    lac = {_norm(x) for x in _ensure_list(left.get("acceptance_criteria")) if x}
    rac = {_norm(x) for x in _ensure_list(right.get("acceptance_criteria")) if x}
    if not lac and not rac:
        return items
    if lac != rac:
        lraw = _ensure_list(left.get("acceptance_criteria"))
        rraw = _ensure_list(right.get("acceptance_criteria"))
        items.append(_item("验收标准", "ambiguous", "P2",
                           "两侧验收标准不一致或缺失",
                           "; ".join(str(x) for x in lraw),
                           "; ".join(str(x) for x in rraw),
                           evidence=_derived_evidence(lev, rev, "ambiguous"),
                           suggestion="对齐 Done 定义，生成需求评审问题单"))
    # 逐条缺失（更细粒度）
    for miss in sorted(rac - lac):
        items.append(_item("验收标准", "missing_in_left", "P2",
                           f"左侧缺少验收标准「{miss}」",
                           "", miss,
                           evidence=_derived_evidence(lev, rev, "missing_in_left")))
    for miss in sorted(lac - rac):
        items.append(_item("验收标准", "missing_in_right", "P2",
                           f"右侧缺少验收标准「{miss}」",
                           miss, "",
                           evidence=_derived_evidence(lev, rev, "missing_in_right")))
    return items


def _compare_test_coverage(left: dict, right: dict, lev: list, rev: list) -> list[dict]:
    """测试覆盖 —— 一侧有规则/接口/字段但没有测试用例即标记覆盖缺口。"""
    items: list[dict] = []
    for side, label, dtype, ev in (
        (left, "左", "coverage_gap_left", lev),
        (right, "右", "coverage_gap_right", rev),
    ):
        has_subject = bool(
            _ensure_list(side.get("business_rules"))
            or _ensure_list(side.get("apis"))
            or _ensure_list(side.get("fields"))
            or _ensure_list(side.get("exception_paths"))
        )
        has_tests = bool(_ensure_list(side.get("test_cases")))
        if has_subject and not has_tests:
            items.append(_item("测试覆盖", "coverage_gap", "P1",
                               f"{label}侧有需求但缺少测试用例",
                               suggestion="从规则/字段/接口生成待审测试用例",
                               evidence=ev))
    # 两侧都有测试用例但数量/类型差异大
    lt = _ensure_list(left.get("test_cases"))
    rt = _ensure_list(right.get("test_cases"))
    if len(lt) > 0 and len(rt) > 0 and abs(len(lt) - len(rt)) >= max(len(lt), len(rt)) * 0.5:
        items.append(_item("测试覆盖", "ambiguous", "P2",
                           "两侧测试用例数量差异较大",
                           f"{len(lt)} 条", f"{len(rt)} 条",
                           evidence=_derived_evidence(lev, rev, "ambiguous"),
                           suggestion="确认是否一侧有漏测或过度覆盖"))
    return items


def _compare_version(left: dict, right: dict, lev: list, rev: list) -> list[dict]:
    """版本 —— 对比契约中的版本标识。契约字段：version。"""
    items: list[dict] = []
    lv, rv = _norm(left.get("version")), _norm(right.get("version"))
    if not lv and not rv:
        return items
    if lv and rv and lv != rv:
        items.append(_item("版本", "changed", "P2",
                           "两侧版本号不一致",
                           left.get("version"), right.get("version"),
                           evidence=_derived_evidence(lev, rev, "changed"),
                           suggestion="确认版本差异是否为预期升级，通知回归范围"))
    elif lv and not rv:
        items.append(_item("版本", "missing_in_right", "P3",
                           "右侧缺少版本标识",
                           left.get("version"), "",
                           suggestion="补充版本号"))
    elif rv and not lv:
        items.append(_item("版本", "missing_in_left", "P3",
                           "左侧缺少版本标识",
                           "", right.get("version"),
                           suggestion="补充版本号"))
    return items


def _compare_evidence_quality(left: dict, right: dict, lev: list, rev: list) -> list[dict]:
    """证据 —— 检查契约中的 claims 是否有来源引用支撑。

    对每条 business_rule，检查其是否有 evidence 字段。
    对整体契约，检查 source_refs 是否为空。

    当两侧 source_refs 均为空时，使用 ambiguous 类型标记（两面都缺证据），
    避免相同契约自比对时产生 missing_in_left + missing_in_right 的虚假差异。
    """
    items: list[dict] = []
    left_empty = not _ensure_list(left.get("source_refs"))
    right_empty = not _ensure_list(right.get("source_refs"))

    # 两侧都为空 → 一个 ambiguous 提示，不产生双向 missing
    if left_empty and right_empty:
        items.append(_item("证据", "ambiguous", "P3",
                           "两侧契约均缺少来源引用（source_refs 为空）",
                           "", "",
                           evidence=lev + rev,
                           suggestion="溯源自蓝湖 Raw Source 或知识库片段，确保结论可追溯"))
        return items

    # 单侧为空
    if left_empty:
        items.append(_item("证据", "missing_in_left", "P2",
                           "左侧契约缺少来源引用（source_refs 为空）",
                           "", "",
                           evidence=rev,
                           suggestion="溯源自蓝湖 Raw Source 或知识库片段，确保结论可追溯"))
    if right_empty:
        items.append(_item("证据", "missing_in_right", "P2",
                           "右侧契约缺少来源引用（source_refs 为空）",
                           "", "",
                           evidence=lev,
                           suggestion="溯源自 Wiki 页面或知识库片段，确保结论可追溯"))
    # 业务规则缺少 evidence
    for side, label, ev_src in ((left, "左", lev), (right, "右", rev)):
        for r in _ensure_list(side.get("business_rules")):
            if isinstance(r, dict) and not r.get("evidence"):
                rule_text = r.get("rule", str(r))
                items.append(_item("证据", "ambiguous", "P3",
                                   f"{label}侧业务规则缺少证据引用「{rule_text[:60]}」",
                                   suggestion="为业务规则补充蓝湖页面或知识库片段引用",
                                   evidence=ev_src))
    return items


# ═══════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════

def classify(left: dict, right: dict) -> list[dict]:
    """比对两份契约，返回差异项列表。left/right 为需求契约 dict。

    覆盖全部 12 个维度。证据从契约 source_refs 推导，保证确定性（无 LLM）。
    边缘情况处理：
      - 空字典 / None → 按空契约处理，标记为「内容缺失」
      - 两侧完全一致 → 返回空列表
      - 契约字段缺失 → 跳过该维度（不产生误报）
    """
    items: list[dict] = []
    left = left or {}
    right = right or {}

    # 提取证据引用（每个契约的 source_refs，在 gather 阶段已填充）
    lev = _ensure_list(left.get("source_refs"))
    rev = _ensure_list(right.get("source_refs"))

    # 边缘：两侧都为空 → 单条汇总差异
    if not any(left.values()) and not any(right.values()):
        items.append(_item("需求范围", "ambiguous", "P2",
                           "两侧契约均为空", "",
                           evidence=lev + rev,
                           suggestion="确认需求在两知识库中是否均有记录，检查搜索关键词是否正确"))
        return items

    # 边缘：单侧空
    if not any(left.values()):
        items.append(_item("需求范围", "missing_in_left", "P0",
                           "左侧契约内容缺失（完全为空）", "", "",
                           evidence=rev,
                           suggestion="检查 RAG 知识库是否缺少该需求，导入蓝湖或手动录入"))
        return items
    if not any(right.values()):
        items.append(_item("需求范围", "missing_in_right", "P0",
                           "右侧契约内容缺失（完全为空）", "", "",
                           evidence=lev,
                           suggestion="检查 Wiki 知识库是否缺少该需求，触发 Wiki 编译"))
        return items

    # 12 维逐维比对
    items.extend(_compare_requirement_scope(left, right, lev, rev))
    items.extend(_compare_client_scope(left, right, lev, rev))
    items.extend(_compare_business_rules(left, right, lev, rev))
    items.extend(_compare_fields(left, right, lev, rev))
    items.extend(_compare_apis(left, right, lev, rev))
    items.extend(_compare_exception_paths(left, right, lev, rev))
    items.extend(_compare_permissions(left, right, lev, rev))
    items.extend(_compare_data_dependencies(left, right, lev, rev))
    items.extend(_compare_acceptance_criteria(left, right, lev, rev))
    items.extend(_compare_test_coverage(left, right, lev, rev))
    items.extend(_compare_version(left, right, lev, rev))
    items.extend(_compare_evidence_quality(left, right, lev, rev))

    return items


# ═══════════════════════════════════════════════════════
# 汇总统计
# ═══════════════════════════════════════════════════════

def summarize(items: list[dict]) -> dict:
    """按 diff_type / severity / dimension 计数。"""
    def _count(key: str) -> dict[str, int]:
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
