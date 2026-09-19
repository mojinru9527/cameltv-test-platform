"""Batch 261 / B4-3/4/5 — 试点 SLO 判定与前置检查（纯函数，可单测）。

真正跑 3 个版本需要环境（C261-1），但"什么算达标"必须在这里先被验证：
否则等环境到位时才第一次运行判定逻辑，等于把验收标准的正确性押在环境上。
"""
from __future__ import annotations

from app.services import pilot_slo_service as slo


def _version(name: str, *, person=1.5, execution=2.0, complete=True, used=3, total=5) -> dict:
    return {
        "version": name,
        "person_hours": person,
        "execution_hours": execution,
        "evidence_complete": complete,
        "reuse_suggested": total,
        "reuse_adopted": used,
    }


class TestSloMath:
    def test_three_passing_versions_meet_slo(self):
        result = slo.compute_slo([_version("16.1.0"), _version("16.2.0"), _version("16.3.0")])
        assert result["consecutive_passing"] == 3
        assert result["meets_all"] is True
        assert result["overall_reuse_hit_rate"] == 0.6

    def test_slow_plan_fails_that_version(self):
        slow = _version("16.1.0", person=3.5)  # > 2h
        result = slo.compute_slo([slow, _version("16.2.0"), _version("16.3.0")])
        assert result["versions"][0]["meets"]["plan_within_2h"] is False
        assert result["versions"][0]["all_met"] is False
        assert result["meets_all"] is False

    def test_incomplete_evidence_fails_that_version(self):
        result = slo.compute_slo([_version("16.1.0", complete=False), _version("16.2.0"), _version("16.3.0")])
        assert result["versions"][0]["meets"]["evidence_complete"] is False
        assert result["meets_all"] is False

    def test_reuse_below_50pct_fails(self):
        result = slo.compute_slo([_version("16.1.0", used=1, total=5)])
        assert result["versions"][0]["reuse_hit_rate"] == 0.2
        assert result["versions"][0]["meets"]["reuse_hit_rate_50pct"] is False

    def test_no_suggestions_is_not_a_pass(self):
        """没有复用建议时既不能判达标，也不能靠"没数据"蒙过去。"""
        result = slo.compute_slo([_version("16.1.0", used=0, total=0)])
        assert result["versions"][0]["reuse_hit_rate"] is None
        assert result["versions"][0]["meets"]["reuse_hit_rate_50pct"] is False

    def test_consecutive_counter_resets_on_failure(self):
        """连续 ≥3 版：中间断一次就要重新计数。"""
        versions = [
            _version("a"),
            _version("b"),
            _version("c", complete=False),  # 断档
            _version("d"),
            _version("e"),
        ]
        result = slo.compute_slo(versions)
        assert result["consecutive_passing"] == 2
        assert result["meets_all"] is False

    def test_missing_measurements_are_not_treated_as_pass(self):
        result = slo.compute_slo([{"version": "x"}])
        version = result["versions"][0]
        assert version["meets"]["plan_within_2h"] is False
        assert version["meets"]["execution_within_3h"] is False
        assert version["all_met"] is False

    def test_empty_input_does_not_claim_success(self):
        result = slo.compute_slo([])
        assert result["meets_all"] is False
        assert result["consecutive_passing"] == 0


class TestPreflightBlockers:
    def test_all_green_means_no_blockers(self):
        assert slo.preflight_blockers(
            {
                "database_ok": True,
                "dataset_meets_target": True,
                "fingerprint_present": True,
                "node_online": True,
                "target_reachable": True,
                "account_slot_configured": True,
            }
        ) == []

    def test_each_missing_check_becomes_a_readable_blocker(self):
        blockers = slo.preflight_blockers({})
        assert len(blockers) == 6
        joined = " ".join(blockers)
        assert "数据库" in joined
        assert "数据集" in joined
        assert "指纹" in joined
        assert "节点" in joined
        assert "VPN" in joined  # 明确指向真实原因，而不是"跑不了"
        assert "槽位" in joined

    def test_unreachable_target_says_it_will_not_substitute(self):
        blockers = slo.preflight_blockers({"target_reachable": False})
        assert any("不会用本地替身顶替" in item for item in blockers)
