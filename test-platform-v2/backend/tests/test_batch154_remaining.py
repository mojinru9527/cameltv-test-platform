"""Batch 154 四项收口回归：数据集绑定 / 图谱治理 / UI 映射 / 级联清理。"""
from __future__ import annotations

from app.models.knowledge import KnowledgeEntity, KnowledgeSource
from app.models.test_case import TestCase as _TestCase
from app.models.ui_test import UiTestJob, UiTestRun
from app.services.knowledge.entity_service import backfill_missing_source, evolve_graph_in_new_session
from app.services.ui_test_service import list_jobs, writeback_case_result


def _create_case(client, auth_headers, *, title="B154TMP-用例", case_type="manual", dataset_id=None):
    body = {"title": title, "case_type": case_type}
    if dataset_id is not None:
        body["dataset_id"] = dataset_id
    resp = client.post("/api/v1/test-cases", json=body, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


class TestDatasetBinding:
    """C147-8：接口用例默认数据集绑定 + 执行兜底。"""

    def test_case_dataset_id_roundtrip(self, client, auth_headers):
        case = _create_case(client, auth_headers, case_type="api", dataset_id=None)
        assert case["dataset_id"] is None

        data = client.post("/api/v1/datasets", json={
            "name": "B154TMP-数据集",
            "source_type": "csv",
            "raw_content": "name,value\nfoo,1\nbar,2",
        }, headers=auth_headers).json()
        dataset_id = data["data"]["dataset"]["id"]

        updated = client.put(
            f"/api/v1/test-cases/{case['id']}",
            json={"dataset_id": dataset_id},
            headers=auth_headers,
        ).json()["data"]
        assert updated["dataset_id"] == dataset_id

    def test_execute_uses_case_default_dataset(self, db_session, client, auth_headers):
        """未显式传 dataset_id 时使用用例默认绑定 → batch_mode 生效。"""
        from app.services.api_execution_service import execute_api_case

        data = client.post("/api/v1/datasets", json={
            "name": "B154TMP-数据集2",
            "source_type": "csv",
            "raw_content": "name,value\nfoo,1",
        }, headers=auth_headers).json()
        dataset_id = data["data"]["dataset"]["id"]

        case = _create_case(client, auth_headers, case_type="api", dataset_id=dataset_id)
        result = execute_api_case(
            db_session, case["id"], project_id=1, environment_id=None, dataset_id=None,
        )
        assert result.get("batch_mode") is True


class TestKnowledgeGovernance:
    """C147-9：缺失来源回填 / evolve 加固 / 删除级联。"""

    def test_backfill_missing_source_by_case_title(self, db_session, client, auth_headers):
        case = _create_case(client, auth_headers, title="B154TMP-实体源用例")
        ent = KnowledgeEntity(
            project_id=1, entity_type="test_case", entity_key="tc:p1:B154TMP-实体源用例",
            name="B154TMP-实体源用例", source_id=None,
        )
        db_session.add(ent)
        db_session.flush()

        result = backfill_missing_source(db_session, 1)
        assert result["updated"] >= 1
        db_session.refresh(ent)
        assert ent.source_id == case["id"]
        assert ent.source_ref == f"test_case:{case['id']}"

    def test_evolve_guarded(self, db_session):
        ent = KnowledgeEntity(
            project_id=1, entity_type="api", entity_key="api:p1:GET /x",
            name="GET /x", source_id=None, confidence=0.8,
        )
        db_session.add(ent)
        db_session.flush()
        db_session.commit()

        result = evolve_graph_in_new_session(1, db=db_session)
        assert "error" not in result or not result.get("error")

    def test_defect_delete_deprecates_knowledge_source(self, db_session, client, auth_headers):
        defect = client.post("/api/v1/defects", json={
            "title": "B154TMP-级联缺陷",
        }, headers=auth_headers).json()["data"]

        src = KnowledgeSource(
            project_id=1, source_type="defect", source_id=defect["id"],
            title="B154TMP-知识源", status="indexed",
        )
        db_session.add(src)
        db_session.flush()

        client.delete(f"/api/v1/defects/{defect['id']}", headers=auth_headers)
        db_session.expire_all()
        # Batch 177（FIX-173-P1-04）：业务删除级联由「标记 deprecated」升级为硬删，
        # 知识源不再残留（此前删除缺陷后切片仍在知识中心可见）。
        refreshed = db_session.get(KnowledgeSource, src.id)
        assert refreshed is None


class TestUiJobCaseMapping:
    """C151-1：UI 任务↔用例映射 + 回写 + 批量创建。"""

    def test_job_case_mapping_and_title(self, db_session, client, auth_headers):
        case = _create_case(client, auth_headers, case_type="ui", title="B154TMP-UI用例")
        resp = client.post("/api/v1/ui-tests", json={
            "name": "B154TMP-UI任务", "case_id": case["id"],
        }, headers=auth_headers)
        assert resp.status_code == 200, resp.text
        job = resp.json()["data"]
        assert job["case_id"] == case["id"]

        items, _ = list_jobs(db_session, project_id=1)
        mine = next(i for i in items if i["id"] == job["id"])
        assert mine["case_title"] == "B154TMP-UI用例"

    def test_run_writeback(self, db_session):
        case = _TestCase(project_id=1, title="B154TMP-回写用例", case_type="ui")
        db_session.add(case)
        db_session.flush()
        job = UiTestJob(project_id=1, name="B154TMP-回写任务", case_id=case.id)
        db_session.add(job)
        db_session.flush()
        run = UiTestRun(job_id=job.id, status="passed", result='{"pass_":2,"fail":0}')
        db_session.add(run)
        db_session.flush()

        writeback_case_result(db_session, job, run)
        db_session.flush()
        db_session.refresh(case)
        assert case.last_run_status == "passed"
        assert "ui_run_id" in case.last_response_json

    def test_create_jobs_from_cases(self, client, auth_headers):
        case = _create_case(client, auth_headers, case_type="ui", title="B154TMP-批量UI")
        resp = client.post("/api/v1/ui-tests/jobs/from-cases", json={
            "case_ids": [case["id"]],
        }, headers=auth_headers)
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["created"] == 1
