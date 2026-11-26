"""V16-024/P1-9：从干净 commit 构建的镜像采集可复核证据。

产出
----
- `docs/aiqe/v1.6/evidence/image-build.json`：image id、tar sha256（等价内容 digest）、
  size、commit、构建 Dockerfile、`sqlglot` 版本（修复运行时挂载问题的证明）；
- `docs/aiqe/v1.6/evidence/image-requirements-frozen.txt`：镜像内 `pip freeze`；
- `docs/aiqe/v1.6/evidence/image-sbom.cdx.json`：`docker scout sbom` 可用时输出，
  否则 `sbom_status=unavailable` 并保留依赖清单（不伪造 SBOM）。

用法
----
    docker build -f test-platform-v2/backend/Dockerfile --target api -t cameltv-aiqe-api:<sha> .
    python scripts/aiqe/capture_image_evidence.py --image cameltv-aiqe-api:<sha>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "docs/aiqe/v1.6/evidence"
DEFAULT_OUTPUT = EVIDENCE / "image-build.json"


def _run(command: list[str], *, timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_head() -> str:
    result = _run(["git", "rev-parse", "HEAD"])
    return result.stdout.strip() if result.returncode == 0 else ""


def capture(image: str, output: Path) -> dict:
    inspect = _run(["docker", "image", "inspect", image])
    if inspect.returncode != 0:
        raise RuntimeError(f"镜像不存在或 Docker 不可用: {inspect.stderr[:300]}")
    info = json.loads(inspect.stdout)[0]
    image_id = str(info.get("Id") or "")
    size = int(info.get("Size") or 0)
    created = str(info.get("Created") or "")

    sqlglot = _run(
        [
            "docker",
            "run",
            "--rm",
            "--entrypoint",
            "python",
            image,
            "-c",
            "import sqlglot; print(sqlglot.__version__)",
        ]
    )
    sqlglot_version = sqlglot.stdout.strip() if sqlglot.returncode == 0 else ""
    frozen = _run(["docker", "run", "--rm", "--entrypoint", "pip", image, "freeze"])
    frozen_text = frozen.stdout if frozen.returncode == 0 else ""

    output.parent.mkdir(parents=True, exist_ok=True)
    frozen_path = output.parent / "image-requirements-frozen.txt"
    if frozen_text:
        frozen_path.write_text(frozen_text, encoding="utf-8", newline="\n")

    sbom_path = output.parent / "image-sbom.cdx.json"
    scout = _run(
        ["docker", "scout", "sbom", "--format", "cyclonedx", "--output", str(sbom_path), image],
        timeout=900,
    )
    sbom_ok = scout.returncode == 0 and sbom_path.exists() and sbom_path.stat().st_size > 0
    if not sbom_ok and sbom_path.exists():
        sbom_path.unlink()

    tar_sha256 = ""
    with tempfile.TemporaryDirectory() as tmp:
        tar_path = Path(tmp) / "image.tar"
        save = _run(["docker", "save", "-o", str(tar_path), image], timeout=1800)
        if save.returncode == 0 and tar_path.exists():
            tar_sha256 = _sha256_file(tar_path)

    docker_version = _run(["docker", "version", "--format", "{{.Server.Version}}"]).stdout.strip()
    report = {
        "schema_version": "1.0",
        "artifact_kind": "image-build",
        "generated_at": datetime.now(UTC).isoformat(),
        "commit": _git_head(),
        "image": image,
        "image_id": image_id,
        "image_tar_sha256": tar_sha256,
        "size_bytes": size,
        "created": created,
        "dockerfile": "test-platform-v2/backend/Dockerfile",
        "target": "api",
        "sqlglot_version": sqlglot_version,
        "sqlglot_import_ok": bool(sqlglot_version),
        "frozen_dependencies": frozen_path.name if frozen_text else "",
        "sbom_status": "captured" if sbom_ok else "unavailable",
        "sbom_file": sbom_path.name if sbom_ok else "",
        "docker_server_version": docker_version,
        "status": "PROVEN" if sqlglot_version and tar_sha256 else "NOT_PROVEN",
    }
    return report


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):  # pragma: no cover
            pass
    parser = argparse.ArgumentParser(description="采集镜像构建证据（digest/SBOM/依赖）")
    parser.add_argument("--image", required=True)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)
    try:
        report = capture(args.image, Path(args.output))
    except Exception as exc:  # noqa: BLE001
        print(f"::error::[image-evidence] {type(exc).__name__}: {exc}")
        return 1
    Path(args.output).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps({"status": report["status"], "sqlglot": report["sqlglot_version"]}, ensure_ascii=False))
    return 0 if report["status"] == "PROVEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
