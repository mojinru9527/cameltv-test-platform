"""Test case CRUD tests — create, read, update, delete, domain tree."""
from __future__ import annotations

import pytest


@pytest.mark.parametrize("export_format", ["excel", "xmind"])
def test_export_uses_canonical_taxonomy_filters(
    client, auth_headers, monkeypatch, export_format
):
    captured: dict[str, str] = {}

    def fake_list_cases(_db, **kwargs):
        captured.update(kwargs)
        return [], 0

    monkeypatch.setattr(
        "app.api.v1.test_case.test_case_service.list_cases", fake_list_cases
    )

    response = client.get(
        f"/api/v1/test-cases/export/{export_format}",
        params={
            "surface": "用户端",
            "taxonomy_domain": "赛事详情",
            "taxonomy_module": "预测Pick",
            "positive_negative": "negative",
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert captured["surface"] == "用户端"
    assert captured["taxonomy_domain"] == "赛事详情"
    assert captured["taxonomy_module"] == "预测Pick"
    assert captured["positive_negative"] == "negative"


class TestCaseCRUD:
    def test_create_case(self, client, auth_headers):
        resp = client.post("/api/v1/test-cases", json={
            "title": "登录功能-正常登录", "domain": "用户端",
            "module": "登录", "priority": "P0", "case_type": "manual",
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["title"] == "登录功能-正常登录"
        assert data["priority"] == "P0"
        assert data["id"] > 0

    def test_list_cases(self, client, auth_headers):
        # Create 2 cases
        for i in range(2):
            client.post("/api/v1/test-cases", json={
                "title": f"Case {i}", "domain": "用户端",
                "module": "测试", "priority": "P1",
            }, headers=auth_headers)
        resp = client.get("/api/v1/test-cases?page=1&page_size=10", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] >= 2
        assert len(data["items"]) >= 2

    def test_get_case(self, client, auth_headers):
        create_resp = client.post("/api/v1/test-cases", json={
            "title": "Detail test", "domain": "用户端", "module": "测试",
        }, headers=auth_headers)
        case_id = create_resp.json()["data"]["id"]
        resp = client.get(f"/api/v1/test-cases/{case_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "Detail test"

    def test_update_case(self, client, auth_headers):
        create_resp = client.post("/api/v1/test-cases", json={
            "title": "Old title", "domain": "用户端", "module": "测试",
        }, headers=auth_headers)
        case_id = create_resp.json()["data"]["id"]
        resp = client.put(f"/api/v1/test-cases/{case_id}", json={
            "title": "New title", "priority": "P2",
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "New title"

    def test_delete_case(self, client, auth_headers):
        create_resp = client.post("/api/v1/test-cases", json={
            "title": "Delete me", "domain": "用户端", "module": "测试",
        }, headers=auth_headers)
        case_id = create_resp.json()["data"]["id"]
        resp = client.delete(f"/api/v1/test-cases/{case_id}", headers=auth_headers)
        assert resp.status_code == 200
        # Verify deleted
        get_resp = client.get(f"/api/v1/test-cases/{case_id}", headers=auth_headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["code"] == 404

    def test_filter_by_domain(self, client, auth_headers):
        client.post("/api/v1/test-cases", json={
            "title": "Case A", "domain": "用户端", "module": "登录",
        }, headers=auth_headers)
        client.post("/api/v1/test-cases", json={
            "title": "Case B", "domain": "运营后台", "module": "配置",
        }, headers=auth_headers)
        resp = client.get("/api/v1/test-cases?domain=用户端", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert all(item["domain"] == "用户端" for item in data["items"])

    def test_domain_tree(self, client, auth_headers):
        client.post("/api/v1/test-cases", json={
            "title": "Tree test", "domain": "用户端", "module": "登录",
        }, headers=auth_headers)
        resp = client.get("/api/v1/test-cases/domains", headers=auth_headers)
        assert resp.status_code == 200
        domains = resp.json()["data"]
        assert len(domains) > 0
        assert any(d["domain"] == "用户端" for d in domains)


class TestCaseBatch:
    def test_batch_update(self, client, auth_headers):
        ids = []
        for i in range(3):
            r = client.post("/api/v1/test-cases", json={
                "title": f"Batch {i}", "domain": "用户端", "module": "测试",
                "priority": "P3",
            }, headers=auth_headers)
            ids.append(r.json()["data"]["id"])

        resp = client.put("/api/v1/test-cases/batch", json={
            "ids": ids, "priority": "P0",
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["updated"] == 3

        # Verify all updated
        for cid in ids:
            r = client.get(f"/api/v1/test-cases/{cid}", headers=auth_headers)
            assert r.json()["data"]["priority"] == "P0"

    def test_batch_delete(self, client, auth_headers):
        ids = []
        for i in range(2):
            r = client.post("/api/v1/test-cases", json={
                "title": f"Del batch {i}", "domain": "用户端", "module": "测试",
            }, headers=auth_headers)
            ids.append(r.json()["data"]["id"])

        # httpx's TestClient.delete() doesn't accept a body; use .request() for DELETE+json.
        resp = client.request("DELETE", "/api/v1/test-cases/batch", json={
            "ids": ids,
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["deleted"] == 2


class TestCaseTypeStatistics:
    """Batch 127 — 类型统计必须守恒并兼容历史 functional 枚举。"""

    def test_stats_aliases_functional_and_excludes_soft_deleted(
        self, client, auth_headers, db_session,
    ):
        from app.models.test_case import TestCase

        db_session.add_all([
            TestCase(project_id=1, title="manual", case_type="manual", is_deleted=False),
            TestCase(project_id=1, title="legacy", case_type="functional", is_deleted=False),
            TestCase(project_id=1, title="api", case_type="api", is_deleted=False),
            TestCase(project_id=1, title="ui", case_type="ui", is_deleted=False),
            TestCase(project_id=1, title="deleted", case_type="manual", is_deleted=True),
        ])
        db_session.commit()

        response = client.get("/api/v1/test-cases/stats", headers=auth_headers)

        assert response.status_code == 200
        assert response.json()["data"] == {
            "total": 4,
            "by_type": {"manual": 2, "api": 1, "ui": 1},
        }

    def test_manual_filter_includes_legacy_functional(
        self, client, auth_headers, db_session,
    ):
        from app.models.test_case import TestCase

        db_session.add_all([
            TestCase(project_id=1, title="manual", case_type="manual", is_deleted=False),
            TestCase(project_id=1, title="legacy", case_type="functional", is_deleted=False),
            TestCase(project_id=1, title="api", case_type="api", is_deleted=False),
        ])
        db_session.commit()

        response = client.get(
            "/api/v1/test-cases?case_type=manual&page_size=20",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total"] == 2
        assert {item["title"] for item in data["items"]} == {"manual", "legacy"}

    def test_create_normalizes_functional_to_manual(self, client, auth_headers):
        response = client.post(
            "/api/v1/test-cases",
            json={"title": "legacy input", "case_type": "functional"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["data"]["case_type"] == "manual"

    def test_dashboard_type_counts_sum_to_total(
        self, client, auth_headers, db_session,
    ):
        from app.models.test_case import TestCase

        db_session.add_all([
            TestCase(project_id=1, title="manual", case_type="manual", priority="P0", is_deleted=False),
            TestCase(project_id=1, title="legacy", case_type="functional", priority="P1", is_deleted=False),
            TestCase(project_id=1, title="api", case_type="api", priority="P2", is_deleted=False),
            TestCase(project_id=1, title="deleted", case_type="ui", priority="P3", is_deleted=True),
        ])
        db_session.commit()

        response = client.get("/api/v1/dashboard/stats", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total_cases"] == 3
        counts = {item["case_type"]: item["count"] for item in data["case_type_stats"]}
        assert counts == {"manual": 2, "api": 1, "ui": 0}
        assert sum(counts.values()) == data["total_cases"]
        manual_priority = next(
            item for item in data["priority_distribution"] if item["case_type"] == "manual"
        )
        assert manual_priority["p0"] == 1
        assert manual_priority["p1"] == 1


class TestCaseTaxonomy:
    """Batch 128/130 — 先区分界面，再按真实业务模块聚合。"""

    def test_taxonomy_defaults_to_functional_cases_and_builds_module_paths(
        self, client, auth_headers, db_session,
    ):
        from app.models.test_case import TestCase

        db_session.add_all([
            TestCase(
                project_id=1,
                title="用户端预测入口",
                domain="体育-用户端-功能",
                module="赛事详情/预测Pick/入口",
                case_type="manual",
                is_deleted=False,
            ),
            TestCase(
                project_id=1,
                title="后台预测配置",
                domain="体育-运营后台-功能",
                module="预测管理/玩法配置",
                case_type="functional",
                is_deleted=False,
            ),
            TestCase(
                project_id=1,
                title="预测接口",
                domain="体育-接口测试",
                module="预测/提交",
                case_type="api",
                is_deleted=False,
            ),
            TestCase(
                project_id=1,
                title="已删除用例",
                domain="体育-用户端-功能",
                module="不应出现",
                case_type="manual",
                is_deleted=True,
            ),
        ])
        db_session.commit()

        response = client.get("/api/v1/test-cases/taxonomy", headers=auth_headers)

        assert response.status_code == 200
        taxonomy = response.json()["data"]
        assert [surface["surface"] for surface in taxonomy] == ["用户端", "运营后台"]
        user_domain = taxonomy[0]["domains"][0]
        assert user_domain["domain"] == "赛事详情"
        assert user_domain["modules"][0] == {
            "name": "预测Pick",
            "path": "预测Pick",
            "count": 1,
            "children": [{
                "name": "入口",
                "path": "预测Pick/入口",
                "count": 1,
                "children": [],
            }],
        }
        assert "预测接口" not in str(taxonomy)
        assert "已删除用例" not in str(taxonomy)

    def test_taxonomy_all_includes_api_surface(self, client, auth_headers, db_session):
        from app.models.test_case import TestCase

        db_session.add(TestCase(
            project_id=1,
            title="健康检查接口",
            domain="体育-接口测试",
            module="系统/健康检查",
            case_type="api",
            is_deleted=False,
        ))
        db_session.commit()

        response = client.get(
            "/api/v1/test-cases/taxonomy?case_type=all",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert [item["surface"] for item in response.json()["data"]] == ["接口测试"]

    @pytest.mark.parametrize("domain", [
        "个人中心", "赛事详情", "直播间", "APP端数据与排行榜", "资讯", "首页",
        "PC端", "搜索", "登录注册", "启动引导", "支付与账户", "UGC内容",
        "WEB端", "骆驼币系统", "广告系统", "银钻系统", "UGC功能", "银钻预测",
        "付费活动",
    ])
    def test_legacy_user_domains_are_reclassified(self, domain):
        from app.services.test_case_service import classify_case_surface

        assert classify_case_surface(domain, "manual") == "用户端"

    @pytest.mark.parametrize("domain", [
        "财务管理", "UGC管理", "商城管理", "消息管理", "赛事预测", "广告管理",
        "活动管理", "银钻任务管理", "风控管理", "装扮管理", "系统管理",
        "球队及联赛管理",
    ])
    def test_legacy_admin_domains_are_reclassified(self, domain):
        from app.services.test_case_service import classify_case_surface

        assert classify_case_surface(domain, "functional") == "运营后台"

    def test_list_surface_and_taxonomy_use_the_same_classifier(
        self, client, auth_headers, db_session,
    ):
        from app.models.test_case import TestCase

        db_session.add_all([
            TestCase(
                project_id=1,
                case_id="LEGACY-USER",
                title="用户资产",
                domain="个人中心",
                module="我的资产/余额",
                case_type="manual",
                is_deleted=False,
            ),
            TestCase(
                project_id=1,
                case_id="LEGACY-ADMIN",
                title="用户账户配置",
                domain="财务管理",
                module="用户账户/配置",
                case_type="functional",
                is_deleted=False,
            ),
            TestCase(
                project_id=1,
                case_id="UNKNOWN-MANUAL",
                title="未来模块",
                domain="未来业务域",
                module="实验",
                case_type="manual",
                is_deleted=False,
            ),
            TestCase(
                project_id=1,
                case_id="API-WINS",
                title="后台接口",
                domain="财务管理",
                module="账户/查询",
                case_type="api",
                is_deleted=False,
            ),
        ])
        db_session.commit()

        list_response = client.get(
            "/api/v1/test-cases?page_size=100",
            headers=auth_headers,
        )
        taxonomy_response = client.get(
            "/api/v1/test-cases/taxonomy?case_type=all",
            headers=auth_headers,
        )

        assert list_response.status_code == 200
        by_case_id = {
            item["case_id"]: item["surface"]
            for item in list_response.json()["data"]["items"]
            if item["case_id"]
        }
        assert by_case_id == {
            "LEGACY-USER": "用户端",
            "LEGACY-ADMIN": "运营后台",
            "UNKNOWN-MANUAL": "其他",
            "API-WINS": "接口测试",
        }

        assert taxonomy_response.status_code == 200
        taxonomy = taxonomy_response.json()["data"]
        taxonomy_domains = {
            (surface["surface"], domain["domain"])
            for surface in taxonomy
            for domain in surface["domains"]
        }
        assert ("用户端", "个人中心") in taxonomy_domains
        assert ("运营后台", "财务管理") in taxonomy_domains
        assert ("其他", "未来业务域") in taxonomy_domains
        assert ("接口测试", "财务管理") in taxonomy_domains

    @pytest.mark.parametrize(("domain", "module", "expected"), [
        (
            "体育-用户端-功能",
            "安卓iOS/赛事详情/预测Pick/入口",
            ("用户端", "赛事详情", "预测Pick/入口"),
        ),
        (
            "用户端/赛事详情/赛事详情页(PC)",
            "赛事详情页(PC)/预测Pick",
            ("用户端", "赛事详情", "预测Pick"),
        ),
        (
            "体育-用户端",
            "赛事回放列表(PC)/筛选",
            ("用户端", "回放", "筛选"),
        ),
        (
            "运营后台/财务管理/用户账户",
            "用户账户/流水",
            ("运营后台", "财务管理", "用户账户/流水"),
        ),
        (
            "体育-运营后台-功能",
            "运营后台/赛事预测/奖励发放记录",
            ("运营后台", "赛事预测", "奖励发放记录"),
        ),
        (
            "体育-接口测试",
            "PC-WEB/世界杯专题/赛程",
            ("接口测试", "世界杯专题", "赛程"),
        ),
        (
            "体育平台-用户端",
            "首页PC端",
            ("用户端", "首页", ""),
        ),
    ])
    def test_taxonomy_location_removes_terminal_wrappers(
        self, domain, module, expected,
    ):
        from app.services.test_case_taxonomy import canonical_case_location

        location = canonical_case_location(domain, module, "manual")

        assert (location.surface, location.domain, location.module_path) == expected
        rendered = f"{location.domain}/{location.module_path}".lower()
        assert "pc-web" not in rendered
        assert "安卓ios" not in rendered
        assert "移动端-web" not in rendered

    def test_taxonomy_aggregates_terminal_variants_and_parent_filter_matches_all(
        self, client, auth_headers, db_session,
    ):
        from app.models.test_case import TestCase

        db_session.add_all([
            TestCase(
                project_id=1,
                case_id="CASE-PC",
                title="PC 预测入口",
                domain="体育-用户端-功能",
                module="PC-web/赛事详情/预测Pick/入口",
                case_type="manual",
                positive_negative="positive",
                is_deleted=False,
            ),
            TestCase(
                project_id=1,
                case_id="CASE-MOBILE",
                title="移动端预测异常",
                domain="用户端/赛事详情/赛事详情页_移动_",
                module="赛事详情页_移动_/预测Pick/异常处理",
                case_type="manual",
                positive_negative="negative",
                is_deleted=False,
            ),
            TestCase(
                project_id=1,
                case_id="CASE-OTHER",
                title="联赛入口",
                domain="用户端/联赛",
                module="联赛详情页/入口",
                case_type="manual",
                positive_negative="negative",
                is_deleted=False,
            ),
        ])
        db_session.commit()

        taxonomy_response = client.get(
            "/api/v1/test-cases/taxonomy", headers=auth_headers,
        )
        list_response = client.get(
            "/api/v1/test-cases",
            params={
                "surface": "用户端",
                "taxonomy_domain": "赛事详情",
                "taxonomy_module": "预测Pick",
                "page_size": 100,
            },
            headers=auth_headers,
        )

        assert taxonomy_response.status_code == 200
        user_surface = next(
            item for item in taxonomy_response.json()["data"]
            if item["surface"] == "用户端"
        )
        event_domain = next(
            item for item in user_surface["domains"]
            if item["domain"] == "赛事详情"
        )
        assert event_domain["count"] == 2
        assert [node["name"] for node in event_domain["modules"]] == ["预测Pick"]
        assert event_domain["modules"][0]["count"] == 2

        assert list_response.status_code == 200
        page = list_response.json()["data"]
        assert page["total"] == 2
        assert {item["case_id"] for item in page["items"]} == {
            "CASE-PC", "CASE-MOBILE",
        }

    def test_exact_case_id_and_negative_filter_do_not_match_unrelated_cases(
        self, client, auth_headers, db_session,
    ):
        from app.models.test_case import TestCase

        db_session.add_all([
            TestCase(
                project_id=1,
                case_id="SP-B125-EXACT",
                title="目标异常",
                domain="用户端/首页",
                module="热门赛事",
                case_type="manual",
                positive_negative="negative",
                is_deleted=False,
            ),
            TestCase(
                project_id=1,
                case_id="SP-B125-EXACT-SUFFIX",
                title="相似编号正向",
                domain="用户端/首页",
                module="热门赛事",
                case_type="manual",
                positive_negative="positive",
                is_deleted=False,
            ),
        ])
        db_session.commit()

        response = client.get(
            "/api/v1/test-cases",
            params={
                "case_id": "SP-B125-EXACT",
                "positive_negative": "negative",
                "page_size": 100,
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        page = response.json()["data"]
        assert page["total"] == 1
        assert [item["case_id"] for item in page["items"]] == ["SP-B125-EXACT"]
        item = page["items"][0]
        assert item["positive_negative"] == "negative"
        assert item["taxonomy_domain"] == "首页"
        assert item["taxonomy_module"] == "热门赛事"
        assert item["terminal_scopes"] == []

class TestCaseDirectFilter:
    """Batch 132 — taxonomy_direct 直属精确过滤：父级计数中的直属用例可精确查询。"""

    def _seed(self, db_session):
        from app.models.test_case import TestCase
        db_session.add_all([
            TestCase(
                project_id=1, case_id="CASE-DIRECT",
                title="赛事详情直属用例",
                domain="用户端/赛事详情", module="",
                case_type="manual", positive_negative="positive",
                is_deleted=False,
            ),
            TestCase(
                project_id=1, case_id="CASE-PICK",
                title="预测Pick 直属用例",
                domain="用户端/赛事详情", module="预测Pick",
                case_type="manual", positive_negative="positive",
                is_deleted=False,
            ),
            TestCase(
                project_id=1, case_id="CASE-SUB",
                title="预测Pick 子模块用例",
                domain="用户端/赛事详情", module="预测Pick/入口",
                case_type="manual", positive_negative="negative",
                is_deleted=False,
            ),
        ])
        db_session.commit()

    def test_domain_direct_only_returns_cases_without_submodule_path(
        self, client, auth_headers, db_session,
    ):
        self._seed(db_session)
        response = client.get(
            "/api/v1/test-cases",
            params={
                "taxonomy_domain": "赛事详情",
                "taxonomy_direct": "true",
                "page_size": 100,
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        page = response.json()["data"]
        assert page["total"] == 1
        assert [item["case_id"] for item in page["items"]] == ["CASE-DIRECT"]
        assert page["items"][0]["taxonomy_module"] == ""

    def test_module_direct_only_is_exact_path_not_descendants(
        self, client, auth_headers, db_session,
    ):
        self._seed(db_session)
        response = client.get(
            "/api/v1/test-cases",
            params={
                "taxonomy_domain": "赛事详情",
                "taxonomy_module": "预测Pick",
                "taxonomy_direct": "true",
                "page_size": 100,
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        page = response.json()["data"]
        assert page["total"] == 1
        assert [item["case_id"] for item in page["items"]] == ["CASE-PICK"]

    def test_without_direct_parent_filter_still_includes_descendants(
        self, client, auth_headers, db_session,
    ):
        self._seed(db_session)
        response = client.get(
            "/api/v1/test-cases",
            params={
                "taxonomy_domain": "赛事详情",
                "taxonomy_module": "预测Pick",
                "page_size": 100,
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        page = response.json()["data"]
        assert page["total"] == 2
        assert {item["case_id"] for item in page["items"]} == {"CASE-PICK", "CASE-SUB"}

    def test_taxonomy_domain_parent_includes_direct_and_descendants(
        self, client, auth_headers, db_session,
    ):
        self._seed(db_session)
        response = client.get(
            "/api/v1/test-cases",
            params={
                "taxonomy_domain": "赛事详情",
                "page_size": 100,
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        page = response.json()["data"]
        assert page["total"] == 3
