"""M3 / TA-025：Counterfactual Replay 单测。"""
from __future__ import annotations

import pytest

from app.aiqe.models.triage import TriageExperiment
from app.aiqe.services.triage_service import (
    EXPERIMENTS,
    ExperimentError,
    list_experiments,
    run_experiment,
)


def test_each_experiment_records_verification_run(db_session):
    for index, key in enumerate(EXPERIMENTS, start=1):
        row = run_experiment(
            db_session,
            experiment_key=key,
            change={"feature_flag": "ad_overlay"},
            idempotency_key=f"idem-{key}",
            triage_case_id="case-1",
        )
        assert row.experiment_key == key
        assert row.changed_variable == "feature_flag"
        assert row.verification_run_id and len(row.verification_run_id) == 36
        assert row.status == "completed"
    assert len(list_experiments(db_session, "case-1")) == len(EXPERIMENTS)


def test_double_variable_rejected(db_session):
    with pytest.raises(ExperimentError):
        run_experiment(
            db_session,
            experiment_key="E2",
            change={"a": 1, "b": 2},
            idempotency_key="idem-double",
        )
    assert db_session.query(TriageExperiment).count() == 0


def test_empty_change_rejected(db_session):
    with pytest.raises(ExperimentError):
        run_experiment(db_session, experiment_key="E1", change={}, idempotency_key="idem-empty")


def test_unknown_experiment_rejected(db_session):
    with pytest.raises(ExperimentError):
        run_experiment(
            db_session, experiment_key="E9", change={"x": 1}, idempotency_key="idem-e9"
        )


def test_idempotency_returns_same_record(db_session):
    first = run_experiment(
        db_session, experiment_key="E1", change={"replay": "same"}, idempotency_key="idem-same"
    )
    second = run_experiment(
        db_session, experiment_key="E1", change={"replay": "same"}, idempotency_key="idem-same"
    )
    assert first.id == second.id
    assert first.verification_run_id == second.verification_run_id
    assert db_session.query(TriageExperiment).count() == 1


def test_explicit_verification_run_preserved(db_session):
    row = run_experiment(
        db_session,
        experiment_key="E3",
        change={"profile": "core_isolated"},
        idempotency_key="idem-explicit",
        verification_run_id="run-verification-1",
    )
    assert row.verification_run_id == "run-verification-1"


def test_different_keys_create_two_rows(db_session):
    run_experiment(db_session, experiment_key="E4", change={"data": "reset"}, idempotency_key="k1")
    run_experiment(db_session, experiment_key="E5", change={"concurrency": "isolate"}, idempotency_key="k2")
    assert db_session.query(TriageExperiment).count() == 2
