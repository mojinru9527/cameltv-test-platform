# -*- coding: utf-8 -*-
"""Batch205-Q4：用重执行结果 UPDATE 已落库的 test_case（按 case_id 更新，不重复插入）。"""
import sqlite3, json, os

DB = r"F:\CamelTv\test-platform-v2\backend\data\platform.db"

def main():
    data = json.load(open("F:\\CamelTv\\_tmp_cases_final.json", encoding="utf-8"))
    cases = data["cases"]

    # 备份（在第一次写入的备份之外再加一次）
    bak = DB + ".bak-sports-realdata-q4-" + __import__("datetime").datetime.now().strftime("%Y%m%d%H%M%S")
    import shutil
    shutil.copy2(DB, bak)
    print("backup:", os.path.basename(bak))

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # 建立 service_id 映射（供 api_endpoint_id 反查，若需要）
    updated = 0; inserted = 0; notfound = 0
    for cs in cases:
        case_id = cs["case_id"]
        c.execute("SELECT id, api_endpoint_id FROM test_case WHERE case_id=? AND source='real_data'", (case_id,))
        row = c.fetchone()
        if row:
            c.execute("""UPDATE test_case SET
                last_response_json=?, last_run_status=?, api_assertions=?, test_data_note=?, api_endpoint=?, steps=?
                WHERE id=?""",
                (cs.get("last_response_json", ""), cs.get("last_run_status", ""),
                 cs["api_assertions"], cs["test_data_note"], cs["api_endpoint"], cs["steps"], row[0]))
            updated += 1
        else:
            notfound += 1  # 兜底：按 case_id 无匹配则跳过（保留首轮插入，不重复造数）
    conn.commit()

    c.execute("SELECT last_run_status, count(*) FROM test_case WHERE source='real_data' GROUP BY last_run_status ORDER BY last_run_status")
    print("\n=== after Q4 update ===")
    print("  updated=%d  notfound=%d" % (updated, notfound))
    for r in c.fetchall():
        print("    last_run_status=%s: %d" % (r[0], r[1]))
    c.execute("SELECT count(*) FROM test_case WHERE source='real_data'")
    print("  total real_data cases:", c.fetchone()[0])
    conn.close()
    print("done. backup:", bak)

if __name__ == "__main__":
    main()
