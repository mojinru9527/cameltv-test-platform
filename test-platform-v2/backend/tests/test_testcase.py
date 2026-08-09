"""Test case CRUD tests — create, read, update, delete, domain tree."""
from __future__ import annotations


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
    """Batch 128 — 用例分类必须先区分用户端/运营后台，再展示子模块。"""

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
        assert user_domain["domain"] == "体育-用户端-功能"
        assert user_domain["modules"][0] == {
            "name": "赛事详情",
            "path": "赛事详情",
            "count": 1,
            "children": [{
                "name": "预测Pick",
                "path": "赛事详情/预测Pick",
                "count": 1,
                "children": [{
                    "name": "入口",
                    "path": "赛事详情/预测Pick/入口",
                    "count": 1,
                    "children": [],
                }],
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
