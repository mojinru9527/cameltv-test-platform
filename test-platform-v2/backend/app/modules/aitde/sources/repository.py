"""Source repository (V30-020/V30-025)."""
from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.aitde.sources.adapters import SourceFragmentDraft, stable_content_hash
from app.modules.aitde.sources.models import (
    MissionSourceLink,
    SourceArtifact,
    SourceFragment,
)


def create_artifact(
    db: Session,
    data: dict[str, Any],
    project_id: int,
    user_id: int,
) -> SourceArtifact:
    row = SourceArtifact(project_id=project_id, created_by=user_id, **data)
    db.add(row)
    db.flush()
    return row


def get_artifact(
    db: Session, artifact_id: int, project_id: int
) -> SourceArtifact | None:
    return db.scalar(
        select(SourceArtifact).where(
            SourceArtifact.id == artifact_id, SourceArtifact.project_id == project_id
        )
    )


def list_artifacts_for_mission(db: Session, mission_id: int) -> list[SourceArtifact]:
    """Return artifacts linked to a mission, ordered by link id."""
    rows = db.scalars(
        select(SourceArtifact)
        .join(MissionSourceLink, MissionSourceLink.artifact_id == SourceArtifact.id)
        .where(MissionSourceLink.mission_id == mission_id)
        .order_by(MissionSourceLink.id.asc())
    ).all()
    return list(rows)


def link_artifact_to_mission(
    db: Session,
    mission_id: int,
    artifact_id: int,
    role: str,
    user_id: int,
    is_primary: bool = False,
) -> MissionSourceLink:
    row = MissionSourceLink(
        mission_id=mission_id,
        artifact_id=artifact_id,
        role=role,
        created_by=user_id,
        is_primary=is_primary,
    )
    db.add(row)
    db.flush()
    return row


def get_link(
    db: Session, mission_id: int, artifact_id: int
) -> MissionSourceLink | None:
    return db.scalar(
        select(MissionSourceLink).where(
            MissionSourceLink.mission_id == mission_id,
            MissionSourceLink.artifact_id == artifact_id,
        )
    )


def list_fragments(db: Session, artifact_id: int) -> list[SourceFragment]:
    rows = db.scalars(
        select(SourceFragment)
        .where(SourceFragment.artifact_id == artifact_id)
        .order_by(SourceFragment.sequence.asc())
    ).all()
    return list(rows)


def replace_fragments(
    db: Session, artifact_id: int, drafts: list[SourceFragmentDraft]
) -> list[SourceFragment]:
    for old in db.scalars(
        select(SourceFragment).where(SourceFragment.artifact_id == artifact_id)
    ).all():
        db.delete(old)
    db.flush()

    fragments: list[SourceFragment] = []
    for draft in drafts:
        fragments.append(
            SourceFragment(
                artifact_id=artifact_id,
                fragment_key=draft.fragment_key,
                title=draft.title,
                text=draft.text,
                location_json=draft.location,
                content_hash=stable_content_hash(draft.text),
                sequence=draft.sequence or len(fragments) + 1,
            )
        )
    db.add_all(fragments)
    db.flush()
    return fragments


def count_fragments(db: Session, artifact_id: int) -> int:
    return db.scalar(
        select(func.count(SourceFragment.id)).where(
            SourceFragment.artifact_id == artifact_id
        )
    ) or 0
