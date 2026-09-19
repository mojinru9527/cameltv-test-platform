"""Batch 261 / B4-2 — 试点数据集选择与基线快照。

DoD（backlog B4-2）：资产导入完成、环境指纹可复现。
本机库无体育资产（C261-1），因此这里验证的是**选择器与基线的机制**：
选得对、够不够如实报、指纹可复现，且**快照里绝不出现被测系统凭据**。
"""
from __future__ import annotations

import json

import pytest

from app.core.exceptions import APIException
from app.models.test_case import TestCase
from app.services import pilot_dataset_service as pds


def _case(db, project_id: int, *, case_type: str, priority: str, module: str = "体育") -> TestCase:
    case = TestCase(
        project_id=project_id,
        title=f"{module}-{case_type}-{priority}",
        module=module,
        case_type=case_type,
        priority=priority,
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


class TestSelection:
    def test_selects_up_to_targets_and_prefers_p0(self, db_session):
        for index in range(5):
            _case(db_session, 1, case_type="api", priority="P2")
        p0 = _case(db_session, 1, case_type="api", priority="P0")
        for index in range(3):
            _case(db_session, 1, case_type="ui", priority="P1")

        result = pds.select_pilot_cases(db_session, project_id=1, api_limit=2, web_limit=1)

        assert result["counts"] == {"api": 2, "web": 1}
        # P0 优先入选
        assert result["api"][0]["id"] == p0.id
        assert result["api"][0]["priority"] == "P0"

    def test_shortfall_is_reported_not_padded(self, db_session):
        _case(db_session, 1, case_type="api", priority="P0")
        result = pds.select_pilot_cases(db_session, project_id=1)  # 默认目标 50/30
        assert result["counts"] == {"api": 1, "web": 0}
        assert result["shortfall"] == {"api": 49, "web": 30}
        assert result["meets_target"] is False

    def test_selection_is_deterministic(self, db_session):
        for index in range(6):
            _case(db_session, 1, case_type="api", priority="P1")
        first = pds.select_pilot_cases(db_session, project_id=1, api_limit=3)
        second = pds.select_pilot_cases(db_session, project_id=1, api_limit=3)
        assert [c["id"] for c in first["api"]] == [c["id"] for c in second["api"]]

    def test_module_prefix_filters(self, db_session):
        _case(db_session, 1, case_type="api", priority="P0", module="体育直播")
        _case(db_session, 1, case_type="api", priority="P0", module="资讯")
        result = pds.select_pilot_cases(db_session, project_id=1, module_prefix="体育")
        assert [c["module"] for c in result["api"]] == ["体育直播"]

    def test_project_isolation(self, db_session):
        _case(db_session, 2, case_type="api", priority="P0")
        assert pds.select_pilot_cases(db_session, project_id=1)["counts"]["api"] == 0


class TestBaseline:
    def test_baseline_carries_fingerprint_and_slot_reference(self, db_session):
        _case(db_session, 1, case_type="api", priority="P0")
        baseline = pds.build_baseline(
            db_session,
            project_id=1,
            environment_id=9,
            account_slot="sports-tester-01",
            components={"openapi_hash": "abc", "frontend_version": "16.1.0"},
        )
        assert baseline["environment"]["environment_id"] == 9
        assert len(baseline["environment"]["fingerprint_hash"]) == 64
        assert baseline["account_slot"] == {
            "name": "sports-tester-01",
            "credentials_in_baseline": False,
        }
        assert baseline["dataset"]["counts"]["api"] == 1

    def test_fingerprint_is_reproducible_and_component_sensitive(self, db_session):
        """DoD「环境指纹可复现」：同因子同哈希，因子变了哈希必变。"""
        same_a = pds.build_baseline(
            db_session, project_id=1, environment_id=9, components={"openapi_hash": "abc"}
        )
        same_b = pds.build_baseline(
            db_session, project_id=1, environment_id=9, components={"openapi_hash": "abc"}
        )
        changed = pds.build_baseline(
            db_session, project_id=1, environment_id=9, components={"openapi_hash": "xyz"}
        )
        assert same_a["environment"]["fingerprint_hash"] == same_b["environment"]["fingerprint_hash"]
        assert same_a["environment"]["fingerprint_hash"] != changed["environment"]["fingerprint_hash"]

    def test_baseline_never_contains_credentials(self, db_session):
        """硬约束 H3：控制面不存被测系统凭据——快照里连影子都不能有。"""
        baseline = pds.build_baseline(
            db_session,
            project_id=1,
            environment_id=9,
            account_slot="sports-tester-01",
            components={"openapi_hash": "abc"},
        )
        blob = json.dumps(baseline, ensure_ascii=False).lower()
        for forbidden in ("password", "token", "secret", "cookie", "authorization", "api_key"):
            assert forbidden not in blob, f"基线快照疑似包含凭据字段: {forbidden}"

    def test_environment_id_is_required(self, db_session):
        with pytest.raises(APIException):
            pds.build_baseline(db_session, project_id=1, environment_id=0)
