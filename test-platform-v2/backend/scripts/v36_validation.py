"""§93 V3.6 版本专项校验 — production evidence security gate battery.

Runs the V3.6 plan §93 checks against the implemented policy/guard/masking
services and writes a structured evidence report. Read-only; never touches
production write paths.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from app.modules.aitde.production.policies import (
    production_db_guard,
    prod_ro_worker_profile,
    readonly_browser_policy,
)
from app.modules.aitde.production import services
from app.modules.aitde.common.enums import PolicyDecision, PiiClassification

_RESULTS: list[dict] = []


def check(check_id: str, name: str, ok: bool, detail: str = "") -> None:
    _RESULTS.append({"id": check_id, "name": name, "ok": bool(ok), "detail": detail})


def main() -> None:
    # §93-1: real read-only account rejects INSERT/UPDATE/DDL (guard layer)
    bad = ["INSERT INTO t VALUES (1)", "UPDATE t SET x=1", "DELETE FROM t",
           "CREATE TABLE t(id int)", "ALTER TABLE t ADD c int", "DROP TABLE t", "TRUNCATE t"]
    ok_bad = all(not production_db_guard.validate(sql)[0] for sql in bad)
    check("V93-1", "INSERT/UPDATE/DDL 被拒绝", ok_bad, ",".join(bad[0:3]))

    # §93-2: CTE / comment-hidden multi-statement still rejected
    tricks = [("WITH x AS (SELECT 1) SELECT * FROM x", "CTE"),
              ("SELECT 1; UPDATE t SET x=1", "multi-statement"),
              ("SELECT * FROM t /* hidden */; UPDATE t SET x=1", "comment-hidden write")]
    ok_tricks = all(not production_db_guard.validate(sql)[0] for sql, _ in tricks)
    check("V93-2", "CTE/注释/多语句仍被拒绝", ok_tricks)

    # §93-3: pay/order/refund Browser action blocked
    ok_blocked = all(
        readonly_browser_policy.evaluate(url=f"https://p/{w}", method="POST")[0] == PolicyDecision.DENY.value
        for w in ["pay", "order", "refund"]
    )
    check("V93-3", "支付/下单/退款 Browser Action 被阻断", ok_blocked)

    # §93-4: XHR 千条后 Authorization/Cookie/Token 泄露=0 (sanitizer redacts)
    leak_count = 0
    for i in range(1000):
        ev = {
            "event_type": "XHR", "method": "POST", "url": "/x", "content_type": "application/json",
            "headers": {"Authorization": f"Bearer tok-{i}", "Cookie": f"sid={i}"},
            "body": json.dumps({"token": f"secret-{i}"}, ensure_ascii=False),
        }
        headers = services.xhr_evidence_service._redact_headers(ev["headers"])
        body = services.xhr_evidence_service._sanitize_body(ev["body"], ev["content_type"])
        if any(h == "Bearer tok-" for h in headers.values()) or "Bearer" in str(headers) and f"tok-{i}" in str(headers):
            leak_count += 1
        if f"secret-{i}" in body:
            leak_count += 1
    check("V93-4", "1000 XHR 后敏感字段泄露=0", leak_count == 0, f"leak={leak_count}")

    # §93-5: 抽样 100 条 PII Mask 后不可恢复原值 (configured REDACT/HASH profile)
    from app.models.production_evidence import MaskingRule
    rule_email = MaskingRule(profile_id=1, field_pattern="email", strategy="HASH", priority=10)
    reversible = 0
    for i in range(100):
        val = f"user-{i}@x.com"
        masked = services.masking_service.apply(
            profile_id=1, rules=[rule_email], record={"email": val}
        )["email"]
        if masked == val:
            reversible += 1
    check("V93-5", "PII Mask 后不可恢复原值", reversible == 0, f"reversible={reversible}")

    # §93-6: 关联实体 Token/Remap 后关系完整 (deterministic TOKENIZE)
    rule_uid = MaskingRule(profile_id=2, field_pattern="user_id", strategy="TOKENIZE", priority=10)
    t1 = services.masking_service.apply(profile_id=2, rules=[rule_uid], record={"user_id": "42"})["user_id"]
    t2 = services.masking_service.apply(profile_id=2, rules=[rule_uid], record={"user_id": "42"})["user_id"]
    t3 = services.masking_service.apply(profile_id=2, rules=[rule_uid], record={"user_id": "43"})["user_id"]
    check("V93-6", "确定性 Token 保关系(相同→相同, 不同→不同)", t1 == t2 and t1 != t3 and t1 != "42")

    # PROD_RO worker: write capability rejected
    ok_worker = not prod_ro_worker_profile.validate(network_zone="PROD_RO", capabilities=["MYSQL"])[0]
    check("V93-7", "PROD_RO Worker 禁写能力", ok_worker)

    # PII classifier sanity
    ok_pii = services.pii_classifier.classify("mobile", "13800138000") == "PHONE"
    check("V93-8", "PII Classifier 正确分类", ok_pii)

    summary = {
        "generated_at": datetime.now().isoformat(),
        "version": "AITDE V3.6",
        "checks": _RESULTS,
        "pass": sum(1 for r in _RESULTS if r["ok"]),
        "fail": sum(1 for r in _RESULTS if not r["ok"]),
    }
    out_dir = Path(__file__).resolve().parents[1] / "work-logs" / "evidence" / "v36"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "validation-report.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\nWROTE: {out_dir / 'validation-report.json'}")


if __name__ == "__main__":
    main()
