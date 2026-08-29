"""AITDE V3.3 Healing guard (V33-011).

Only produces Action-only diffs as a Proposal. Any diff that changes an Oracle or
the Contract is rejected wholesale and recorded for audit — healing can never
mutate the frozen contract.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Command drivers that carry an oracle reference / contract-expectation.
_ORACLE_DRIVERS = {"assertion", "oracle"}


@dataclass
class HealingGuard:
    schema_version: str = "1.0"

    @staticmethod
    def _command_key(cmd: dict[str, Any]) -> Any:
        # Stable identity: driver + action + id (fallback to JSON stability).
        return (cmd.get("driver"), cmd.get("action"), cmd.get("id"))

    @staticmethod
    def _is_oracle_touching(cmd: dict[str, Any]) -> bool:
        return cmd.get("driver") in _ORACLE_DRIVERS

    def detect_mutation(self, before_ir: dict[str, Any], after_ir: dict[str, Any]) -> dict[str, Any]:
        """Diff two Command IR documents; report any Oracle/Contract mutation.

        Returns ``{"changed": bool, "oracle_mutation": bool, "diff": [...]}`.
        """
        before = {self._command_key(c): c for c in before_ir.get("commands", [])}
        after = {self._command_key(c): c for c in after_ir.get("commands", [])}

        all_keys = set(before) | set(after)
        diff: list[dict[str, Any]] = []
        oracle_mutation = False

        for key in sorted(all_keys, key=lambda k: (str(k[0]), str(k[1]), str(k[2]))):
            old = before.get(key)
            new = after.get(key)
            if old == new:
                continue
            change_type = "none"
            if new is None:
                change_type = "removed"
            elif old is None:
                change_type = "added"
            else:
                change_type = "modified"
            # A change to (or add/remove of) an oracle-touching command = mutation.
            if self._is_oracle_touching(old or {}) or self._is_oracle_touching(new or {}):
                oracle_mutation = True
            diff.append(
                {
                    "command": key[2],
                    "driver": key[0],
                    "action": key[1],
                    "change": change_type,
                    "oracle_touching": self._is_oracle_touching(old or {})
                    or self._is_oracle_touching(new or {}),
                }
            )
        return {"changed": len(diff) > 0, "oracle_mutation": oracle_mutation, "diff": diff}

    def create_proposal(
        self, before_ir: dict[str, Any], after_ir: dict[str, Any], reason: str
    ) -> dict[str, Any]:
        """Build an Action-only Healing Proposal; reject Oracle/Contract changes.

        Returns a proposal dict with ``status`` OPEN (action-only allowed) or the
        whole thing marked REJECTED when an oracle/contract mutation is present
        (recorded for audit; never applied).
        """
        result = self.detect_mutation(before_ir, after_ir)
        proposal_type = self._proposal_type(result)
        if result["oracle_mutation"]:
            return {
                "approved": False,
                "status": "REJECTED",
                "proposal_type": "NON_BUSINESS_ACTION",
                "reason": "oracle_contract_mutation",
                "before_json": before_ir,
                "after_json": after_ir,
                "audit": True,
            }
        return {
            "approved": True,
            "status": "OPEN",
            "proposal_type": proposal_type or "NON_BUSINESS_ACTION",
            "reason": reason,
            "before_json": before_ir,
            "after_json": after_ir,
            "audit": False,
        }

    @staticmethod
    def _proposal_type(diff_result: dict[str, Any]) -> str | None:
        """Best-effort classify an action-only diff (locator/wait/navigation)."""
        for entry in diff_result.get("diff", []):
            action = entry.get("action")
            if action == "click":
                return "LOCATOR"
            if action == "wait_for":
                return "WAIT"
            if action == "goto":
                return "NAVIGATION"
        return None
