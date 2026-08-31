"""V39-011 — Alembic migration graph structural invariants (offline, no DB).

These guards run entirely against the migration script directory and verify the
properties the V3.9 runbook depends on:

- exactly one head and one base (no forked / divergent heads);
- every ``down_revision`` points at an existing revision (no dangling edge);
- every revision is reachable from the single base AND from the single head
  (no cycles / orphans / unreachable branches);
- the base terminates the chain (``down_revision is None``);
- every migration defines an ``upgrade()`` / ``downgrade()``.

Merge revisions are ALLOWED (Alembic supports ``down_revision`` tuples) as long
as they converge to a single head — that is exactly what the single-head +
reachability checks enforce. They deliberately do NOT touch a database, so they
stay deterministic and fast. The actual upgrade / rollback drill (upgrade head
then downgrade on a temp DB) is covered separately in ``test_rollback_drill.py``
and gated on a DB being available.
"""
from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


def _script_directory() -> ScriptDirectory:
    backend_root = Path(__file__).resolve().parents[3]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    return ScriptDirectory.from_config(config)


def _down_edges(revision) -> list[str]:
    """The list of parent revision ids for a revision (empty if base)."""
    down = revision.down_revision
    if down is None:
        return []
    if isinstance(down, str):
        return [down]
    return list(down)


def _all_revisions() -> dict[str, object]:
    """Map revision id -> revision object, revealing the whole graph."""
    sd = _script_directory()
    return {revision.revision: revision for revision in sd.walk_revisions()}


def test_exactly_one_head() -> None:
    sd = _script_directory()
    heads = sd.get_heads()
    assert len(heads) == 1, f"expected a single Alembic head, got {heads}"


def test_exactly_one_base() -> None:
    sd = _script_directory()
    bases = sd.get_bases()
    assert len(bases) == 1, f"expected a single Alembic base, got {bases}"


def test_down_revisions_reference_existing_revisions() -> None:
    """.down_revision values must all resolve to an existing revision id."""
    revisions = _all_revisions()
    dangling = []
    for rev_id, revision in revisions.items():
        for item in _down_edges(revision):
            if item not in revisions:
                dangling.append(f"{rev_id} -> {item}")
    assert dangling == [], f"down_revision references unknown revision: {dangling}"


def test_all_revisions_reachable_from_head() -> None:
    """Following down_revision edges from the head must cover every revision."""
    sd = _script_directory()
    revisions = _all_revisions()
    head = sd.get_heads()[0]

    seen: set[str] = set()
    stack = [head]
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        stack.extend(_down_edges(revisions[current]))

    assert seen == set(revisions), (
        f"revisions unreachable from head: {sorted(set(revisions) - seen)}"
    )


def test_all_revisions_reachable_from_base() -> None:
    """Following up-edges from the base must cover every revision (full chain)."""
    sd = _script_directory()
    revisions = _all_revisions()
    base = sd.get_bases()[0]

    children: dict[str, list[str]] = {}
    for rev_id, revision in revisions.items():
        for item in _down_edges(revision):
            children.setdefault(item, []).append(rev_id)

    seen: set[str] = set()
    stack = [base]
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        stack.extend(children.get(current, []))

    assert seen == set(revisions), (
        f"revisions unreachable from base: {sorted(set(revisions) - seen)}"
    )


def test_base_terminates_chain() -> None:
    sd = _script_directory()
    base = sd.get_bases()[0]
    assert sd.get_revision(base).down_revision is None, (
        f"base revision {base} must have down_revision None"
    )


def test_every_revision_has_an_upgrade_and_downgrade() -> None:
    """Each migration must define an idempotent-``upgrade()`` + ``downgrade()``.

    We only assert callables are present; whether a downgrade is safe to run is
    the job of ``test_rollback_drill.py``.
    """
    revisions = _all_revisions()
    missing = [
        rev_id
        for rev_id, revision in revisions.items()
        if not callable(getattr(revision.module, "upgrade", None))
        or not callable(getattr(revision.module, "downgrade", None))
    ]
    assert missing == [], f"migrations missing upgrade/downgrade: {missing}"
