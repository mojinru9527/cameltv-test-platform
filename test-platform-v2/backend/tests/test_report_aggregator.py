"""Unit tests for report_aggregator service — uses db_session fixture."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.services.report_aggregator import get_aggregated_summary


# ═══════════════════════════════════════════════════════════
# Structure
# ═══════════════════════════════════════════════════════════

class TestAggregatedSummaryStructure:
    def test_has_expected_keys(self, db_session):
        summary = get_aggregated_summary(db_session, project_id=1, days=7)
        assert "api" in summary
        assert "ui" in summary
        assert "combined" in summary
        assert "period_days" in summary
        assert "generated_at" in summary
        assert summary["period_days"] == 7

    def test_api_sub_keys(self, db_session):
        summary = get_aggregated_summary(db_session, project_id=1)
        api = summary["api"]
        for key in ("total_tasks", "total_passed", "total_failed",
                     "pass_rate", "error_categories", "recent_trend"):
            assert key in api, f"Missing key in api summary: {key}"

    def test_ui_sub_keys(self, db_session):
        summary = get_aggregated_summary(db_session, project_id=1)
        ui = summary["ui"]
        for key in ("total_runs", "total_passed", "total_failed",
                     "pass_rate", "error_categories", "recent_trend"):
            assert key in ui, f"Missing key in ui summary: {key}"

    def test_combined_sub_keys(self, db_session):
        summary = get_aggregated_summary(db_session, project_id=1)
        combined = summary["combined"]
        for key in ("total_runs", "total_passed", "total_failed", "pass_rate"):
            assert key in combined, f"Missing key in combined: {key}"


# ═══════════════════════════════════════════════════════════
# Empty database
# ═══════════════════════════════════════════════════════════

class TestAggregatedSummaryEmptyDb:
    def test_all_zeros_on_empty_db(self, db_session):
        summary = get_aggregated_summary(db_session, project_id=1)
        assert summary["api"]["total_tasks"] == 0
        assert summary["api"]["total_passed"] == 0
        assert summary["api"]["total_failed"] == 0
        assert summary["ui"]["total_runs"] == 0
        assert summary["ui"]["total_passed"] == 0
        assert summary["ui"]["total_failed"] == 0
        assert summary["combined"]["total_runs"] == 0
        assert summary["combined"]["pass_rate"] == 0.0

    def test_pass_rate_zero_division_safe(self, db_session):
        """pass_rate should be 0.0 not NaN when no data.  max(..., 1) guards. """
        summary = get_aggregated_summary(db_session, project_id=1)
        assert summary["api"]["pass_rate"] == 0.0
        assert summary["ui"]["pass_rate"] == 0.0
        assert summary["combined"]["pass_rate"] == 0.0

    def test_error_categories_empty_dict(self, db_session):
        summary = get_aggregated_summary(db_session, project_id=1)
        assert summary["api"]["error_categories"] == {}
        assert summary["ui"]["error_categories"] == {}

    def test_recent_trend_empty_list(self, db_session):
        summary = get_aggregated_summary(db_session, project_id=1)
        assert summary["api"]["recent_trend"] == []
        assert summary["ui"]["recent_trend"] == []


# ═══════════════════════════════════════════════════════════
# API summary with data
# ═══════════════════════════════════════════════════════════

class TestApiSummaryWithData:
    def test_correct_pass_fail_counts(self, db_session):
        from app.models.api_asset import ApiExecutionTask

        now = datetime.now(timezone.utc)
        t1 = ApiExecutionTask(
            project_id=1, task_id="T-1", name="Task 1",
            total=5, passed=5, failed=0, status="success",
            created_at=now,
        )
        t2 = ApiExecutionTask(
            project_id=1, task_id="T-2", name="Task 2",
            total=3, passed=2, failed=1, status="failed",
            created_at=now,
        )
        db_session.add_all([t1, t2])
        db_session.commit()

        summary = get_aggregated_summary(db_session, project_id=1, days=7)
        api = summary["api"]
        assert api["total_tasks"] == 2
        assert api["total_passed"] == 7  # 5+2
        assert api["total_failed"] == 1  # 0+1
        assert api["pass_rate"] == round(7 / 8 * 100, 1)

    def test_old_records_excluded(self, db_session):
        from app.models.api_asset import ApiExecutionTask

        now = datetime.now(timezone.utc)
        old = ApiExecutionTask(
            project_id=1, task_id="T-OLD", name="Old",
            total=1, passed=1, failed=0, status="success",
            created_at=now - timedelta(days=30),
        )
        recent = ApiExecutionTask(
            project_id=1, task_id="T-NEW", name="New",
            total=1, passed=0, failed=1, status="failed",
            created_at=now,
        )
        db_session.add_all([old, recent])
        db_session.commit()

        summary = get_aggregated_summary(db_session, project_id=1, days=7)
        assert summary["api"]["total_tasks"] == 1
        assert summary["api"]["total_passed"] == 0
        assert summary["api"]["total_failed"] == 1

    def test_project_isolation(self, db_session):
        from app.models.api_asset import ApiExecutionTask

        now = datetime.now(timezone.utc)
        p1 = ApiExecutionTask(
            project_id=1, task_id="T-P1", name="P1",
            total=1, passed=1, failed=0, status="success",
            created_at=now,
        )
        p2 = ApiExecutionTask(
            project_id=2, task_id="T-P2", name="P2",
            total=3, passed=3, failed=0, status="success",
            created_at=now,
        )
        db_session.add_all([p1, p2])
        db_session.commit()

        summary = get_aggregated_summary(db_session, project_id=1, days=7)
        assert summary["api"]["total_tasks"] == 1
        assert summary["api"]["total_passed"] == 1

    def test_different_periods(self, db_session):
        from app.models.api_asset import ApiExecutionTask

        now = datetime.now(timezone.utc)
        t = ApiExecutionTask(
            project_id=1, task_id="T-DAYS", name="Days",
            total=1, passed=1, failed=0, status="success",
            created_at=now - timedelta(days=15),
        )
        db_session.add(t)
        db_session.commit()

        s30 = get_aggregated_summary(db_session, project_id=1, days=30)
        assert s30["api"]["total_tasks"] == 1

        s7 = get_aggregated_summary(db_session, project_id=1, days=7)
        assert s7["api"]["total_tasks"] == 0

    def test_api_passed_failed_handle_none(self, db_session):
        """Tasks with None passed/failed should count as 0."""
        from app.models.api_asset import ApiExecutionTask

        now = datetime.now(timezone.utc)
        t = ApiExecutionTask(
            project_id=1, task_id="T-NONE", name="No Counts",
            total=1, status="pending",  # passed/failed default to 0
            created_at=now,
        )
        db_session.add(t)
        db_session.commit()

        summary = get_aggregated_summary(db_session, project_id=1, days=7)
        api = summary["api"]
        assert api["total_tasks"] == 1
        assert api["total_passed"] == 0
        assert api["total_failed"] == 0

    def test_error_categories_grouped(self, db_session):
        from app.models.api_asset import ApiExecutionTask, ApiExecutionTaskItem

        now = datetime.now(timezone.utc)
        task = ApiExecutionTask(
            project_id=1, task_id="T-CAT", name="Cat Test",
            total=3, passed=0, failed=3, status="failed",
            created_at=now,
        )
        db_session.add(task)
        db_session.flush()

        item1 = ApiExecutionTaskItem(
            task_id=task.id, case_id=1, status="failed",
            error_message="请求超时",
        )
        item2 = ApiExecutionTaskItem(
            task_id=task.id, case_id=2, status="failed",
            error_message="Connection refused",
        )
        item3 = ApiExecutionTaskItem(
            task_id=task.id, case_id=3, status="failed",
            error_message="断言失败：Expected 200 got 500",
        )
        db_session.add_all([item1, item2, item3])
        db_session.commit()

        summary = get_aggregated_summary(db_session, project_id=1, days=7)
        cats = summary["api"]["error_categories"]
        assert "timeout" in cats
        assert "connection" in cats
        assert "assertion" in cats
        assert cats["timeout"] == 1
        assert cats["connection"] == 1
        assert cats["assertion"] == 1


# ═══════════════════════════════════════════════════════════
# UI summary with data
# ═══════════════════════════════════════════════════════════

class TestUiSummaryWithData:
    def test_correct_pass_fail_counts(self, db_session):
        from app.models.ui_test import UiTestJob, UiTestRun

        now = datetime.now(timezone.utc)
        job = UiTestJob(
            project_id=1, name="UI Job", status="done",
            created_at=now,
        )
        db_session.add(job)
        db_session.flush()

        run1 = UiTestRun(
            job_id=job.id, status="done",
            result='{"total":10,"pass_":8,"fail":2}',
            started_at=now,
        )
        run2 = UiTestRun(
            job_id=job.id, status="done",
            result='{"total":5,"pass_":4,"fail":1}',
            started_at=now,
        )
        db_session.add_all([run1, run2])
        db_session.commit()

        summary = get_aggregated_summary(db_session, project_id=1, days=7)
        ui = summary["ui"]
        assert ui["total_runs"] == 2
        assert ui["total_passed"] == 12  # 8+4
        assert ui["total_failed"] == 3   # 2+1

    def test_old_runs_excluded(self, db_session):
        from app.models.ui_test import UiTestJob, UiTestRun

        now = datetime.now(timezone.utc)
        job = UiTestJob(project_id=1, name="UI Job", status="done", created_at=now)
        db_session.add(job)
        db_session.flush()

        old_run = UiTestRun(
            job_id=job.id, status="done",
            result='{"total":1,"pass_":1,"fail":0}',
            started_at=now - timedelta(days=14),
        )
        recent_run = UiTestRun(
            job_id=job.id, status="done",
            result='{"total":1,"pass_":0,"fail":1}',
            started_at=now,
        )
        db_session.add_all([old_run, recent_run])
        db_session.commit()

        summary = get_aggregated_summary(db_session, project_id=1, days=7)
        assert summary["ui"]["total_runs"] == 1

    def test_ui_project_isolation(self, db_session):
        from app.models.ui_test import UiTestJob

        now = datetime.now(timezone.utc)
        j1 = UiTestJob(project_id=1, name="J1", status="done", created_at=now)
        j2 = UiTestJob(project_id=2, name="J2", status="done", created_at=now)
        db_session.add_all([j1, j2])
        db_session.commit()

        summary = get_aggregated_summary(db_session, project_id=1, days=7)
        # No runs, but project isolation means only p1 jobs exist
        assert summary["ui"]["total_runs"] == 0
        # project 1 should have 0 jobs for p2
        s2 = get_aggregated_summary(db_session, project_id=2, days=7)
        assert s2["ui"]["total_runs"] == 0

    def test_ui_error_categories(self, db_session):
        from app.models.ui_test import UiTestJob, UiTestRun

        now = datetime.now(timezone.utc)
        job = UiTestJob(project_id=1, name="UI Job", status="fail", created_at=now)
        db_session.add(job)
        db_session.flush()

        r1 = UiTestRun(
            job_id=job.id, status="fail",
            error_message="Playwright 不可用",
            started_at=now,
        )
        r2 = UiTestRun(
            job_id=job.id, status="fail",
            error_message="npx: command not found",
            started_at=now,
        )
        db_session.add_all([r1, r2])
        db_session.commit()

        summary = get_aggregated_summary(db_session, project_id=1, days=7)
        cats = summary["ui"]["error_categories"]
        assert "playwright_unavailable" in cats
        assert "npx_missing" in cats
        assert cats["playwright_unavailable"] >= 1
        assert cats["npx_missing"] >= 1

    def test_ui_runs_with_invalid_result_json(self, db_session):
        from app.models.ui_test import UiTestJob, UiTestRun

        now = datetime.now(timezone.utc)
        job = UiTestJob(project_id=1, name="UI Job", status="done", created_at=now)
        db_session.add(job)
        db_session.flush()

        run = UiTestRun(
            job_id=job.id, status="done",
            result="not valid json {{{",
            started_at=now,
        )
        db_session.add(run)
        db_session.commit()

        summary = get_aggregated_summary(db_session, project_id=1, days=7)
        assert summary["ui"]["total_runs"] == 1
        # Should not crash; empty dict fallback gives 0/0
        assert summary["ui"]["total_passed"] == 0
        assert summary["ui"]["total_failed"] == 0

    def test_ui_empty_result(self, db_session):
        from app.models.ui_test import UiTestJob, UiTestRun

        now = datetime.now(timezone.utc)
        job = UiTestJob(project_id=1, name="UI Job", status="done", created_at=now)
        db_session.add(job)
        db_session.flush()

        run = UiTestRun(job_id=job.id, status="done", result="{}", started_at=now)
        db_session.add(run)
        db_session.commit()

        summary = get_aggregated_summary(db_session, project_id=1, days=7)
        assert summary["ui"]["total_passed"] == 0
        assert summary["ui"]["total_failed"] == 0

    def test_jobs_without_runs(self, db_session):
        """Jobs with no runs should not affect ui summary."""
        from app.models.ui_test import UiTestJob

        now = datetime.now(timezone.utc)
        job = UiTestJob(project_id=1, name="Empty Job", status="idle", created_at=now)
        db_session.add(job)
        db_session.commit()

        summary = get_aggregated_summary(db_session, project_id=1, days=7)
        assert summary["ui"]["total_runs"] == 0


# ═══════════════════════════════════════════════════════════
# Combined
# ═══════════════════════════════════════════════════════════

class TestCombinedSummary:
    def test_combined_sums_correctly(self, db_session):
        from app.models.api_asset import ApiExecutionTask
        from app.models.ui_test import UiTestJob, UiTestRun

        now = datetime.now(timezone.utc)

        # API
        t = ApiExecutionTask(
            project_id=1, task_id="T-API", name="API",
            total=2, passed=1, failed=1, status="failed",
            created_at=now,
        )
        db_session.add(t)

        # UI
        job = UiTestJob(project_id=1, name="UI Job", status="done", created_at=now)
        db_session.add(job)
        db_session.flush()
        run = UiTestRun(
            job_id=job.id, status="done",
            result='{"total":3,"pass_":2,"fail":1}',
            started_at=now,
        )
        db_session.add(run)
        db_session.commit()

        summary = get_aggregated_summary(db_session, project_id=1, days=7)
        c = summary["combined"]
        # API: 1 task + UI: 1 run = 2 total
        assert c["total_runs"] == 2
        # API passed=1 + UI passed=2 = 3
        assert c["total_passed"] == 3
        # API failed=1 + UI failed=1 = 2
        assert c["total_failed"] == 2
        # 3 / (3+2) * 100 = 60.0
        assert c["pass_rate"] == 60.0
