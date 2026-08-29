"""AITDE V3.3 semantic locator resolution (V33-004).

Resolves a semantic locator to a normalized selector descriptor using the plan's
priority order: data-testid → role+accessible name → stable label → stable
semantic text → CSS (last). Visual-coordinate clicks are never the default
regression strategy.
"""
from __future__ import annotations

from typing import Any


class SemanticLocatorResolver:
    PRIORITY = ("data-testid", "role", "label", "text", "css")

    def resolve(self, locator: dict[str, Any]) -> dict[str, Any]:
        """Return ``{"strategy": ..., "selector": ...}`` for a semantic locator."""
        if not isinstance(locator, dict):
            return {"strategy": "css", "selector": str(locator)}

        # Direct strategy selector (already normalized).
        if locator.get("strategy") and locator.get("selector") is not None:
            return {"strategy": locator["strategy"], "selector": locator["selector"]}

        if locator.get("data-testid"):
            return {"strategy": "data-testid", "selector": locator["data-testid"]}

        role = locator.get("role")
        if role:
            name = locator.get("name")
            selector = f"role={role}"
            if name:
                selector += f'[name="{name}"]'
            return {"strategy": "role", "selector": selector}

        if locator.get("label"):
            return {"strategy": "label", "selector": locator["label"]}

        if locator.get("text"):
            return {"strategy": "text", "selector": locator["text"]}

        return {"strategy": "css", "selector": ""}

    @staticmethod
    def priority_order() -> list[str]:
        return list(SemanticLocatorResolver.PRIORITY)
