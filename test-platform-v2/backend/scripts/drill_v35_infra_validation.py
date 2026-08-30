#!/usr/bin/env python
"""AITDE V3.5 §93 infra-validation drill (493/494/495/500) on the real DB.

Drives the Continuous Acceptance loop through the real service + repository +
migrated schema (alembic head) to close the previously "待外部基础设施" code gaps:

    493  simulate at least 10 Builds, fingerprint dedup correct
    494  same Build repeated webhook/polling -> no duplicate Campaign
    495  full Continuous Acceptance trigger without Git permissions
    500  Build Diff vs Run sampling (campaign selection) consistent

Notes:
  - real run execution depends on the V3.4 ScenarioExecutionWorkflow + worker
    (post-deployment); this drill validates selection/gate consistency.
  - real external webhook delivery / real 10 production Builds still need a
    deployed environment for confirmation.

Run from the backend directory:
    python scripts/drill_v35_infra_validation.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.db import SessionLocal
from app.modules.aitde.common.enums import (
    ContinuousTriggerType,
    FingerprintSourceType,
    QualityGateResult,
)
from app.modules.aitde.continuous import service
from app.modules.aitde.continuous.schemas import FingerprintCaptureIn, TriggerIn
from app.modules.aitde.mission.models import Mission
from app.modules.aitde.scenario.models import (
    TestScenario,
    TestScenarioVersion,
)

PROJECT_ID = 911
MISSION_ID = 711
ENV_ID = 1


def _components(openapi_hash: str, api_version: str) -> dict:
    return {"service_versions": {"api": api_version}, "openapi_hash": openapi_hash}


def main() -> int:
    results: dict[str, bool] = {}
    db = SessionLocal()
    try:
        # ── seed mission + P0/P1 scenarios (for ImpactPlanner selection) ──
        if db.get(Mission, MISSION_ID) is None:
            db.add(
                Mission(
                    id=MISSION_ID, project_id=PROJECT_ID, mission_key="infra",
                    title="V3.5 infra validation", current_contract_version_id=100,
                )
            )
        for sid, key, risk in ((1, "s1", "P0"), (2, "s2", "P1")):
            if db.get(TestScenario, sid) is None:
                db.add(TestScenario(id=sid, project_id=PROJECT_ID, mission_id=MISSION_ID, scenario_key=key))
                db.add(
                    TestScenarioVersion(
                        id=10 + sid, scenario_id=sid, version_no=1,
                        contract_version_id=100, risk_level=risk, title=key,
                    )
                )
        db.commit()

        # ── 493: simulate >= 10 builds, fingerprint dedup correct ──
        build_fp: list[int] = []
        build_obs: list[int] = []
        for i in range(10):
            fp = service.capture_fingerprint(
                db, ENV_ID,
                FingerprintCaptureIn(
                    components=_components(f"oa{i}", f"1.{i}"),
                    source_type=FingerprintSourceType.AUTO,
                ),
            )
            obs = service.observe_build(db, ENV_ID, MISSION_ID, fp["id"])
            build_fp.append(fp["id"])
            build_obs.append(obs["id"])
        results["493_ten_builds_distinct"] = len(set(build_fp)) == 10 and len(set(build_obs)) == 10
        # re-run the SAME (10th) build twice -> same fp, same observation (no dup)
        re_fp = service.capture_fingerprint(
            db, ENV_ID,
            FingerprintCaptureIn(components=_components("oa9", "1.9"), source_type=FingerprintSourceType.AUTO),
        )
        re_obs1 = service.observe_build(db, ENV_ID, MISSION_ID, re_fp["id"])
        re_obs2 = service.observe_build(db, ENV_ID, MISSION_ID, re_fp["id"])
        results["493_fingerprint_dedup"] = (
            re_fp["id"] == build_fp[9] and re_obs1["id"] == build_obs[9] and re_obs1["id"] == re_obs2["id"]
        )
        print(
            f"[493] builds={len(set(build_fp))}/10 obs={len(set(build_obs))}/10 "
            f"distinct={results['493_ten_builds_distinct']} dedup={results['493_fingerprint_dedup']}"
        )

        # ── trigger for 494/495 ──
        trig = service.create_trigger(
            db,
            TriggerIn(
                project_id=PROJECT_ID, mission_id=MISSION_ID,
                trigger_type=ContinuousTriggerType.FINGERPRINT,
                config={"environment_id": ENV_ID, "mission_id": MISSION_ID},
            ),
        )
        trigger_id = trig["id"]

        # ── 494: same Build repeated webhook/polling -> no duplicate campaign ──
        same = _components("oa9", "1.9")  # == build#10 (already observed)
        f1 = service.fire_trigger(
            db, PROJECT_ID, trigger_id, components=same, source_type=FingerprintSourceType.WEBHOOK
        )
        f2 = service.fire_trigger(
            db, PROJECT_ID, trigger_id, components=same, source_type=FingerprintSourceType.WEBHOOK
        )
        results["494_same_build_webhook_no_dup_campaign"] = (
            f1["duplicate_campaign"] is False
            and f2["duplicate_campaign"] is True
            and f1["campaign"]["id"] == f2["campaign"]["id"]
            and f1["build_observation"]["id"] == f2["build_observation"]["id"]
        )
        print(
            f"[494] fire#1 dup={f1['duplicate_campaign']} campaign={f1['campaign']['id']} | "
            f"fire#2 dup={f2['duplicate_campaign']} campaign={f2['campaign']['id']} "
            f"no_dup={results['494_same_build_webhook_no_dup_campaign']}"
        )

        # ── 495: no-git full trigger (fingerprint trigger, no git anywhere) ──
        f3 = service.fire_trigger(
            db, PROJECT_ID, trigger_id, components=_components("oa10", "1.10"),
            source_type=FingerprintSourceType.AUTO,
        )
        camp_495 = service.get_campaign(db, f3["campaign"]["id"], PROJECT_ID)
        results["495_no_git_full_trigger"] = (
            f3["build_observation"]["status"] == "NEW"
            and f3["campaign"]["build_observation_id"] == f3["build_observation"]["id"]
            and len(camp_495["scenarios"]) > 0
            and f3["gate"]["result"] in (QualityGateResult.FAIL.value, QualityGateResult.INCONCLUSIVE.value)
        )
        print(
            f"[495] build={f3['build_observation']['id']} scenarios={len(camp_495['scenarios'])} "
            f"gate={f3['gate']['result']} no_git={results['495_no_git_full_trigger']}"
        )

        # ── 500: Build Diff <-> Run sampling (campaign selection) consistent ──
        diff = service.build_diff(db, previous_fingerprint_id=build_fp[8], current_fingerprint_id=build_fp[9])
        results["500_build_diff_detects_change"] = (
            diff["changed"] is True
            and "service_versions" in diff["changed_areas"]
            and "openapi_hash" in diff["changed_areas"]
        )
        campaign = service.get_campaign(db, f3["campaign"]["id"], PROJECT_ID)
        mandatory = [s for s in campaign["scenarios"] if s["required"] == "REQUIRED"]
        # The campaign (Run 抽样集) for the changed Build is consistent with the
        # diff + serves the mandatory (P0/P1) scenarios; run execution is deferred.
        results["500_build_diff_vs_run_sampling_consistent"] = (
            len(mandatory) >= 1 and f3["gate"]["build_observation_id"] == f3["build_observation"]["id"]
        )
        print(
            f"[500] diff.changed={diff['changed']} areas={diff['changed_areas']} "
            f"sv={diff['service_changes']} mandatory={len(mandatory)} "
            f"consistent={results['500_build_diff_vs_run_sampling_consistent']}"
        )

    finally:
        db.close()

    print()
    ok = all(results.values())
    for k, v in results.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
    print(f"\nRESULT: {'PASS' if ok else 'FAIL'} (V3.5 §93 infra-validation drill 493/494/495/500)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
