"""TestCaseLinker — 测试用例 ↔ 模块/页面 自动关联器 (v1.1)

Multi-strategy matching engine that connects TestCase records to RequirementModule
nodes via KnowledgeRelation (relation_type="tested_by").

Strategies (priority order):
  1. Exact match: case name contains module name
  2. Function point match: case relates to a function_point child
  3. API match: case's API endpoint matches the module's domain
  4. Manual: user-provided mapping (not handled here — see API layer)
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.knowledge import KnowledgeEntity, KnowledgeRelation
from app.models.requirement_module import RequirementModule
from app.models.test_case import TestCase

logger = logging.getLogger("knowledge.test_case_linker")


# ── Dataclasses ──

@dataclass
class ModuleTestSummary:
    """Test coverage summary for a module."""
    module_id: int
    module_name: str
    total_test_cases: int = 0
    functional: int = 0
    api: int = 0
    automation: int = 0
    coverage_rate: float = 0.0
    last_run_status: str = "unknown"
    linked_case_ids: list[int] = field(default_factory=list)


@dataclass
class LinkingResult:
    """Result of a link test cases operation."""
    linked_count: int = 0
    relations_created: int = 0
    by_strategy: dict[str, int] = field(default_factory=dict)  # strategy → count
    unmatched_cases: list[int] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ── Entity Key Helpers ──

def _module_entity_key(project_id: int, module_name: str, version: str = "") -> str:
    """Build stable entity_key for a client_module."""
    if version:
        return f"client_module:p{project_id}:{version}:{module_name}"
    return f"client_module:p{project_id}:{module_name}"


def _test_case_entity_key(project_id: int, test_case_id: int) -> str:
    return f"test_case:p{project_id}:{test_case_id}"


def _normalize(text: str) -> str:
    return (text or "").strip().lower()


# ── Matching Strategies ──

def _match_exact(
    module: RequirementModule,
    test_cases: list[TestCase],
) -> list[TestCase]:
    """Strategy 1: Exact name match — case title or module field contains module name."""
    mod_name = _normalize(module.name)
    matched: list[TestCase] = []
    for tc in test_cases:
        tc_title = _normalize(tc.title)
        tc_module = _normalize(tc.module)
        if mod_name and (mod_name in tc_title or mod_name in tc_module):
            matched.append(tc)
    return matched


def _match_function_point(
    db: Session,
    module: RequirementModule,
    test_cases: list[TestCase],
) -> list[TestCase]:
    """Strategy 2: Function point match — case relates to child function_point nodes."""
    # Load function_point children
    fp_nodes = list(
        db.scalars(
            select(RequirementModule).where(
                RequirementModule.node_type == "function_point",
                RequirementModule.parent_module_id.in_(
                    select(RequirementModule.id).where(
                        RequirementModule.parent_module_id == module.id,
                    )
                ),
            )
        ).all()
    )

    if not fp_nodes:
        return []

    fp_names = {_normalize(fp.name) for fp in fp_nodes}
    matched: list[TestCase] = []
    for tc in test_cases:
        tc_title = _normalize(tc.title)
        if any(fp_name in tc_title for fp_name in fp_names):
            matched.append(tc)
    return matched


def _match_api(
    module: RequirementModule,
    test_cases: list[TestCase],
) -> list[TestCase]:
    """Strategy 3: API endpoint match — case's API endpoint domain hints at module."""
    mod_name = _normalize(module.name)
    matched: list[TestCase] = []
    for tc in test_cases:
        if not tc.api_endpoint:
            continue
        endpoint_lower = tc.api_endpoint.lower()
        # Check if module name appears in endpoint path
        # e.g., module="资讯" matches /api/v1/news/... (need domain knowledge)
        if mod_name and mod_name in endpoint_lower:
            matched.append(tc)
        # Also check module field
        tc_mod = _normalize(tc.module)
        if tc_mod and tc_mod == mod_name:
            if tc not in matched:
                matched.append(tc)
    return matched


# ── Public API ──

def link_test_cases_to_module(
    db: Session,
    *,
    module: RequirementModule,
    test_cases: list[TestCase],
    project_id: int,
    version: str = "",
    dry_run: bool = False,
) -> LinkingResult:
    """Link test cases to a single module using all strategies.

    Returns LinkingResult with details per strategy.
    """
    result = LinkingResult()
    remaining = list(test_cases)

    strategies = [
        ("exact_name", _match_exact),
        ("function_point", lambda m, tcs: _match_function_point(db, m, tcs)),
        ("api_match", _match_api),
    ]

    all_matched: set[int] = set()

    for strategy_name, strategy_fn in strategies:
        matched = strategy_fn(module, remaining)
        if not matched:
            continue

        result.by_strategy[strategy_name] = len(matched)
        for tc in matched:
            if tc.id in all_matched:
                continue
            all_matched.add(tc.id)

            if not dry_run:
                # Create KnowledgeRelation: Module ──tested_by──→ TestCase
                rel = _create_tested_by_relation(
                    db, module, tc, project_id, version, strategy_name,
                )
                if rel:
                    result.relations_created += 1

        # Remove matched from remaining
        matched_ids = {tc.id for tc in matched}
        remaining = [tc for tc in remaining if tc.id not in matched_ids]

    result.linked_count = len(all_matched)
    result.unmatched_cases = [tc.id for tc in remaining]

    logger.info(
        "Linked %d test cases to module #%d '%s' (%d relations) — strategies: %s",
        result.linked_count, module.id, module.name,
        result.relations_created, result.by_strategy,
    )
    return result


def _create_tested_by_relation(
    db: Session,
    module: RequirementModule,
    test_case: TestCase,
    project_id: int,
    version: str,
    strategy: str,
) -> KnowledgeRelation | None:
    """Create a tested_by KnowledgeRelation from module to test case.

    Idempotent: skips if relation already exists.
    """
    module_key = _module_entity_key(project_id, module.name, version)
    case_key = _test_case_entity_key(project_id, test_case.id)

    # Ensure source/target entities exist
    source = _ensure_entity(db, project_id, module_key, "client_module", module.name)
    target = _ensure_entity(db, project_id, case_key, "test_case", test_case.title)

    if not source or not target:
        return None

    # Check for existing relation
    existing = db.scalar(
        select(KnowledgeRelation.id).where(
            KnowledgeRelation.project_id == project_id,
            KnowledgeRelation.from_entity_id == source.id,
            KnowledgeRelation.to_entity_id == target.id,
            KnowledgeRelation.relation_type == "tested_by",
        )
    )
    if existing:
        return None

    rel = KnowledgeRelation(
        project_id=project_id,
        from_entity_id=source.id,
        relation_type="tested_by",
        to_entity_id=target.id,
        confidence=0.9 if strategy == "exact_name" else 0.6,
        evidence_chunk_ids=json.dumps([]),
        metadata_json=json.dumps({
            "strategy": strategy,
            "case_type": test_case.case_type,
            "case_priority": test_case.priority,
        }, ensure_ascii=False),
    )
    db.add(rel)
    db.flush()
    return rel


def _ensure_entity(
    db: Session,
    project_id: int,
    entity_key: str,
    entity_type: str,
    name: str,
) -> KnowledgeEntity | None:
    """Get or create a KnowledgeEntity. Returns existing if found."""
    entity = db.scalar(
        select(KnowledgeEntity).where(
            KnowledgeEntity.project_id == project_id,
            KnowledgeEntity.entity_key == entity_key,
        )
    )
    if entity:
        return entity

    entity = KnowledgeEntity(
        project_id=project_id,
        entity_type=entity_type,
        entity_key=entity_key,
        name=name,
        description=f"{entity_type}: {name}",
        confidence=1.0 if entity_type == "test_case" else 0.8,
    )
    db.add(entity)
    db.flush()
    return entity


# ── Batch Linking ──

def link_all_modules(
    db: Session,
    *,
    release_bundle_id: int,
    project_id: int,
    version: str = "",
    dry_run: bool = False,
) -> dict[int, LinkingResult]:
    """Link test cases to ALL modules in a release bundle.

    Returns dict of module_id → LinkingResult.
    """
    modules = list(
        db.scalars(
            select(RequirementModule).where(
                RequirementModule.release_bundle_id == release_bundle_id,
                RequirementModule.node_type.in_(["module", "page"]),
            )
        ).all()
    )

    if not modules:
        logger.warning("No modules found in bundle #%d for linking", release_bundle_id)
        return {}

    # Load all active test cases for the project
    test_cases = list(
        db.scalars(
            select(TestCase).where(
                TestCase.project_id == project_id,
                TestCase.is_deleted == False,  # noqa: E712
                TestCase.status == "active",
            )
        ).all()
    )

    if not test_cases:
        logger.warning("No active test cases found for project #%d", project_id)
        return {}

    results: dict[int, LinkingResult] = {}
    for module in modules:
        result = link_test_cases_to_module(
            db,
            module=module,
            test_cases=test_cases,
            project_id=project_id,
            version=version,
            dry_run=dry_run,
        )
        results[module.id] = result

    total_linked = sum(r.linked_count for r in results.values())
    total_relations = sum(r.relations_created for r in results.values())
    logger.info(
        "Batch linking complete: %d modules, %d cases linked, %d relations created",
        len(modules), total_linked, total_relations,
    )
    return results


# ── Coverage Summary ──

def get_module_test_summary(
    db: Session,
    *,
    module_id: int,
    project_id: int,
    version: str = "",
) -> ModuleTestSummary:
    """Get test coverage summary for a module."""
    module = db.get(RequirementModule, module_id)
    if not module:
        return ModuleTestSummary(module_id=module_id, module_name="unknown")

    summary = ModuleTestSummary(
        module_id=module_id,
        module_name=module.name,
    )

    # Find tested_by relations from this module's entity
    module_key = _module_entity_key(project_id, module.name, version)
    entity = db.scalar(
        select(KnowledgeEntity).where(
            KnowledgeEntity.project_id == project_id,
            KnowledgeEntity.entity_key == module_key,
        )
    )

    if not entity:
        return summary

    relations = list(
        db.scalars(
            select(KnowledgeRelation).where(
                KnowledgeRelation.project_id == project_id,
                KnowledgeRelation.from_entity_id == entity.id,
                KnowledgeRelation.relation_type == "tested_by",
            )
        ).all()
    )

    summary.total_test_cases = len(relations)

    # Load test cases for classification
    target_entity_ids = [r.to_entity_id for r in relations]
    if target_entity_ids:
        # Resolve test_case entities → TestCase records
        target_entities = list(
            db.scalars(
                select(KnowledgeEntity).where(
                    KnowledgeEntity.id.in_(target_entity_ids),
                )
            ).all()
        )
        case_ids = [
            int(e.entity_key.split(":")[-1])
            for e in target_entities
            if e.entity_key.split(":")[-1].isdigit()
        ]
        summary.linked_case_ids = case_ids

        if case_ids:
            cases = list(
                db.scalars(
                    select(TestCase).where(TestCase.id.in_(case_ids))
                ).all()
            )
            for tc in cases:
                if tc.case_type == "api":
                    summary.api += 1
                elif tc.case_type == "ui":
                    summary.automation += 1
                else:
                    summary.functional += 1

    # Coverage rate heuristic: pages with at least 1 case / total pages
    child_pages = list(
        db.scalars(
            select(RequirementModule).where(
                RequirementModule.parent_module_id == module_id,
                RequirementModule.node_type == "page",
            )
        ).all()
    )
    if child_pages:
        summary.coverage_rate = min(1.0, summary.total_test_cases / max(1, len(child_pages)))

    return summary
