# -*- coding: utf-8 -*-
"""写入 platform.db：basketball-service(服务+端点) + 足球/篮球真实数据用例(test_case)。"""
import sqlite3, json, shutil, datetime, os

DB = r"F:\CamelTv\test-platform-v2\backend\data\platform.db"
FINAL = r"F:\CamelTv\_tmp_cases_final.json"

def now():
    return datetime.datetime.now().isoformat(sep=" ", timespec="seconds")

def main():
    # 1. 备份
    bak = DB + ".bak-sports-realdata-" + datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    shutil.copy2(DB, bak)
    print("backup:", os.path.basename(bak))

    data = json.load(open(FINAL, encoding="utf-8"))
    endpoints = data["endpoints"]
    cases = data["cases"]

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    ts = now()

    # 2. api_service：basketball-service
    c.execute("SELECT id FROM api_service WHERE project_id=1 AND name='basketball-service'")
    row = c.fetchone()
    if row:
        bb_svc = row[0]
        print("basketball-service already exists: id=%d" % bb_svc)
    else:
        c.execute("""INSERT INTO api_service
            (project_id, name, display_name, description, default_base_path, owner, status, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (1, "basketball-service", "basketball-service", "篮球直播服务", "/basketball-service", "", "active", ts, ts))
        bb_svc = c.lastrowid
        print("basketball-service created: id=%d" % bb_svc)

    c.execute("SELECT id FROM api_service WHERE project_id=1 AND name='camel-service'")
    camel_svc = c.fetchone()[0]
    print("camel-service id=%d" % camel_svc)

    svc_ids = {"basketball-service": bb_svc, "camel-service": camel_svc}

    # 3. api_endpoint：匹配现有，创建缺失；记录 endpoint_id 映射 (svc -> (method,path) -> id)
    ep_id_map = {}
    created_ep = 0
    for svc, ops in endpoints.items():
        sid = svc_ids[svc]
        ep_id_map[svc] = {}
        for op in ops:
            method = op["method"]; path = op["path"]
            c.execute("SELECT id FROM api_endpoint WHERE service_id=? AND method=? AND path=?", (sid, method, path))
            r = c.fetchone()
            if r:
                ep_id_map[svc][(method, path)] = r[0]
            else:
                req = json.dumps(op["request_schema"], ensure_ascii=False)
                c.execute("""INSERT INTO api_endpoint
                    (project_id, service_id, module, method, path, summary, description, request_schema, response_schema, auth_required, deprecated, source, version, created_at, updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (1, sid, op["module"], method, path, op.get("summary",""), op.get("description",""),
                     req, "{}", 0, 0, "real_data_import", "", ts, ts))
                ep_id_map[svc][(method, path)] = c.lastrowid
                created_ep += 1
    print("api_endpoint created (missing):", created_ep)

    # 4. test_case 写入
    ins = 0
    for cs in cases:
        svc = "basketball-service" if "/basketball-service/" in cs["api_endpoint"] else "camel-service"
        # 由 api_endpoint 反查 endpoint_id（endpoint 不含服务前缀）
        ep_relative = cs["api_endpoint"].split("?", 1)[0].replace("/basketball-service", "").replace("/camel-service", "")
        # 从 api_method + 相对 path 找 endpoint_id
        method = cs["api_method"]
        eid = ep_id_map[svc].get((method, ep_relative))
        if eid is None:
            # 尝试用 path 匹配（去 query）
            for (m, p), i in ep_id_map[svc].items():
                if m == method and p == ep_relative:
                    eid = i; break
        spec_ref = "api_endpoint:%d" % eid if eid else ""
        c.execute("""INSERT INTO test_case
            (project_id, case_id, title, domain, module, case_type, priority, status,
             tags, preconditions, steps, expected_result,
             api_method, api_endpoint, api_spec_ref, source,
             api_headers, api_body, api_assertions,
             case_design_method, positive_negative, test_data_note,
             last_response_json, last_run_status, api_endpoint_id, review_status, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (1, cs["case_id"], cs["title"], cs["domain"], cs["module"], "api", cs["priority"], "active",
             cs["tags"], cs["preconditions"], cs["steps"], cs["expected_result"],
             cs["api_method"], cs["api_endpoint"], spec_ref, cs["source"],
             cs["api_headers"], cs["api_body"], cs["api_assertions"],
             cs["case_design_method"], cs["positive_negative"], cs["test_data_note"],
             cs.get("last_response_json", ""), cs.get("last_run_status", ""),
             eid, "draft", ts, ts))
        ins += 1

    conn.commit()

    # 5. 校验
    c.execute("SELECT count(*) FROM api_endpoint WHERE service_id=?", (bb_svc,))
    bb_ep = c.fetchone()[0]
    c.execute("SELECT count(*), sum(case_type='api') FROM test_case WHERE source='real_data'")
    tc_total, tc_api = c.fetchone()
    print("\n=== write summary ===")
    print("  basketball-service endpoints: %d" % bb_ep)
    print("  test_case inserted (source=real_data): %d (api=%d)" % (tc_total, tc_api))
    c.execute("SELECT last_run_status, count(*) FROM test_case WHERE source='real_data' GROUP BY last_run_status")
    for r in c.fetchall():
        print("    last_run_status=%s: %d" % (r[0], r[1]))
    conn.close()
    print("done. backup at:", bak)

if __name__ == "__main__":
    main()
