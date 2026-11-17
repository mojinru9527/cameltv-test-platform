"""Create the production M6 integrated Run via the production backend services."""
from __future__ import annotations

import json
import time

from sqlalchemy import select

from app.aiqe.services.capability_registry import register_manifest
from app.aiqe.services.run_launch import launch_run
from app.aiqe.services.workflow_service import approve_workflow, create_workflow
from app.core.db import SessionLocal
from app.models.project import Project
from app.services.ai_agent_service import register_agent

ROOT = r"F:\CamelTv-worktrees\DeepSeek_Harness-aiqe-post-pr595-v14"
OUT = ROOT + r"\work-logs\evidence\prod-m6-integrated"

graph = {
    "schema_version": "1.0",
    "nodes": [
        {
            "key": "sports_api",
            "driver": "http",
            "depends_on": [],
            "input": {
                "url": "https://api.cameltv.live/account-service/ee/client/general",
                "method": "GET",
                "timeout_ms": 15000,
            },
            "assertions": [
                {
                    "assertion_key": "sports_api_status",
                    "type": "http_status",
                    "oracle_layer": "STD",
                    "oracle_ref": "M6-SPORTS-API",
                    "expected": 200,
                },
                {
                    "assertion_key": "sports_api_region",
                    "type": "jsonpath",
                    "oracle_layer": "STD",
                    "oracle_ref": "M6-SPORTS-API",
                    "path": "$.data.region",
                    "expected": "CN",
                },
            ],
        },
        {
            "key": "sports_ui",
            "driver": "external_e2e",
            "depends_on": [],
            "input": {
                "command": [
                    "python",
                    "scripts/qa/sports_real_mouse_smoke.py",
                    "--url",
                    "https://www.camel1.tv/",
                    "--x",
                    "230",
                    "--y",
                    "340",
                    "--out",
                    OUT + r"\sports-ui",
                ],
                "version": "prod-m6-ui-v1",
                "cwd": ROOT,
                "timeout_s": 180,
                "artifacts_dir": OUT + r"\sports-ui",
            },
            "assertions": [
                {
                    "assertion_key": "sports_ui_result",
                    "type": "jsonpath",
                    "oracle_layer": "STD",
                    "oracle_ref": "M6-SPORTS-UI",
                    "path": "$.result",
                    "expected": "PASS",
                }
            ],
        },
        {
            "key": "android_mqtt",
            "driver": "external_e2e",
            "depends_on": [],
            "input": {
                "command": [
                    "python",
                    "scripts/qa/android_mqtt_e2e.py",
                    "--out",
                    OUT,
                ],
                "version": "prod-m6-v1",
                "cwd": ROOT,
                "timeout_s": 300,
                "artifacts_dir": OUT,
            },
            "assertions": [
                {
                    "assertion_key": "android_mqtt_result",
                    "type": "jsonpath",
                    "oracle_layer": "STD",
                    "oracle_ref": "M6-ANDROID-MQTT",
                    "path": "$.result",
                    "expected": "PASS",
                }
            ],
        },
    ],
    "edges": [],
    "run_policy": {"max_parallel_nodes": 3, "fail_fast": False},
}

db = SessionLocal()
try:
    project_id = int(db.scalar(select(Project.id).order_by(Project.id)))
    for node_id, driver, caps, platforms in [
        ("prod-http-node", "http", ["aiqe:http", "api.http"], ["linux"]),
        (
            "prod-browser-node",
            "playwright",
            ["aiqe:playwright", "browser.chromium"],
            ["windows"],
        ),
        (
            "prod-external-node",
            "external_e2e",
            ["aiqe:external_e2e", "api.http", "device.android", "mqtt.client"],
            ["windows"],
        ),
    ]:
        register_manifest(
            db,
            node_id=node_id,
            driver_key=driver,
            driver_version="prod-m6",
            capabilities=caps,
            platforms=platforms,
            max_parallel_sessions=2,
            artifact_types=["screenshot", "report", "log"],
            evidence_ref=f"prod://{node_id}/m6",
        )
    workflow = create_workflow(
        db,
        project_id=project_id,
        graph=graph,
        scenario_id=None,
        validation_status="valid",
    )
    approve_workflow(db, workflow.id, approved_by=1)
    agent, token = register_agent(
        db,
        agent_id="prod-local-runner",
        project_scope=project_id,
        capabilities=[
            "api",
            "aiqe:http",
            "aiqe:playwright",
            "aiqe:appium",
            "aiqe:external_e2e",
        ],
    )
    db.commit()
    run = launch_run(
        db,
        project_id=project_id,
        user_id=1,
        workflow_definition_id=workflow.id,
        launch_key=f"prod-m6-{int(time.time())}",
        build_ref="prod-m6-integrated",
        commit_sha="3582a0696",
        source_type="manual",
    )
    db.commit()
    result = {
        "project_id": project_id,
        "workflow_id": workflow.id,
        "run_id": run.id,
        "run_status": run.status,
        "agent_id": agent.agent_id,
        "agent_scope": agent.project_scope,
        "agent_token": token,
        "out": OUT,
    }
    print(json.dumps(result, ensure_ascii=False))
finally:
    db.close()
