"""AITDE V3.2 data strategy package (V32-005..V32-008).

Strategy registry mapping a plan strategy to its builder. Builders only produce
provision specs + policy guard — they never touch real systems on their own.
"""
from __future__ import annotations

from app.modules.aitde.common.enums import DataPlanStrategy
from app.modules.aitde.data.strategies.api_builder import ApiDataBuilder
from app.modules.aitde.data.strategies.base import BaseBuilder
from app.modules.aitde.data.strategies.db_fixture_builder import DbFixtureBuilder
from app.modules.aitde.data.strategies.existing_finder import ExistingDataFinder
from app.modules.aitde.data.strategies.workflow_builder import WorkflowDataBuilder

_BUILDERS = {
    DataPlanStrategy.EXISTING.value: ExistingDataFinder,
    DataPlanStrategy.API_BUILDER.value: ApiDataBuilder,
    DataPlanStrategy.DB_FIXTURE.value: DbFixtureBuilder,
    DataPlanStrategy.WORKFLOW.value: WorkflowDataBuilder,
}


def get_builder(strategy: str) -> BaseBuilder:
    cls = _BUILDERS.get(strategy)
    if cls is None:
        raise KeyError(strategy)
    return cls()
