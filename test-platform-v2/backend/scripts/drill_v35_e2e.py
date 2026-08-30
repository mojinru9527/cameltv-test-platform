#!/usr/bin/env python
"""AITDE V3.5 Continuous Acceptance real-DB E2E drill (part 4 of the objective).

Runs the true pipeline against the ACTUAL migrated app DB (data/*.db, 144 tables,
alembic head) using the real service + repository + schemas:

    capture_fingerprint -> observe_build -> create_campaign -> evaluate_gate -> create_trigger

This is stronger than the in-memory test fixture: it exercises the real schema.
Run from the backend directory:
    python scripts/drill_v35_e2e.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.db import SessionLocal  # noqa: E402
from app.modules.aitde.common.enums import (  # noqa: E402
    BuildObservationStatus,
    CampaignType,
    ContinuousTriggerType,
    FingerprintSourceType,
    QualityGateResult,
)
from app.modules.aitde.continuous import service  # noqa: E402
from app.modules.aitde.continuous.schemas import (  # noqa: E402
    CampaignCreateIn,
    FingerprintCaptureIn,
    TriggerIn,
)

PROJECT_ID = 901
MISSION_ID = 701
ENV_ID = 1


def _components(openapi_hash: str, api: str = "1.0") -> dict:
    return {"service_versions": {"api": api}, "openapi_hash": openapi_hash}


def main() -> int:
    results: dict[str, bool] = {}
    db = SessionLocal()
    try:
        # ── 1. EnvironmentFingerprint capture (dedupe on same hash) ──
        fp1 = service.capture_fingerprint(
            db, PROJECT_ID,
            FingerprintCaptureIn(components=_components("abc"), source_type=FingerprintSourceType.AUTO),
        )
        fp1b = service.capture_fingerprint(
            db, PROJECT_ID,
            FingerprintCaptureIn(components=_components("abc"), source_type=FingerprintSourceType.AUTO),
        )
        results["fingerprint_dedupes_same_hash"] = (
            fp1["fingerprint_hash"] == fp1b["fingerprint_hash"] and fp1["id"] == fp1b["id"]
        )
        print(f"[1] fingerprint id={fp1['id']} hash={fp1['fingerprint_hash']:.10s} dedupe={results['fingerprint_dedupes_same_hash']}")

        # ── 2. BuildObservation (NEW on first, dedupe on same fp) ──
        obs1 = service.observe_build(db, ENV_ID, MISSION_ID, fp1["id"])
        obs1b = service.observe_build(db, ENV_ID, MISSION_ID, fp1["id"])
        results["build_observation_no_duplicate"] = (
            obs1["id"] == obs1b["id"] and obs1["status"] == BuildObservationStatus.NEW.value
        )
        print(f"[2] build_observation id={obs1['id']} status={obs1['status']} dedupe={results['build_observation_no_duplicate']}")

        # ── 3. ExecutionCampaign (immutable scenario snapshot) ──
        campaign = service.create_campaign(
            db,
            CampaignCreateIn(
                project_id=PROJECT_ID, mission_id=MISSION_ID, environment_id=1,
                campaign_type=CampaignType.IMPACTED,
                scenarios=[
                    {"scenario_id": 1, "scenario_version_id": 10, "required": "REQUIRED",
                     "selection_reason": {"planner": "v1"}},
                ],
            ),
        )
        results["campaign_snapshot_created"] = campaign["campaign_type"] == CampaignType.IMPACTED.value
        detail = service.get_campaign(db, campaign["id"], PROJECT_ID)
        results["campaign_scenario_bound"] = len(detail["scenarios"]) == 1
        print(f"[3] campaign id={campaign['id']} type={campaign['campaign_type']} scenarios={len(detail['scenarios'])}")

        # ── 4. QualityGate: 0 execution with scenarios -> FAIL; no campaign -> INCONCLUSIVE ──
        gate = service.evaluate_gate(db, PROJECT_ID, MISSION_ID, campaign["id"], None)
        results["gate_zero_execution_fail"] = gate["result"] == QualityGateResult.FAIL.value
        gate_none = service.evaluate_gate(db, PROJECT_ID, MISSION_ID, None, None)
        results["gate_no_scenario_inconclusive"] = gate_none["result"] == QualityGateResult.INCONCLUSIVE.value
        print(f"[4] gate(result={gate['result']}, checks={gate.get('checks_json')}) fail={results['gate_zero_execution_fail']} | no-campaign={gate_none['result']} inconclusive={results['gate_no_scenario_inconclusive']}")

        # ── 5. Trigger ──
        trig = service.create_trigger(
            db, TriggerIn(project_id=PROJECT_ID, trigger_type=ContinuousTriggerType.FINGERPRINT, config={"interval_min": 5})
        )
        results["trigger_created"] = (
            trig["trigger_type"] == ContinuousTriggerType.FINGERPRINT.value
            and len(service.list_triggers(db, PROJECT_ID)) == 1
        )
        print(f"[5] trigger id={trig['id']} type={trig['trigger_type']} created={results['trigger_created']}")

    finally:
        db.close()

    print()
    ok = all(results.values())
    for k, v in results.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
    print(f"\nRESULT: {'PASS' if ok else 'FAIL'} (V3.5 real-DB E2E fingerprint->build->campaign->gate->trigger)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
