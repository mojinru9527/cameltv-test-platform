"""切片 6 (VNext-6) —— Wiki 健康体检：5 条确定性 lint 规则。

每条规则至少一个测试：
  1. orphan_page   — 无链接的页面被检出
  2. no_source     — source_refs_json 为空的页面被检出
  3. stale_page    — 引用 superseded raw source 的 approved 页面被检出
  4. conflict_rule — 同 slug 且 content_hash 不同的 approved rule 页面被检出
  5. coverage_gap  — 已 approved 的 requirement 页面没有测试覆盖

API 层：门禁/权限/列表/详情/convert 接线。
"""
from __future__ import annotations

import json

import pytest

from app.core.config import settings
from app.models.wiki import (
    WikiLintIssue,
    WikiLintReport,
    WikiLink,
    WikiPage,
    WikiRawSource,
)
from app.services.wiki import lint_service


# ═══════════════════════════════════════════════════════
# 辅助工厂函数
# ═══════════════════════════════════════════════════════

def _make_raw(db_session, **kw):
    row = WikiRawSource(
        project_id=1,
        source_type=kw.pop("source_type", "lanhu"),
        title=kw.pop("title", "Test Raw"),
        content_md=kw.pop("content_md", "content"),
        content_hash=kw.pop("content_hash", "hash1"),
        status=kw.pop("status", "active"),
        **kw,
    )
    db_session.add(row)
    db_session.flush()
    return row


def _make_page(db_session, **kw):
    row = WikiPage(
        project_id=1,
        page_type=kw.pop("page_type", "requirement"),
        title=kw.pop("title", "Test Page"),
        slug=kw.pop("slug", "test-page"),
        content_md=kw.pop("content_md", "# Test"),
        content_hash=kw.pop("content_hash", "ch1"),
        review_status=kw.pop("review_status", "pending"),
        source_refs_json=kw.pop("source_refs_json", "[]"),
        **kw,
    )
    db_session.add(row)
    db_session.flush()
    return row


def _make_link(db_session, from_id: int, to_id: int, **kw):
    row = WikiLink(
        project_id=1,
        from_page_id=from_id,
        to_page_id=to_id,
        link_type=kw.pop("link_type", "mentions"),
        **kw,
    )
    db_session.add(row)
    db_session.flush()
    return row


# ═══════════════════════════════════════════════════════
# 规则 1: orphan_page
# ═══════════════════════════════════════════════════════

class TestOrphanPage:
    def test_detects_page_without_links(self, db_session):
        """没有入站/出站链接的页面应被报为孤儿。"""
        _make_page(db_session, title="Orphan")
        # 另一个有链接的页面不应被报
        a = _make_page(db_session, title="A")
        b = _make_page(db_session, title="B")
        _make_link(db_session, a.id, b.id)

        report = lint_service.run_lint(db_session, project_id=1)
        db_session.flush()
        issues = lint_service.get_issues(db_session, report.id)

        orphan_issues = [i for i in issues if i.rule == "orphan_page"]
        assert len(orphan_issues) == 1
        assert "Orphan" in orphan_issues[0].title

    def test_no_false_positive_when_has_inbound_link(self, db_session):
        """有入站链接的页面不应报孤儿。"""
        a = _make_page(db_session, title="A")
        b = _make_page(db_session, title="B")
        _make_link(db_session, a.id, b.id)  # a -> b, b 有入站

        report = lint_service.run_lint(db_session, project_id=1)
        db_session.flush()
        issues = lint_service.get_issues(db_session, report.id)

        orphan_issues = [i for i in issues if i.rule == "orphan_page"]
        assert len(orphan_issues) == 0

    def test_no_false_positive_when_has_outbound_link(self, db_session):
        """有出站链接的页面不应报孤儿。"""
        a = _make_page(db_session, title="A")
        b = _make_page(db_session, title="B")
        _make_link(db_session, a.id, b.id)  # a 有出站

        report = lint_service.run_lint(db_session, project_id=1)
        db_session.flush()
        issues = lint_service.get_issues(db_session, report.id)

        orphan_issues = [i for i in issues if i.rule == "orphan_page"]
        assert len(orphan_issues) == 0


# ═══════════════════════════════════════════════════════
# 规则 2: no_source
# ═══════════════════════════════════════════════════════

class TestNoSource:
    def test_detects_page_with_empty_source_refs(self, db_session):
        """source_refs_json 为空时应报 no_source。"""
        _make_page(db_session, title="No Source", source_refs_json="[]")

        report = lint_service.run_lint(db_session, project_id=1)
        db_session.flush()
        issues = lint_service.get_issues(db_session, report.id)

        no_src = [i for i in issues if i.rule == "no_source"]
        assert len(no_src) == 1
        assert "No Source" in no_src[0].title

    def test_skips_page_with_source_refs(self, db_session):
        """有 source_refs_json 的页面不应报 no_source。"""
        _make_page(db_session, title="Has Source",
                   source_refs_json=json.dumps([{"raw_source_id": 1}]))

        report = lint_service.run_lint(db_session, project_id=1)
        db_session.flush()
        issues = lint_service.get_issues(db_session, report.id)

        no_src = [i for i in issues if i.rule == "no_source"]
        assert len(no_src) == 0


# ═══════════════════════════════════════════════════════
# 规则 3: stale_page
# ═══════════════════════════════════════════════════════

class TestStalePage:
    def test_detects_approved_page_referencing_superseded_raw(self, db_session):
        """approved 页面引用了 superseded raw source 应报 stale_page。"""
        raw = _make_raw(db_session, title="Old Raw", status="superseded",
                        immutable_version="v1")
        page = _make_page(
            db_session, title="Stale Page", review_status="approved",
            source_refs_json=json.dumps([{"raw_source_id": raw.id}]),
        )

        report = lint_service.run_lint(db_session, project_id=1)
        db_session.flush()
        issues = lint_service.get_issues(db_session, report.id)

        stale = [i for i in issues if i.rule == "stale_page"]
        assert len(stale) == 1
        assert stale[0].entity_id == page.id

    def test_skips_approved_page_with_active_raw(self, db_session):
        """approved 页面引用 active raw source 不应报 stale。"""
        raw = _make_raw(db_session, title="Active Raw", status="active")
        _make_page(
            db_session, title="Fresh Page", review_status="approved",
            source_refs_json=json.dumps([{"raw_source_id": raw.id}]),
        )

        report = lint_service.run_lint(db_session, project_id=1)
        db_session.flush()
        issues = lint_service.get_issues(db_session, report.id)

        stale = [i for i in issues if i.rule == "stale_page"]
        assert len(stale) == 0

    def test_skips_pending_page_with_superseded_raw(self, db_session):
        """非 approved 页面即使引用 superseded raw 也不报 stale（未生效的页面无过期概念）。"""
        raw = _make_raw(db_session, title="Old Raw", status="superseded")
        _make_page(
            db_session, title="Pending Page", review_status="pending",
            source_refs_json=json.dumps([{"raw_source_id": raw.id}]),
        )

        report = lint_service.run_lint(db_session, project_id=1)
        db_session.flush()
        issues = lint_service.get_issues(db_session, report.id)

        stale = [i for i in issues if i.rule == "stale_page"]
        assert len(stale) == 0


# ═══════════════════════════════════════════════════════
# 规则 4: conflict_rule
# ═══════════════════════════════════════════════════════

class TestConflictRule:
    def test_detects_conflicting_approved_rules(self, db_session):
        """两个 approved rule 同 slug 但不同 content_hash 应报冲突。"""
        _make_page(db_session, title="Rule A", page_type="rule", slug="same-rule",
                   content_md="# Rule v1", content_hash="hash-a",
                   review_status="approved")
        _make_page(db_session, title="Rule B", page_type="rule", slug="same-rule",
                   content_md="# Rule v2", content_hash="hash-b",
                   review_status="approved")

        report = lint_service.run_lint(db_session, project_id=1)
        db_session.flush()
        issues = lint_service.get_issues(db_session, report.id)

        conflicts = [i for i in issues if i.rule == "conflict_rule"]
        assert len(conflicts) >= 1
        assert all(i.severity == "P0" for i in conflicts)

    def test_skips_same_content_same_slug(self, db_session):
        """同 slug 且 content_hash 相同不报冲突（同一内容）。"""
        _make_page(db_session, title="Rule A", page_type="rule", slug="same-rule",
                   content_md="# Rule", content_hash="hash-same",
                   review_status="approved")
        _make_page(db_session, title="Rule B", page_type="rule", slug="same-rule",
                   content_md="# Rule", content_hash="hash-same",
                   review_status="approved")

        report = lint_service.run_lint(db_session, project_id=1)
        db_session.flush()
        issues = lint_service.get_issues(db_session, report.id)

        conflicts = [i for i in issues if i.rule == "conflict_rule"]
        assert len(conflicts) == 0

    def test_skips_non_approved_conflicts(self, db_session):
        """非 approved 的 rule 页面即使冲突也不报。"""
        _make_page(db_session, title="Rule A", page_type="rule", slug="same-rule",
                   content_md="# Rule v1", content_hash="hash-a",
                   review_status="approved")
        _make_page(db_session, title="Rule B", page_type="rule", slug="same-rule",
                   content_md="# Rule v2", content_hash="hash-b",
                   review_status="pending")

        report = lint_service.run_lint(db_session, project_id=1)
        db_session.flush()
        issues = lint_service.get_issues(db_session, report.id)

        conflicts = [i for i in issues if i.rule == "conflict_rule"]
        assert len(conflicts) == 0


# ═══════════════════════════════════════════════════════
# 规则 5: coverage_gap
# ═══════════════════════════════════════════════════════

class TestCoverageGap:
    def test_detects_approved_requirement_without_test_coverage(self, db_session):
        """approved requirement 页面没有关联 TestCase 或 ApiEndpoint 应报 coverage_gap。"""
        _make_page(db_session, title="Uncovered Feature", page_type="requirement",
                   review_status="approved")

        report = lint_service.run_lint(db_session, project_id=1)
        db_session.flush()
        issues = lint_service.get_issues(db_session, report.id)

        gaps = [i for i in issues if i.rule == "coverage_gap"]
        assert len(gaps) == 1
        assert "Uncovered Feature" in gaps[0].title

    def test_skips_non_approved_requirement(self, db_session):
        """非 approved 的 requirement 页面不报 coverage_gap。"""
        _make_page(db_session, title="Draft Feature", page_type="requirement",
                   review_status="draft")

        report = lint_service.run_lint(db_session, project_id=1)
        db_session.flush()
        issues = lint_service.get_issues(db_session, report.id)

        gaps = [i for i in issues if i.rule == "coverage_gap"]
        assert len(gaps) == 0


# ═══════════════════════════════════════════════════════
# 报告与边界
# ═══════════════════════════════════════════════════════

class TestLintReport:
    def test_report_has_summary(self, db_session):
        """报告 summary_json 应包含各规则命中数。"""
        # 创建会触发 orphan + no_source 的页面
        _make_page(db_session, title="Page 1")

        report = lint_service.run_lint(db_session, project_id=1)
        db_session.flush()

        assert report.status == "success"
        summary = json.loads(report.summary_json)
        assert "orphan_page" in summary
        assert "no_source" in summary
        assert "stale_page" in summary
        assert "conflict_rule" in summary
        assert "coverage_gap" in summary

    def test_empty_project_returns_success(self, db_session):
        """空项目应返回 success，issues 为空。"""
        report = lint_service.run_lint(db_session, project_id=1)
        db_session.flush()
        issues = lint_service.get_issues(db_session, report.id)

        assert report.status == "success"
        assert len(issues) == 0
        summary = json.loads(report.summary_json)
        assert all(v == 0 for v in summary.values())

    def test_project_isolation(self, db_session):
        """不同项目的 lint 不互相影响。"""
        _make_page(db_session, title="P1 Page")
        raw2 = _make_raw(db_session, title="P2 Raw")
        raw2.project_id = 999  # 不同项目

        report = lint_service.run_lint(db_session, project_id=1)
        db_session.flush()
        issues_p1 = lint_service.get_issues(db_session, report.id)

        # project_id=1 应该只看到自己的页面
        assert all(i.project_id == 1 for i in issues_p1)
        # 项目 999 的 raw 不应影响项目 1 的 stale 检测
        stale = [i for i in issues_p1 if i.rule == "stale_page"]
        assert len(stale) == 0

    def test_get_report_enforces_project_isolation(self, db_session):
        """get_report 应校验项目隔离。"""
        report = lint_service.run_lint(db_session, project_id=1)
        db_session.flush()

        # 不同项目查不到
        assert lint_service.get_report(db_session, report.id, project_id=999) is None
        # 正确项目能查到
        assert lint_service.get_report(db_session, report.id, project_id=1) is not None

    def test_list_reports_pagination(self, db_session):
        """list_reports 应正确分页。"""
        for _ in range(3):
            r = WikiLintReport(project_id=1, status="success",
                              summary_json='{"orphan_page":0}')
            db_session.add(r)
        db_session.flush()

        rows, total = lint_service.list_reports(db_session, project_id=1,
                                                 page=1, page_size=2)
        assert len(rows) == 2
        assert total == 3


# ═══════════════════════════════════════════════════════
# Convert / AI Artifact
# ═══════════════════════════════════════════════════════

class TestConvertToArtifact:
    def test_convert_creates_artifact(self, db_session):
        """convert 应为每条 issue 创建 AiArtifact 并标记 resolved。"""
        _make_page(db_session, title="Orphan", source_refs_json="[]")

        report = lint_service.run_lint(db_session, project_id=1)
        db_session.flush()
        issues = lint_service.get_issues(db_session, report.id)
        # 至少有一条 orphan 或 no_source
        pending = [i for i in issues if i.review_status == "pending"]
        assert len(pending) >= 1

        from app.services.wiki.lint_service import convert_issues_to_artifacts
        artifacts = convert_issues_to_artifacts(
            db_session, report,
            issue_ids=[pending[0].id],
        )
        db_session.flush()

        assert len(artifacts) == 1
        assert artifacts[0].artifact_type in ("wiki_cleanup", "wiki_source")
        assert artifacts[0].review_status == "pending"

        # issue 应该被标记
        db_session.refresh(pending[0])
        assert pending[0].resolved_artifact_id == artifacts[0].id
        assert pending[0].review_status == "accepted"

    def test_convert_all_pending(self, db_session):
        """不指定 issue_ids 时转换所有 pending issues。"""
        _make_page(db_session, title="Orphan 1")
        _make_page(db_session, title="Orphan 2", source_refs_json="[]")

        report = lint_service.run_lint(db_session, project_id=1)
        db_session.flush()
        issues = lint_service.get_issues(db_session, report.id)
        pending = [i for i in issues if i.review_status == "pending"]

        from app.services.wiki.lint_service import convert_issues_to_artifacts
        artifacts = convert_issues_to_artifacts(db_session, report)
        db_session.flush()

        assert len(artifacts) == len(pending)
        assert all(a.review_status == "pending" for a in artifacts)


# ═══════════════════════════════════════════════════════
# API 层
# ═══════════════════════════════════════════════════════

class TestLintApi:
    def test_lint_gated_when_disabled(self, client, auth_headers, monkeypatch):
        """wiki_lint_enabled=False 时返回 503。"""
        monkeypatch.setattr(settings, "wiki_lint_enabled", False, raising=False)
        r = client.post("/api/v1/wiki/lint", headers=auth_headers, json={})
        assert r.status_code == 503

    def test_lint_requires_auth(self, client, monkeypatch):
        """未登录时返回 401/403。"""
        monkeypatch.setattr(settings, "wiki_lint_enabled", True, raising=False)
        r = client.post("/api/v1/wiki/lint", json={})
        assert r.status_code in (401, 403)

    def test_run_and_get_report(self, client, auth_headers, db_session, monkeypatch):
        """能跑 lint 并获取报告详情。"""
        monkeypatch.setattr(settings, "wiki_lint_enabled", True, raising=False)
        _make_page(db_session, title="API Test Page")

        r = client.post("/api/v1/wiki/lint", headers=auth_headers, json={})
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["status"] == "success"
        assert "issues" in data
        report_id = data["id"]

        r2 = client.get(f"/api/v1/wiki/lint/reports/{report_id}", headers=auth_headers)
        assert r2.status_code == 200
        assert r2.json()["data"]["id"] == report_id

    def test_list_reports(self, client, auth_headers, monkeypatch):
        """报告列表接口可用。"""
        monkeypatch.setattr(settings, "wiki_lint_enabled", True, raising=False)
        r = client.get("/api/v1/wiki/lint/reports", headers=auth_headers)
        assert r.status_code == 200
        assert "total" in r.json()["data"]

    def test_convert_issues_api(self, client, auth_headers, db_session, monkeypatch):
        """POST /lint/reports/{id}/convert 能成功转换。"""
        monkeypatch.setattr(settings, "wiki_lint_enabled", True, raising=False)
        _make_page(db_session, title="Convert Test")

        r = client.post("/api/v1/wiki/lint", headers=auth_headers, json={})
        assert r.status_code == 200
        report_id = r.json()["data"]["id"]
        issues = r.json()["data"]["issues"]
        if not issues:
            pytest.skip("没有 lint 问题可转换")

        c = client.post(f"/api/v1/wiki/lint/reports/{report_id}/convert",
                        headers=auth_headers, json={"issue_ids": []})
        assert c.status_code == 200
        result = c.json()["data"]
        assert result["converted"] >= 1
        assert len(result["artifact_ids"]) >= 1
