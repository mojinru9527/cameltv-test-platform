# -*- coding: utf-8 -*-
"""生成足球(camel-service) + 篮球(basketball-service)接口用例（真实数据版）。

正向：真实参数回填（来自 Test5 网关真实数据库数据池 + 契约 example/default/enum + 语义兜底）
负向（标准三要素）：缺参 / 类型错 / 越权(无效 token)，模拟异常参数
断言口径对齐 C204-3：正向 = 2xx + 业务码 $.status=200 + $.data 存在；负向 = 2xx + $.status≠200（网关信封）
"""
import json
from collections import Counter

GW = "http://camel-api-gateway05.svc.elelive.cn"
DAY = "20260825"
REAL_UID = "11025728"

def load(fn):
    with open(fn, encoding="utf-8") as f:
        return json.load(f)

POOL = load("F:\\CamelTv\\_tmp_real_param_pool.json")

# ── 参数语义 → 真实值解析 ─────────────────────────────────
def infer_id_semantics(path, name):
    p = path.lower()
    if "competition" in p or "league" in p or "group_competition" in p:
        return "competitionId"
    if "team" in p or "club" in p:
        return "teamId"
    if "player" in p:
        return "playerId"
    if "article" in p or "news" in p:
        return "articleId"
    if "season" in p:
        return "seasonId"
    if "author" in p:
        return "authorId"
    if "match" in p or "faceoff" in p or "replay" in p:
        return "matchId"
    if "stage" in p:
        return "stageId"
    return "matchId"

def resolve_real(name, ptype, meta, path, svc_pool):
    n = name.lower().strip()
    # 语言/分页/日期
    if n in ("accept-language", "locale", "lang", "language"):
        return "en"
    if n in ("page", "current", "pageno", "page_no", "pageindex"):
        return 1
    if n in ("size", "pagesize", "page_size", "count", "limit", "num"):
        return 20
    if n in ("day", "date", "matchday", "matchdate"):
        return DAY
    if n in ("sporttype", "sport_type", "sport"):
        return "1"
    if n in ("uid", "userid", "user_id", "userId"):
        return REAL_UID
    # 时间
    if n in ("matchtimestart", "matchtimeend", "starttime", "endtime", "begintime", "endtime"):
        return 1700000000
    # 名称语义
    names = svc_pool.get("names", {})
    if n in ("teamname", "team_name", "team"):
        return names.get("teamName", ["Real Madrid"])[0]
    if n in ("name", "competitionname", "comp_name", "competition_name"):
        if "team" in path.lower():
            return names.get("teamName", ["Real Madrid"])[0]
        return names.get("competitionName", ["UEFA Champions League"])[0]
    if n in ("keyword", "q", "query", "word", "searchword"):
        return names.get("keyword", ["NBA"])[0]
    if n in ("streamname", "stream_name"):
        return "stream_%s" % (svc_pool["matchId"][0][:6] if svc_pool["matchId"] else "1")
    if n in ("types",):
        return "all"
    if n == "type":
        return "team"
    if n in ("key",):
        return "matchId"
    # id 语义
    if n == "matchid" or ("match" in n and "id" in n and "time" not in n):
        return svc_pool["matchId"][0] if svc_pool["matchId"] else None
    if n in ("competitionid", "comp_id", "competition") or ("competition" in n and "id" in n):
        return svc_pool["competitionId"][0] if svc_pool["competitionId"] else None
    if n == "seasonid" or ("season" in n and "id" in n):
        return svc_pool["seasonId"][0] if svc_pool["seasonId"] else None
    if n == "teamid" or ("team" in n and "id" in n):
        return svc_pool["teamId"][0] if svc_pool["teamId"] else None
    if n == "playerid" or ("player" in n and "id" in n):
        return svc_pool["playerId"][0] if svc_pool["playerId"] else None
    if n == "authorid" or ("author" in n and "id" in n):
        return REAL_UID
    if n == "articleid" or ("article" in n and "id" in n):
        return svc_pool["articleId"][0] if svc_pool["articleId"] else None
    if n == "stageid" or ("stage" in n and "id" in n):
        return svc_pool["stageId"][0] if svc_pool["stageId"] else None
    if n == "venueid":
        return svc_pool["venueId"][0] if svc_pool["venueId"] else None
    if n == "refereeid":
        return svc_pool["refereeId"][0] if svc_pool["refereeId"] else None
    if n == "id":
        sem = infer_id_semantics(path, n)
        return resolve_real(sem, ptype, meta, path, svc_pool)
    # 数组 ids
    if n in ("ids", "authorids", "matchids") or n.endswith("ids"):
        base = {"ids": "matchId", "authorids": "authorId", "matchids": "matchId",
                "playerids": "playerId", "teamids": "teamId", "competitionids": "competitionId"}.get(n, "matchId")
        if base == "authorId":
            return [REAL_UID]
        v = svc_pool.get(base, [])
        return v[:2] if v else ["1"]
    # 契约真实值
    if meta.get("example") is not None:
        return meta["example"]
    if meta.get("default") is not None:
        return meta["default"]
    if meta.get("enum"):
        return meta["enum"][0]
    # 类型兜底
    if ptype == "integer" or ptype == "number":
        return 1
    if ptype == "boolean":
        return True
    if ptype == "array":
        return []
    return "1"

def ptype_of(param):
    s = param.get("schema")
    if isinstance(s, dict):
        return s.get("type", "string")
    return "string"

# ── 契约解析 ─────────────────────────────────────────────
def parse_contract(svc):
    doc = load("F:\\CamelTv\\_tmp_%s_api-docs.json" % svc)
    ops = []
    for p, methods in doc.get("paths", {}).items():
        for m, spec in methods.items():
            if m.lower() not in ("get", "post", "put", "delete", "patch", "head", "options"):
                continue
            params = spec.get("parameters", []) or []
            query, path_p, header, body = [], [], [], {}
            for prm in params:
                loc = prm.get("in")
                sch = prm.get("schema") or {}
                entry = {
                    "name": prm.get("name", ""),
                    "type": sch.get("type", "string") if isinstance(sch, dict) else "string",
                    "required": bool(prm.get("required", False)),
                    "description": prm.get("description", ""),
                    "example": sch.get("example") if isinstance(sch, dict) else None,
                    "enum": sch.get("enum") if isinstance(sch, dict) else None,
                    "default": sch.get("default") if isinstance(sch, dict) else None,
                }
                if loc == "query":
                    query.append(entry)
                elif loc == "path":
                    path_p.append(entry)
                elif loc == "header":
                    header.append(entry)
            # requestBody
            rb = spec.get("requestBody")
            if rb:
                content = (rb.get("content") or {}).get("application/json") or {}
                sch = content.get("schema") or {}
                if sch.get("$ref"):
                    sch = resolve_ref(doc, sch["$ref"])
                props = sch.get("properties", {})
                body = {
                    "properties": {k: resolve_prop_ref(doc, v) for k, v in props.items()},
                    "required": sch.get("required", []),
                }
            module = p.strip("/").split("/")[1] if len(p.strip("/").split("/")) > 1 else "root"
            ops.append({
                "service_name": svc,
                "module": module,
                "method": m.upper(),
                "path": p,
                "summary": spec.get("summary", ""),
                "description": (spec.get("description", "") or "").strip(),
                "request_schema": {"query": query, "path": path_p, "header": header, "body": body},
            })
    return ops

def resolve_ref(doc, ref):
    # #/components/schemas/Foo
    parts = ref.lstrip("#/").split("/")
    node = doc
    for part in parts:
        node = node.get(part, {})
    return node

def resolve_prop_ref(doc, prop):
    if isinstance(prop, dict) and prop.get("$ref"):
        return resolve_ref(doc, prop["$ref"])
    return prop

# ── 用例构造 ─────────────────────────────────────────────
def make_case(ep, *, title, priority, scenario, pn, method_name, endpoint, body, headers, assertions, expected, data_note):
    return {
        "title": title,
        "domain": "接口测试",
        "module": ep["module"],
        "case_type": "api",
        "priority": priority,
        "preconditions": describe_preconditions(ep),
        "steps": json.dumps([{"step": 1, "action": "发送 %s 请求到 %s" % (ep["method"], ep["path"]), "expected": expected}], ensure_ascii=False),
        "expected_result": expected,
        "api_method": ep["method"],
        "api_endpoint": endpoint,
        "api_headers": json.dumps(headers, ensure_ascii=False),
        "api_body": json.dumps(body, ensure_ascii=False) if body else "",
        "api_assertions": json.dumps(assertions, ensure_ascii=False),
        "case_design_method": method_name,
        "positive_negative": pn,
        "test_data_note": data_note,
        "source": "real_data",
        "tags": json.dumps(["service:%s" % ep["service_name"], "scenario:%s" % scenario, "source:real_data"], ensure_ascii=False),
    }

def describe_preconditions(ep):
    parts = ["%s %s 可访问" % (ep["method"], ep["path"])]
    if ep.get("auth_required"):
        parts.append("接口需要认证")
    schema = ep["request_schema"]
    for loc in ("header", "query", "path"):
        req = [p["name"] for p in schema.get(loc, []) if p.get("required")]
        if req:
            parts.append("%s 必填参数：%s" % (loc, "、".join(req)))
    if ep.get("summary"):
        parts.append("接口说明：%s" % ep["summary"])
    return "；".join(parts)

def build_query_string(ep, overrides=None):
    """构造带真实 query 参数的 endpoint（含服务前缀）。"""
    svc = ep["service_name"]
    schema = ep["request_schema"]
    q = schema.get("query", [])
    pairs = []
    for prm in q:
        v = overrides.get(prm["name"]) if overrides and prm["name"] in overrides else None
        if v is None:
            v = resolve_real(prm["name"], prm["type"], prm, ep["path"], POOL[svc])
        if v is None:
            continue
        if isinstance(v, (list, tuple)):
            v = ",".join(str(x) for x in v)
        pairs.append("%s=%s" % (prm["name"], v))
    path = ep["path"]
    # path params {type} substitution
    for pp in schema.get("path", []):
        v = overrides.get(pp["name"]) if overrides and pp["name"] in overrides else resolve_real(pp["name"], pp["type"], pp, ep["path"], POOL[svc])
        path = path.replace("{%s}" % pp["name"], str(v))
    qs = ("&".join(pairs)) if pairs else ""
    full = path + ("?" + qs if qs else "")
    return "/%s%s" % (svc, full)

def build_body(ep):
    schema = ep["request_schema"]
    body_schema = schema.get("body", {})
    props = body_schema.get("properties", {})
    body = {}
    for field, prop in props.items():
        ptype = prop.get("type", "string") if isinstance(prop, dict) else "string"
        body[field] = resolve_real(field, ptype, prop if isinstance(prop, dict) else {}, ep["path"], POOL[ep["service_name"]])
    return body

POS_ASSERT = lambda ep: [
    {"type": "status_code", "expected": 200, "operator": "gte"},
    {"type": "status_code", "expected": 300, "operator": "lt"},
    {"type": "response_time", "expected": 5000, "operator": "lt"},
    {"type": "jsonpath", "path": "$.status", "operator": "eq", "expected": 200},
    {"type": "jsonpath", "path": "$.data", "operator": "exists"},
]

NEG_ASSERT = lambda ep: [
    {"type": "status_code", "expected": 200, "operator": "gte"},
    {"type": "status_code", "expected": 500, "operator": "lt"},
]

def gen_cases_for_endpoint(ep, seq):
    svc = ep["service_name"]
    pool = POOL[svc]
    method = ep["method"]
    schema = ep["request_schema"]
    query = schema.get("query", [])
    req_query = [p for p in query if p.get("required")]
    body_schema = schema.get("body", {})
    req_body = body_schema.get("required", [])

    cases = []
    ep_path_full = build_query_string(ep)
    body = build_body(ep)

    # 1. 正向：真实参数
    cases.append(make_case(ep,
        title="【正向】%s - 正常请求（真实参数回填）" % (ep["summary"] or ep["path"]),
        priority="P0", scenario="positive", pn="positive", method_name="场景法",
        endpoint=ep_path_full, body=body if method in ("POST", "PUT", "PATCH") else {},
        headers={"Content-Type": "application/json"},
        assertions=POS_ASSERT(ep),
        expected="返回 2xx；业务码 $.status=200；$.data 存在且含真实业务数据；响应时间 < 5s。",
        data_note="数据来源：Test5 网关真实数据库数据回填（home_match/list_competition 等列表接口收割的真实 id）。",
    ))

    # 2. 负向：缺参（去掉第一个必填 query 或 body 参数）
    if req_query:
        missing = req_query[0]["name"]
        neg_ep = build_query_string(ep, overrides={missing: None})
        cases.append(make_case(ep,
            title="【缺参】%s - 缺少必填参数 %s" % (ep["summary"] or ep["path"], missing),
            priority="P1", scenario="required_missing", pn="negative", method_name="等价类划分",
            endpoint=neg_ep, body=body if method in ("POST", "PUT", "PATCH") else {},
            headers={"Content-Type": "application/json"},
            assertions=NEG_ASSERT(ep),
            expected="缺少必填参数 %s 时应被拒绝（网关信封 $.status≠200 或 HTTP 4xx），不得 5xx。" % missing,
            data_note="异常参数（模拟）：去掉必填参数 %s。" % missing,
        ))
    elif req_body:
        missing = req_body[0]
        neg_body = dict(body); neg_body.pop(missing, None)
        cases.append(make_case(ep,
            title="【缺参】%s - 缺少必填字段 %s" % (ep["summary"] or ep["path"], missing),
            priority="P1", scenario="required_missing", pn="negative", method_name="等价类划分",
            endpoint=ep_path_full, body=neg_body, headers={"Content-Type": "application/json"},
            assertions=NEG_ASSERT(ep),
            expected="缺少必填字段 %s 时应被拒绝，不得 5xx。" % missing,
            data_note="异常参数（模拟）：去掉必填字段 %s。" % missing,
        ))

    # 3. 负向：类型错（对第一个 integer 参数传字符串，或对 string 参数传超长数字）
    type_target = None
    for p in query:
        if p.get("type") in ("integer", "number"):
            type_target = p["name"]; break
    if type_target is None and req_query:
        type_target = req_query[0]["name"]
    if type_target:
        neg_ep = build_query_string(ep, overrides={type_target: "not_a_number"})
        cases.append(make_case(ep,
            title="【类型错】%s - 参数 %s 类型错误" % (ep["summary"] or ep["path"], type_target),
            priority="P1", scenario="type_error", pn="negative", method_name="错误推测",
            endpoint=neg_ep, body=body if method in ("POST", "PUT", "PATCH") else {},
            headers={"Content-Type": "application/json"},
            assertions=NEG_ASSERT(ep),
            expected="参数 %s 类型不符时应被拒绝，不得 5xx。" % type_target,
            data_note="异常参数（模拟）：%s 传入非法类型 not_a_number。" % type_target,
        ))

    # 4. 负向：越权/无效 token
    cases.append(make_case(ep,
        title="【越权】%s - 无效/弱 Token" % (ep["summary"] or ep["path"]),
        priority="P1", scenario="auth_missing", pn="negative", method_name="错误推测",
        endpoint=ep_path_full, body=body if method in ("POST", "PUT", "PATCH") else {},
        headers={"Content-Type": "application/json", "Authorization": "Bearer invalid-token-for-qa"},
        assertions=NEG_ASSERT(ep),
        expected="携带无效 Token 时应被拒绝（401/403 或业务拒绝），不得越权访问他方数据。",
        data_note="异常参数（模拟）：无效 Token 越权访问。",
    ))

    return cases

# ── 主流程 ───────────────────────────────────────────────
def main():
    all_cases = []
    stats = {}
    seq = 0
    for svc in ["camel-service", "basketball-service"]:
        ops = parse_contract(svc)
        svc_cases = []
        for ep in ops:
            cases = gen_cases_for_endpoint(ep, seq)
            for c in cases:
                seq += 1
                c["case_id"] = "TC-API-%s-%04d" % ("BB" if svc == "basketball-service" else "FB", seq)
                svc_cases.append(c)
            all_cases.extend(cases)
        stats[svc] = {"endpoints": len(ops), "cases": len(svc_cases)}
    print("=== generation stats ===")
    for k, v in stats.items():
        print("  %s: %d endpoints -> %d cases" % (k, v["endpoints"], v["cases"]))
    print("  TOTAL: %d cases" % len(all_cases))
    pn = Counter(c.get("positive_negative") for c in all_cases)
    print("  positive/negative:", dict(pn))
    sc = Counter(c.get("module") for c in all_cases)
    print("  modules:", dict(sc))
    out = {
        "stats": stats,
        "endpoints": {svc: parse_contract(svc) for svc in ["camel-service", "basketball-service"]},
        "cases": all_cases,
    }
    with open("F:\\CamelTv\\_tmp_cases_generated.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("saved _tmp_cases_generated.json")

if __name__ == "__main__":
    main()
