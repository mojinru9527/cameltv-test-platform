"""Phase 0 baseline collector for the AI local-first optimization.

The collector is read-only and intentionally omits credentials. It records the
current provider/embedding posture, runtime-package signals and exact-cache
stats so later Phase 2-4 changes can be compared against a real baseline.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings  # noqa: E402
from app.core.db import SessionLocal  # noqa: E402
from app.services.ai_gateway.cache import exact_cache_stats  # noqa: E402


def _runtime_signals() -> dict:
    dockerfile = (BACKEND_DIR / "Dockerfile").read_text(encoding="utf-8", errors="replace")
    checks = {
        "node_runtime": "npm install -g" in dockerfile,
        "dsh_runtime": "@deepseek-ai/dsh" in dockerfile,
        "playwright_chromium": "playwright install" in dockerfile,
        "ffmpeg": "ffmpeg" in dockerfile,
        "fastembed": "fastembed" in (BACKEND_DIR / "requirements.txt").read_text(encoding="utf-8", errors="replace"),
    }
    return {"signals": checks, "detected_count": sum(1 for value in checks.values() if value)}


def _frontend_signals() -> dict:
    dist = REPO_ROOT / "test-platform-v2" / "frontend" / "dist" / "assets"
    if not dist.is_dir():
        return {"dist_present": False, "asset_count": 0, "total_bytes": 0, "largest_bytes": 0}
    files = [path for path in dist.iterdir() if path.is_file()]
    sizes = [path.stat().st_size for path in files]
    return {
        "dist_present": True,
        "asset_count": len(files),
        "total_bytes": sum(sizes),
        "largest_bytes": max(sizes) if sizes else 0,
    }


def _cache_stats() -> dict:
    db = SessionLocal()
    try:
        return exact_cache_stats(db, 0)
    except Exception as exc:  # noqa: BLE001 - baseline must not fail on a fresh DB
        return {"available": False, "error": type(exc).__name__}
    finally:
        db.close()


def collect() -> dict:
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "provider": {
            "ai_enabled": bool(settings.ai_enabled),
            "api_base_url": settings.ai_api_base_url,
            "model": settings.ai_model,
            "exact_cache_enabled": bool(settings.ai_exact_cache_enabled),
            "exact_cache_ttl_seconds": int(settings.ai_exact_cache_ttl_seconds),
        },
        "embedding": {
            "model": settings.embedding_model,
            "dim": int(settings.embedding_dim),
            "cache_dir": settings.embedding_cache_dir,
            "rag_enabled": bool(settings.rag_enabled),
        },
        "runtime": _runtime_signals(),
        "frontend": _frontend_signals(),
        "exact_cache": _cache_stats(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="")
    args = parser.parse_args()
    payload = collect()
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")
    sys.stdout.write(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

