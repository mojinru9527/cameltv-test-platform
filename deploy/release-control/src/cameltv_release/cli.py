"""Command-line checks for release-control contracts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from cameltv_release.contracts import ReleaseManifest


_MANIFEST_SCHEMA_NAME = "release-manifest.v1.schema.json"


def generated_schemas() -> dict[str, dict[str, object]]:
    """Return the schemas that are part of the public core contract."""
    return {_MANIFEST_SCHEMA_NAME: ReleaseManifest.model_json_schema()}


def schema_check(schema_dir: Path) -> list[Path]:
    """Return checked-in schema paths whose parsed JSON differs from the models."""
    drifted: list[Path] = []
    for name, expected in generated_schemas().items():
        path = schema_dir / name
        try:
            actual = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            drifted.append(path)
            continue
        if actual != expected:
            drifted.append(path)
    return drifted


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CamelTv release-control checks")
    parser.add_argument("command", choices=["schema-check"])
    parser.add_argument("--schema-dir", type=Path, default=Path(__file__).parents[2] / "schemas")
    args = parser.parse_args(argv)
    drifted = schema_check(args.schema_dir)
    if drifted:
        for path in drifted:
            print(f"schema drift: {path}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
