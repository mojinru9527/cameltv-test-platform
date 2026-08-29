"""AITDE V3.3 ActionPlanner (V33-003).

Turns a scenario's ``when_model`` + frozen oracles into a Command IR candidate.
Deterministic in V33-003 (no LLM); the hard guard ``reject_oracle_mutation``
blocks any candidate that references a new/changed oracle, so a planner output
can never mutate the Frozen Contract.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.modules.aitde.command import DEFAULT_REGISTRY


@dataclass
class ActionPlanner:
    schema_version: str = "1.0"

    def plan(
        self,
        when_model: dict[str, Any],
        oracles: list[dict[str, Any]],
        route: str = "/",
    ) -> dict[str, Any]:
        """Build a Command IR candidate: navigate → act → assert each frozen oracle."""
        commands: list[dict[str, Any]] = []
        seq = 1

        commands.append(
            {"id": str(seq), "driver": "browser", "action": "goto", "input": {"route": route}}
        )
        seq += 1

        action = when_model.get("action")
        if action:
            commands.append(
                {
                    "id": str(seq),
                    "driver": "browser",
                    "action": "click",
                    "input": {"locator": {"strategy": "role", "role": "button", "name": str(action)}},
                }
            )
            seq += 1

        for oracle in oracles:
            key = oracle.get("oracle_key")
            if not key:
                continue
            commands.append(
                {"id": str(seq), "driver": "assertion", "action": "evaluate", "input": {"oracle_key": key}}
            )
            seq += 1

        ir = {"schema_version": self.schema_version, "commands": commands}
        return ir

    def plan_and_validate(
        self, when_model: dict[str, Any], oracles: list[dict[str, Any]], route: str = "/"
    ) -> dict[str, Any]:
        """Plan, then validate against the Command schema registry.

        Raises ValueError if the candidate is schema-invalid; never emits SQL or
        arbitrary code.
        """
        ir = self.plan(when_model, oracles, route)
        errors = DEFAULT_REGISTRY.validate(ir)
        if errors:
            raise ValueError(f"Command IR 校验失败：{errors}")
        return ir

    @staticmethod
    def reject_oracle_mutation(ir: dict[str, Any], oracles: list[dict[str, Any]]) -> bool:
        """True if the IR references an oracle not in the scenario's frozen set.

        Such a candidate represents an Oracle mutation and must be rejected
        entirely (with audit) rather than applied.
        """
        existing = {str(o.get("oracle_key")) for o in oracles if o.get("oracle_key")}
        for command in ir.get("commands", []):
            if command.get("driver") == "assertion":
                key = (command.get("input") or {}).get("oracle_key")
                if key and str(key) not in existing:
                    return True
        return False
