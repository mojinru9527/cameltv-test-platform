"""PromptLoader (V30-081).

Prompt versions are derived from file name + content hash so any prompt change
produces a new immutable version.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "intelligence" / "prompts"


@dataclass
class PromptVersion:
    name: str
    version: str
    content: str


class PromptLoader:
    def load(self, name: str) -> PromptVersion:
        path = _PROMPTS_DIR / f"{name}.txt"
        if not path.exists():
            raise FileNotFoundError(f"Prompt not found: {name}")
        content = path.read_text(encoding="utf-8")
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]
        version = f"{path.name}:{digest}"
        return PromptVersion(name=name, version=version, content=content)
