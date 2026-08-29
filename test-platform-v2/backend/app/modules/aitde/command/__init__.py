"""AITDE V3.3 Command IR schema registry (V33-001).

A Scenario's UI execution input is a declarative Command IR, never arbitrary
LLM code. The registry knows the allowed drivers / actions / input shapes and
schema versions, and rejects unknown commands deterministically.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CommandActionSpec:
    action: str
    # Required input keys (subset) for the action; extra keys are allowed.
    required_input: frozenset[str] = frozenset()
    has_input: bool = True


@dataclass(frozen=True)
class DriverSpec:
    driver: str
    actions: frozenset[str] = frozenset()

    def has_action(self, action: str) -> bool:
        return action in self.actions


@dataclass
class CommandSchemaRegistry:
    """Registers driver/action/schema-version and validates Command IR commands."""

    def __init__(self, schema_version: str = "1.0"):
        self.schema_version = schema_version
        self._drivers: dict[str, DriverSpec] = {}
        self._actions: dict[str, CommandActionSpec] = {}

    def register_driver(self, driver: str, actions: list[str]) -> None:
        self._drivers[driver] = DriverSpec(driver=driver, actions=frozenset(actions))

    def register_action(
        self,
        driver: str,
        action: str,
        required_input: list[str] | None = None,
        has_input: bool = True,
    ) -> None:
        self._actions[f"{driver}:{action}"] = CommandActionSpec(
            action=action,
            required_input=frozenset(required_input or []),
            has_input=has_input,
        )

    def known_drivers(self) -> list[str]:
        return sorted(self._drivers)

    # ── validation ────────────────────────────────────────────────────────
    def validate_command(self, command: dict[str, Any]) -> dict[str, Any]:
        """Return an error dict, or {} if the command is valid."""
        driver = command.get("driver")
        action = command.get("action")
        if not isinstance(driver, str) or driver not in self._drivers:
            return {"code": "unknown_driver", "driver": driver}
        if not isinstance(action, str) or not self._drivers[driver].has_action(action):
            return {"code": "unknown_action", "driver": driver, "action": action}

        spec = self._actions.get(f"{driver}:{action}")
        if spec is not None:
            raw_input = command.get("input")
            if spec.has_input and not isinstance(raw_input, dict):
                return {"code": "input_required", "driver": driver, "action": action}
            if isinstance(raw_input, dict):
                missing = [k for k in spec.required_input if k not in raw_input]
                if missing:
                    return {"code": "missing_input", "driver": driver, "action": action, "missing": missing}
        return {}

    def validate(self, ir: dict[str, Any]) -> list[dict[str, Any]]:
        """Validate a Command IR document; returns a list of validation errors."""
        errors: list[dict[str, Any]] = []
        if not isinstance(ir, dict):
            return [{"code": "ir_not_object"}]
        if ir.get("schema_version") != self.schema_version:
            errors.append(
                {"code": "schema_version_mismatch", "expected": self.schema_version, "actual": ir.get("schema_version")}
            )
        commands = ir.get("commands")
        if not isinstance(commands, list) or not commands:
            errors.append({"code": "commands_required"})
            return errors
        for i, cmd in enumerate(commands):
            if not isinstance(cmd, dict):
                errors.append({"code": "command_not_object", "index": i})
                continue
            err = self.validate_command(cmd)
            if err:
                errors.append({"code": "command_error", "index": i, **err})
        return errors


# ── default V3.3 registry ──────────────────────────────────────────────────
def default_registry() -> CommandSchemaRegistry:
    reg = CommandSchemaRegistry(schema_version="1.0")

    # browser driver (subset of §4 Browser Driver methods)
    reg.register_driver("browser", [
        "open_session", "goto", "click", "fill", "select", "upload",
        "wait_for", "capture_dom", "capture_screenshot", "capture_network", "close_session",
    ])
    reg.register_action("browser", "goto", required_input=["route"])
    reg.register_action("browser", "click", required_input=["locator"])
    reg.register_action("browser", "fill", required_input=["locator", "value"])
    reg.register_action("browser", "select", required_input=["locator", "value"])
    reg.register_action("browser", "wait_for", required_input=["locator"])
    reg.register_action("browser", "capture_dom", has_input=False)
    reg.register_action("browser", "capture_screenshot", has_input=False)
    reg.register_action("browser", "capture_network", has_input=False)
    reg.register_action("browser", "close_session", has_input=False)
    reg.register_action("browser", "open_session", required_input=["mode"])
    reg.register_action("browser", "upload", required_input=["locator", "file"])

    # data driver (V3.2 ensure)
    reg.register_driver("data", ["ensure"])
    reg.register_action("data", "ensure", required_input=["requirement_ref"])

    # api driver
    reg.register_driver("api", ["request"])
    reg.register_action("api", "request", required_input=["method", "path"])

    # assertion driver (deterministic oracle)
    reg.register_driver("assertion", ["evaluate"])
    reg.register_action("assertion", "evaluate", required_input=["oracle_key"])

    return reg


DEFAULT_REGISTRY = default_registry()
