"""Wiki 健康体检服务 —— 确定性 lint 规则扫描（VNext-6）。

5 条规则全部为确定性查询，不依赖 LLM：
  1. orphan_page   — Wiki 页面没有任何入站/出站链接。
  2. no_source     — Wiki 页面 source_refs_json 为空（结论无来源）。
  3. stale_page    — Raw Source 已 superseded，但引用它的页面仍为 approved。
  4. conflict_rule — 两个已 approved 的 rule 型页面在同一 stable_key 上内容冲突。
  5. coverage_gap  — 已 approved 的 requirement 型页面没有关联 test_case 或 api_case。

设计约定：
  - 函数只 `db.flush()`，由调用方 commit。
  - 空项目返回成功但 issues 为空。
  - severity 规则：orphan/no_source→P2，stale→P1，conflict→P0，coverage_gap→P1。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.knowledge import AiArtifact
from app.models.wiki import (
    WikiLintIssue,
    WikiLintReport,
    WikiLink,
    WikiPage,
    WikiRawSource,
)


def _issue(
    db: Session,
    *,
    report_id: int,
    project_id: int,
    rule: str,
    severity: str,
    title: str,
    description: str = "",
    entity_type: str = "",
    entity_id: int | None = None,
    related_entity_json: dict | None = None,
    suggestion: str = "",
) -> WikiLintIssue:
    issue = WikiLintIssue(
        report_id=report_id,
        project_id=project_id,
        rule=rule,
        severity=severity,
        title=title,
        description=description,
        entity_type=entity_type,
        entity_id=entity_id,
        related_entity_json=json.dumps(related_entity_json or {}, ensure_ascii=False),
        suggestion=suggestion,
        review_status="pending",
    )
    db.add(issue)
    return issue


# ── 规则 1: orphan_page ──

def _check_orphan_pages(db: Session, report_id: int, project_id: int) -> int:
    """Wiki 页面没有任何入站/出站链接（孤立页面）。"""
    # 子查询：有链接的页面 id 集合
    linked_from = db.query(WikiLink.from_page_id).filter(
        WikiLink.project_id == project_id,
    ).distinct().subquery()
    linked_to = db.query(WikiLink.to_page_id).filter(
        WikiLink.project_id == project_id,
    ).distinct().subquery()

    # 既不在 from 也不在 to 的页面
    orphan_ids = (
        db.query(WikiPage.id)
        .filter(WikiPage.project_id == project_id)
        .filter(~WikiPage.id.in_(db.query(linked_from.c.from_page_id)))
        .filter(~WikiPage.id.in_(db.query(linked_to.c.to_page_id)))
        .all()
    )
    orphan_id_set = {row[0] for row in orphan_ids}

    if not orphan_id_set:
        return 0

    pages = db.query(WikiPage).filter(WikiPage.id.in_(orphan_id_set)).all()
    for page in pages:
        _issue(
            db, report_id=report_id, project_id=project_id,
            rule="orphan_page", severity="P2",
            title=f"孤立页面: {page.title or '(无标题)'}",
            description=f"Wiki 页面 #{page.id}（类型={page.page_type}）没有任何入站或出站链接，可能无法被其他页面关联到。",
            entity_type="wiki_page", entity_id=page.id,
            suggestion="为该页面添加链接到相关模块/需求页面，或确认该页面是否需要保留。",
        )
    db.flush()
    return len(pages)


# ── 规则 2: no_source ──

def _check_no_source(db: Session, report_id: int, project_id: int) -> int:
    """Wiki 页面 source_refs_json 为空（结论无来源引用）。"""
    pages = (
        db.query(WikiPage)
        .filter(
            WikiPage.project_id == project_id,
            (WikiPage.source_refs_json == "[]") | (WikiPage.source_refs_json == "") | (WikiPage.source_refs_json.is_(None)),
        )
        .all()
    )
    for page in pages:
        _issue(
            db, report_id=report_id, project_id=project_id,
            rule="no_source", severity="P2",
            title=f"无来源页面: {page.title or '(无标题)'}",
            description=f"Wiki 页面 #{page.id}（类型={page.page_type}）的 source_refs_json 为空，其结论没有可追溯的来源引用。",
            entity_type="wiki_page", entity_id=page.id,
            suggestion="为该页面关联 Raw Source 或知识源，确保每个 Wiki 结论可追溯到原始需求。",
        )
    db.flush()
    return len(pages)


# ── 规则 3: stale_page ──

def _check_stale_pages(db: Session, report_id: int, project_id: int) -> int:
    """Raw Source 已 superseded，但引用它的 approved 页面未更新。"""
    # 找出所有 superseded 的 raw source
    superseded_raws = (
        db.query(WikiRawSource.id)
        .filter(WikiRawSource.project_id == project_id, WikiRawSource.status == "superseded")
        .all()
    )
    superseded_ids = {row[0] for row in superseded_raws}
    if not superseded_ids:
        return 0

    # 找出所有 approved 页面
    approved_pages = (
        db.query(WikiPage)
        .filter(WikiPage.project_id == project_id, WikiPage.review_status == "approved")
        .all()
    )

    count = 0
    for page in approved_pages:
        try:
            refs = json.loads(page.source_refs_json or "[]")
        except (json.JSONDecodeError, TypeError):
            refs = []
        # 检查 source_refs_json 中是否引用了 superseded 的 raw source
        stale_ref_ids: list[int] = []
        for ref in refs:
            raw_id = ref.get("raw_source_id")
            if raw_id and raw_id in superseded_ids:
                stale_ref_ids.append(raw_id)

        if stale_ref_ids:
            _issue(
                db, report_id=report_id, project_id=project_id,
                rule="stale_page", severity="P1",
                title=f"过期页面: {page.title or '(无标题)'}",
                description=(
                    f"Wiki 页面 #{page.id} 状态为 approved，但其引用的 Raw Source "
                    f"{stale_ref_ids} 已被标记为 superseded（有更新版本）。"
                ),
                entity_type="wiki_page", entity_id=page.id,
                related_entity_json={"stale_raw_source_ids": stale_ref_ids},
                suggestion="重新触发 Wiki 编译，将页面更新到最新 Raw Source 版本。",
            )
            count += 1

    db.flush()
    return count


# ── 规则 4: conflict_rule ──

def _check_conflict_rules(db: Session, report_id: int, project_id: int) -> int:
    """两个已 approved 的 rule 型页面，slug 相同但 content_hash 不同（冲突规则）。"""
    # 找出所有 approved rule 页面，按 slug 分组
    rule_pages = (
        db.query(WikiPage)
        .filter(
            WikiPage.project_id == project_id,
            WikiPage.page_type == "rule",
            WikiPage.review_status == "approved",
        )
        .all()
    )

    # 按 slug 分组
    slug_groups: dict[str, list[WikiPage]] = {}
    for page in rule_pages:
        slug = (page.slug or "").strip()
        if not slug:
            continue
        slug_groups.setdefault(slug, []).append(page)

    count = 0
    for slug, pages in slug_groups.items():
        if len(pages) < 2:
            continue
        # 检查是否所有页面的 content_hash 都相同
        hashes = {p.content_hash for p in pages}
        if len(hashes) <= 1:
            continue  # 内容相同，不冲突

        page_ids = [p.id for p in pages]
        # 选取内容最长的页面作为参照
        longest = max(pages, key=lambda p: len(p.content_md or ""))
        conflict_ids = [p for p in pages if p.id != longest.id]

        for conflict_page in conflict_ids:
            _issue(
                db, report_id=report_id, project_id=project_id,
                rule="conflict_rule", severity="P0",
                title=f"规则冲突: slug={slug}",
                description=(
                    f"已 approved 的规则页面 #{longest.id}（{longest.title}）和 #{conflict_page.id}"
                    f"（{conflict_page.title}）slug 相同但内容不一致。"
                ),
                entity_type="wiki_page", entity_id=conflict_page.id,
                related_entity_json={"conflicting_page_ids": [
                    p.id for p in pages if p.id != conflict_page.id
                ]},
                suggestion=f"审核这两个规则页面，确定以哪个版本为准，驳回或下架冲突版本。",
            )
            count += 1

    db.flush()
    return count


# ── 规则 5: coverage_gap ──

def _check_coverage_gaps(db: Session, report_id: int, project_id: int) -> int:
    """已 approved 的 requirement 页面没有关联 test_case 或 api_endpoint。"""
    from app.models.test_case import TestCase
    from app.models.api_asset import ApiEndpoint

    approved_reqs = (
        db.query(WikiPage)
        .filter(
            WikiPage.project_id == project_id,
            WikiPage.page_type == "requirement",
            WikiPage.review_status == "approved",
        )
        .all()
    )

    count = 0
    for page in approved_reqs:
        # 检查是否有 test_case 引用此页面（通过 title 模糊匹配）
        has_test = (
            db.query(TestCase.id)
            .filter(
                TestCase.project_id == project_id,
                TestCase.title.contains(page.title),
            )
            .first()
            is not None
        )

        # 检查是否有 api_endpoint 引用此页面（通过 summary 或 path 模糊匹配）
        has_api = (
            db.query(ApiEndpoint.id)
            .filter(
                ApiEndpoint.project_id == project_id,
                (ApiEndpoint.summary.contains(page.title))
                | (ApiEndpoint.path.contains(page.title)),
            )
            .first()
            is not None
        )

        if not has_test and not has_api:
            _issue(
                db, report_id=report_id, project_id=project_id,
                rule="coverage_gap", severity="P1",
                title=f"测试覆盖缺口: {page.title or '(无标题)'}",
                description=(
                    f"已 approved 的需求页面 #{page.id}（{page.title}）没有关联的"
                    f"功能测试用例或接口端点。"
                ),
                entity_type="wiki_page", entity_id=page.id,
                suggestion=(
                    f"为「{page.title}」生成功能测试用例或接口测试用例，"
                    f"确保 approved 需求有对应的测试覆盖。"
                ),
            )
            count += 1

    db.flush()
    return count


# ── 入口 ──

def run_lint(
    db: Session,
    *,
    project_id: int,
    operator_id: int = 0,
) -> WikiLintReport:
    """对指定项目运行全部 5 条 lint 规则，返回报告。

    报告状态：
      - running → success（全部规则执行完成）
      - running → failed（某规则抛异常，报告含 error_message）
    """
    report = WikiLintReport(
        project_id=project_id,
        status="running",
        summary_json="{}",
    )
    db.add(report)
    db.flush()

    rules = [
        ("orphan_page", _check_orphan_pages),
        ("no_source", _check_no_source),
        ("stale_page", _check_stale_pages),
        ("conflict_rule", _check_conflict_rules),
        ("coverage_gap", _check_coverage_gaps),
    ]

    summary: dict[str, int] = {}
    error_details: list[str] = []

    for rule_name, rule_fn in rules:
        try:
            hit = rule_fn(db, report.id, project_id)
            summary[rule_name] = hit
        except Exception as exc:
            summary[rule_name] = -1
            error_details.append(f"{rule_name}: {exc}")

    report.summary_json = json.dumps(summary, ensure_ascii=False)
    if error_details:
        report.status = "failed"
        report.error_message = "; ".join(error_details)
    else:
        report.status = "success"

    db.flush()
    return report


def get_report(db: Session, report_id: int, project_id: int) -> WikiLintReport | None:
    """获取 lint 报告，校验项目隔离。"""
    report = db.get(WikiLintReport, report_id)
    if not report or report.project_id != project_id:
        return None
    return report


def list_reports(
    db: Session,
    project_id: int,
    *,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[WikiLintReport], int]:
    """分页列出项目下的 lint 报告。"""
    q = db.query(WikiLintReport).filter(WikiLintReport.project_id == project_id)
    if status:
        q = q.filter(WikiLintReport.status == status)
    total = q.count()
    rows = (
        q.order_by(WikiLintReport.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return rows, total


def get_issues(
    db: Session,
    report_id: int,
    *,
    rule: str | None = None,
    severity: str | None = None,
    review_status: str | None = None,
) -> list[WikiLintIssue]:
    """获取报告下的 lint 问题列表，支持按规则/严重度/审核状态筛选。"""
    q = db.query(WikiLintIssue).filter(WikiLintIssue.report_id == report_id)
    if rule:
        q = q.filter(WikiLintIssue.rule == rule)
    if severity:
        q = q.filter(WikiLintIssue.severity == severity)
    if review_status:
        q = q.filter(WikiLintIssue.review_status == review_status)
    return q.order_by(WikiLintIssue.severity, WikiLintIssue.id).all()


def convert_issues_to_artifacts(
    db: Session,
    report: WikiLintReport,
    issue_ids: list[int] | None = None,
    artifact_type: str = "",
    operator_id: int = 0,
) -> list[AiArtifact]:
    """将 lint 问题转换为 AiArtifact（review_status=pending），进入人工审核台。

    产物类型自动映射：orphan_page→wiki_cleanup, no_source→wiki_source,
    stale_page→wiki_update, conflict_rule→wiki_conflict, coverage_gap→test_case。
    """
    q = db.query(WikiLintIssue).filter(
        WikiLintIssue.report_id == report.id,
        WikiLintIssue.resolved_artifact_id.is_(None),
    )
    if issue_ids:
        q = q.filter(WikiLintIssue.id.in_(issue_ids))

    issues = q.all()
    artifacts: list[AiArtifact] = []

    for issue in issues:
        atype = artifact_type or _map_artifact_type(issue.rule)
        content_data = {
            "description": issue.description,
            "suggestion": issue.suggestion,
            "rule": issue.rule,
            "severity": issue.severity,
            "entity_type": issue.entity_type,
            "entity_id": issue.entity_id,
            "lint_report_id": report.id,
        }
        art = AiArtifact(
            project_id=report.project_id,
            artifact_type=atype,
            title=f"[Lint] {issue.title}",
            content_json=json.dumps(content_data, ensure_ascii=False),
            source_refs=json.dumps(
                [{"type": "wiki_page", "id": issue.entity_id}] if issue.entity_id else [],
                ensure_ascii=False,
            ),
            review_status="pending",
        )
        db.add(art)
        db.flush()
        issue.resolved_artifact_id = art.id
        issue.review_status = "accepted"
        artifacts.append(art)

    db.flush()
    return artifacts


def _map_artifact_type(rule: str) -> str:
    mapping = {
        "orphan_page": "wiki_cleanup",
        "no_source": "wiki_source",
        "stale_page": "wiki_update",
        "conflict_rule": "wiki_conflict",
        "coverage_gap": "test_case",
    }
    return mapping.get(rule, "wiki_issue")
