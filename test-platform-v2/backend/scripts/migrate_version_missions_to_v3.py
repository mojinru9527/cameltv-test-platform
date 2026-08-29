"""Migrate legacy VersionMission rows to AITDE v3 Mission (V30-110, M4).

Conservative status mapping (never auto-mark CONTRACT_FROZEN / SCENARIO_READY /
ACCEPTED). Idempotent: rows whose ``legacy_version_mission_id`` already exists in
``missions`` are skipped. Supports ``--dry-run``.

Usage:
    python scripts/migrate_version_missions_to_v3.py [--dry-run]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.modules.aitde.common.enums import MissionStatus, SourceRole, SourceType  # noqa: E402
from app.modules.aitde.mission.models import Mission  # noqa: E402
from app.modules.aitde.sources.models import MissionSourceLink, SourceArtifact  # noqa: E402
from app.models.version_mission import VersionMission  # noqa: E402


def _status_map(row: VersionMission) -> str:
    """Conservative old-status → AITDE status mapping (M4.1)."""
    if row.status in ("draft", ""):
        return MissionStatus.DRAFT.value
    has_sources = bool(
        row.requirement_url or row.api_spec_url or row.requirement_doc_id
    )
    if has_sources:
        return MissionStatus.SOURCE_READY.value
    return MissionStatus.DRAFT.value


def migrate(db: Session, dry_run: bool = False) -> dict:
    planned = skipped = conflict = 0
    source_links = 0

    rows = list(db.scalars(select(VersionMission)).all())
    for row in rows:
        already = db.scalar(
            select(Mission).where(Mission.legacy_version_mission_id == row.id)
        )
        if already:
            skipped += 1
            continue
        if not row.project_id:
            skipped += 1
            continue

        key_exists = db.scalar(
            select(Mission).where(
                Mission.project_id == row.project_id,
                Mission.mission_key == row.mission_key,
            )
        )
        if key_exists:
            conflict += 1
            continue

        planned += 1
        if dry_run:
            continue

        mission = Mission(
            project_id=row.project_id,
            mission_key=row.mission_key,
            mission_type="VERSION",
            title=row.title,
            version_label=row.version,
            qa_owner_id=row.qa_owner_id,
            created_by=row.created_by,
            default_environment_id=row.environment_id,
            legacy_version_mission_id=row.id,
            status=_status_map(row),
        )
        db.add(mission)
        db.flush()

        # Requirement association (best-effort): link the requirement doc as a source
        if row.requirement_doc_id:
            artifact = db.scalar(
                select(SourceArtifact).where(
                    SourceArtifact.project_id == row.project_id,
                    SourceArtifact.source_type == SourceType.REQUIREMENT.value,
                )
            )
            if not artifact:
                artifact = SourceArtifact(
                    project_id=row.project_id,
                    source_type=SourceType.REQUIREMENT.value,
                    provider="requirement_doc",
                    name=f"需求文档 #{row.requirement_doc_id}",
                    created_by=row.created_by,
                )
                db.add(artifact)
                db.flush()
            linked = db.scalar(
                select(MissionSourceLink).where(
                    MissionSourceLink.mission_id == mission.id,
                    MissionSourceLink.artifact_id == artifact.id,
                )
            )
            if not linked:
                db.add(
                    MissionSourceLink(
                        mission_id=mission.id,
                        artifact_id=artifact.id,
                        role=SourceRole.REQUIREMENT.value,
                        is_primary=True,
                        created_by=row.created_by,
                    )
                )
                source_links += 1

    if not dry_run:
        db.commit()

    return {
        "planned": planned,
        "skipped": skipped,
        "conflict": conflict,
        "source_links": source_links,
        "total": len(rows),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate VersionMission → AITDE Mission"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Report counts without writing"
    )
    args = parser.parse_args()

    from app.core.db import SessionLocal

    import app.models  # noqa: F401  registers all models
    import app.modules.aitde.mission.models  # noqa: F401

    db = SessionLocal()
    try:
        result = migrate(db, dry_run=args.dry_run)
    finally:
        db.close()
    print(
        f"planned={result['planned']} skipped={result['skipped']} "
        f"conflict={result['conflict']} source_links={result['source_links']} "
        f"total={result['total']}"
    )


if __name__ == "__main__":
    main()
