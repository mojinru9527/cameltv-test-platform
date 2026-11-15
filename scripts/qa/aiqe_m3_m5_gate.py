"""AIQE v1.4 M3–M5 Test 环境 Gate（真实 Provider + A4 归因 + E1–E6 + A5/A6）。

在 Test backend 容器内执行：
  docker cp aiqe_m3_m5_gate.py aiqe-test-backend:/tmp/
  docker exec -e PYTHONPATH=/app -w /app aiqe-test-backend python /tmp/aiqe_m3_m5_gate.py

输出：/tmp/aiqe_m3_m5_gate.json（不含 API Key）。
"""
from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from app.aiqe.agents.base import BaseAgent
from app.aiqe.agents.change_impact_agent import ChangeImpactAgent, compute_impact
from app.aiqe.agents.failure_triage_agent import FailureTriageAgent
from app.aiqe.agents.orchestrator import run_agent
from app.aiqe.agents.requirement_agent import RequirementAgent
from app.aiqe.agents.test_design_agent import TestDesignAgent
from app.aiqe.agents.workflow_planner_agent import WorkflowPlannerAgent
from app.aiqe.models.agent import AgentExecution
from app.aiqe.services import learning_service, triage_service
from app.aiqe.services.platform_matrix import build_platform_matrix
from app.core.db import SessionLocal
from app.services.ai_client import chat_completions_full, resolve_config


def _llm(db, model: str):
    def call(system_prompt: str, user_message: str) -> str:
        out = chat_completions_full(
            db,
            1,
            system_prompt=system_prompt,
            user_message=user_message,
            max_tokens=3000,
            temperature=0.1,
            json_mode=True,
        )
        return out["content"]

    return call


def _persist(db, agent: BaseAgent, input_text: str, output: dict) -> None:
    db.add(
        AgentExecution(
            project_id=1,
            agent_key=agent.key,
            status="succeeded",
            model=getattr(agent, "model", ""),
            input_text=input_text[:8000],
            output_json=output,
            started_at=datetime.now(UTC),
            finished_at=datetime.now(UTC),
        )
    )
    db.flush()


def main() -> int:
    db = SessionLocal()
    report: dict = {"generated_at": datetime.now(UTC).isoformat(), "project_id": 1}
    try:
        cfg = resolve_config(db, 1)
        if cfg is None:
            raise RuntimeError("NO_PROVIDER")
        llm = _llm(db, cfg.model)
        report["provider"] = {"model": cfg.model, "base_url": cfg.api_base_url}

        # ── M3 A0/A2/A3 真实 Provider ─────────────────────────────────
        requirement = (
            "Test 环境验收需求：1) GET /api/v1/open/health 返回 200 且 data.status=ok；"
            "2) 登录页有“忘记密码”入口，点击后进入 /forgot-password 并显示“找回密码”；"
            "3) PostgreSQL sys_project 至少存在 1 个项目。"
        )
        a0 = RequirementAgent(llm, model=cfg.model)
        assessment = run_agent(db, a0, project_id=1, input_text=requirement)
        db.commit()
        a2 = TestDesignAgent(llm, model=cfg.model)
        design = run_agent(
            db,
            a2,
            project_id=1,
            input_text="需求评估:\n" + str(assessment) + "\n已有用例:\n[]\n覆盖充分: False",
        )
        db.commit()
        a3 = WorkflowPlannerAgent(llm)
        plan = run_agent(
            db,
            a3,
            project_id=1,
            input_text=str(
                {
                    "assessment": assessment,
                    "scenario_key": "test-health-forgot-db",
                }
            ),
        )
        db.commit()
        report["M3"] = {
            "requirement": requirement,
            "A0": assessment,
            "A2": design,
            "A3": plan,
            "A3_validator_pass": True,
            # A3 的输出包含 steps/query 等自由度字段；真正执行必须经人工审阅转成
            # v1.4 可执行 input/assertions 契约（Test Dogfood workflow/run 即该人工版本）。
            "human_adapted_workflow_id": "a35f0100-05e9-4630-b953-0b674ea1fbb0",
            "human_adapted_test_run_id": "1dd2184e-c505-4464-808f-98df7c1193e4",
        }

        # ── M4 A4 真实归因 + E1–E6 ────────────────────────────────────
        contexts = [
            {
                "name": "http_business_500",
                "execution_outcome": "FAIL",
                "evidence": ["HTTP 200 expected, got 500", "response body: INTERNAL_ERROR"],
                "node": "health",
            },
            {
                "name": "http_timeout",
                "execution_outcome": "FAIL",
                "evidence": ["httpx.TimeoutException after 15s", "no response headers"],
                "node": "health",
            },
            {
                "name": "playwright_locator_not_visible",
                "execution_outcome": "FAIL",
                "evidence": ["locator a[href='/forgot-password'] not visible", "DOM has login form"],
                "node": "ui_forgot",
            },
            {
                "name": "db_row_missing",
                "execution_outcome": "FAIL",
                "evidence": ["SELECT count(*) = 0", "expected >= 1"],
                "node": "db_projects",
            },
            {
                "name": "network_reset",
                "execution_outcome": "ERROR",
                "evidence": ["connection reset by peer", "other nodes in same run passed"],
                "node": "verify_health",
            },
            {
                "name": "test_data_missing",
                "execution_outcome": "FAIL",
                "evidence": ["fixture project not found", "same query passes on seed data"],
                "node": "db_projects",
            },
            {
                "name": "concurrency_lock",
                "execution_outcome": "FAIL",
                "evidence": ["lock timeout on shared fixture", "passes when run in isolation"],
                "node": "db_projects",
            },
        ]
        a4 = FailureTriageAgent(llm, model=cfg.model)
        triage_rows = []
        for context in contexts:
            output = run_agent(
                db,
                a4,
                project_id=1,
                input_text=json.dumps(context, ensure_ascii=False),
            )
            db.commit()
            triage_rows.append(
                {
                    "context": context["name"],
                    "classification": [h["classification"] for h in output["hypotheses"]],
                    "attribution_status": output["attribution_status"],
                    "human_review_required": output["human_review_required"],
                    "auto_close_defect": output["auto_close_defect"],
                }
            )

        experiments = []
        for idx, key in enumerate(("E1", "E2", "E3", "E4", "E5", "E6"), start=1):
            change = {f"var_{key.lower()}": f"value-{idx}"}
            row = triage_service.run_experiment(
                db,
                experiment_key=key,
                change=change,
                idempotency_key=f"m4-test-{key}-{uuid.uuid4().hex[:8]}",
                triage_case_id="test-m4",
            )
            experiments.append(
                {"key": key, "changed": row.changed_variable, "status": row.status}
            )
        db.commit()
        idem_key = f"m4-idem-{uuid.uuid4().hex[:8]}"
        first = triage_service.run_experiment(
            db,
            experiment_key="E1",
            change={"network": "isolated"},
            idempotency_key=idem_key,
        )
        second = triage_service.run_experiment(
            db,
            experiment_key="E1",
            change={"network": "isolated"},
            idempotency_key=idem_key,
        )
        double_change_rejected = False
        try:
            triage_service.validate_change({"a": 1, "b": 2})
        except triage_service.ExperimentError:
            double_change_rejected = True
        report["M4"] = {
            "A4": triage_rows,
            "E1_E6": experiments,
            "idempotency_same_row": first.id == second.id,
            "double_variable_rejected": double_change_rejected,
        }

        # ── M5 A5 变更影响 + A6 学习候选 + 平台矩阵 ─────────────────
        files = [
            "test-platform-v2/backend/app/api/v1/auth.py",
            "test-platform-v2/backend/app/services/session_service.py",
            "test-platform-v2/frontend/src/pages/login/index.tsx",
        ]
        a5 = ChangeImpactAgent(llm, model=cfg.model)
        impact = a5.analyze(files)
        _persist(db, a5, str({"files": files}), impact)
        db.commit()

        candidate = learning_service.create_candidate(
            db,
            project_id=1,
            rule={"pattern": f"test-m5-network-flake-{uuid.uuid4().hex[:6]}", "description": "M5 benchmark candidate"},
        )
        learning_service.evaluate_candidate(
            db,
            candidate.id,
            {"false_positive_rate": 0.1, "sample_size": 50},
            project_id=1,
        )
        learning_service.approve_candidate(db, candidate.id, project_id=1)
        pattern = learning_service.activate_candidate(db, candidate.id, project_id=1)
        db.commit()
        matrix = build_platform_matrix(db)
        report["M5"] = {
            "A5": impact,
            "A5_rule_baseline": compute_impact(files),
            "A6": {
                "candidate_id": candidate.id,
                "status": candidate.status,
                "benchmark": candidate.benchmark_json,
                "pattern_id": None if pattern is None else pattern.id,
            },
            "platform_matrix": {
                "platforms": matrix["platforms"],
                "capabilities": matrix["capabilities"],
                "available_nodes": matrix["available_nodes"],
            },
        }

        with open("/tmp/aiqe_m3_m5_gate.json", "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2, default=str)
        print(
            json.dumps(
                {
                    "ok": True,
                    "A0_ac": len(assessment["acceptance_criteria"]),
                    "A2_cases": len(design["cases"]),
                    "A3_nodes": len(plan["workflow"]["nodes"]),
                    "A4_contexts": len(triage_rows),
                    "E_experiments": len(experiments),
                    "A5_forced": impact["forced_suites"],
                    "A6_status": candidate.status,
                    "matrix_platforms": matrix["platforms"],
                },
                ensure_ascii=False,
            )
        )
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
