"""AITDE V3.2 data strategies (V32-005..V32-008).

Each strategy turns a data requirement + a source into a *provision spec*
(set of entities + compensation) while enforcing policy. Strategies do not
touch real systems themselves; execution is orchestrated by the fixture runtime.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from app.modules.aitde.data.models import DataRequirement, DataSource


@dataclass
class EntitySpec:
    entity_type: str
    logical_key: str
    physical_ref: dict[str, Any]
    created_by_fixture: bool
    cleanup_action: dict[str, Any] | None = None


@dataclass
class BuildResult:
    entities: list[EntitySpec] = field(default_factory=list)
    risk_note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "entities": [asdict(e) for e in self.entities],
            "risk_note": self.risk_note,
        }


class BaseBuilder:
    """Base strategy. Concrete builders implement ``build`` with policy guard."""

    def build(
        self,
        source: DataSource | None,
        requirement: DataRequirement,
        environment_id: int | None,
        project_id: int,
    ) -> BuildResult:
        raise NotImplementedError

    @staticmethod
    def _requirements_of(source: DataSource | None) -> str:
        return source.source_type if source else "NONE"
