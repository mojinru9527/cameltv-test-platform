"""v1.4 FIX-013：跨项目对象访问必须 403/404（不泄露存在性）。"""
from __future__ import annotations

import pytest

from app.aiqe.services import learning_service, noise_rule_service


def test_noise_rule_cross_project_read_update_delete_blocked(db_session):
    row = noise_rule_service.create_rule(
        db_session, project_id=1, pattern="已知噪音", action="hint"
    )
    with pytest.raises(noise_rule_service.NoiseRuleError):
        noise_rule_service.update_rule(
            db_session, row.id, pattern="x", project_id=2
        )
    with pytest.raises(noise_rule_service.NoiseRuleError):
        noise_rule_service.renew_rule(db_session, row.id, project_id=2)
    with pytest.raises(noise_rule_service.NoiseRuleError):
        noise_rule_service.delete_rule(db_session, row.id, project_id=2)
    assert noise_rule_service.get_rule(db_session, row.id, project_id=1)


def test_learning_candidate_cross_project_blocked(db_session):
    row = learning_service.create_candidate(
        db_session, project_id=1, rule={"pattern": "flaky-network"}
    )
    with pytest.raises(learning_service.LearningError):
        learning_service.get_candidate(db_session, row.id, project_id=2)
    with pytest.raises(learning_service.LearningError):
        learning_service.evaluate_candidate(
            db_session,
            row.id,
            {"false_positive_rate": 0.1, "sample_size": 10},
            project_id=2,
        )
    with pytest.raises(learning_service.LearningError):
        learning_service.approve_candidate(db_session, row.id, project_id=2)
    with pytest.raises(learning_service.LearningError):
        learning_service.activate_candidate(db_session, row.id, project_id=2)


def test_artifact_download_cross_project_denied(db_session, tmp_path, monkeypatch):
    from app.aiqe.models.run import TestRun
    from app.aiqe.services import artifact_service

    run = TestRun(project_id=1, run_key="RUN-ART-SCOPE", source_type="manual", status="COMPLETED")
    db_session.add(run)
    db_session.flush()
    row = artifact_service.put_artifact(
        db_session,
        project_id=1,
        run_id=run.id,
        content=b"hello",
        artifact_type="log",
        redaction_status="sanitized",
    )
    with pytest.raises(artifact_service.ArtifactAccessDenied):
        artifact_service.get_artifact(db_session, row.id, project_id=2)
    with pytest.raises(artifact_service.ArtifactAccessDenied):
        artifact_service.read_artifact(db_session, row.id, project_id=2)
