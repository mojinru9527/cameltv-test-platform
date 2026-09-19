"""证据包校验（Batch 261 / B4-1）。

回答两个问题：
  1. 这个证据包**被动过吗**（逐文件 sha256 与 manifest 比对）；
  2. 按 09 方案的完整率口径，它**还缺什么必需证据**。

**收敛原则（Design §2）**：完整率判定**不新建第二套实现**——
必需证据清单来自既有 `app/modules/aitde/assertion/completeness.py`
（`required_evidence(adapter, oracle)` + `is_complete(present, required)`）。
本服务只做两件事：把外部证据包翻译成该策略能吃的输入，以及在判定前把
**篡改/缺失**的文件排除。

为什么必须排除：既有策略 V3.9-R1 已明确"A required evidence is COMPLETE only when the
artifact is physically usable — sanitized, hash-valid, non-empty, and confirmed present"。
若只在 verdict 上标 tampered 却仍把它计入必需证据，就会出现
"证据被改过、完整率仍 100%、放行结论照样成立"的荒唐结果。
"""
from __future__ import annotations

import hashlib

from app.modules.aitde.assertion import completeness
from app.modules.aitde.common.enums import AdapterType, EvidenceType, OracleType
from app.services import execution_evidence_store as store

MANIFEST_NAME = store.MANIFEST_NAME

# 文件名后缀 → EvidenceType。**本批唯一新增的口径**，其余全部复用既有策略。
FILE_TYPE_MAP: tuple[tuple[str, str], ...] = (
    ("request.json", EvidenceType.REQUEST.value),
    ("response.json", EvidenceType.RESPONSE.value),
    ("console.json", EvidenceType.CONSOLE.value),
    ("trace.zip", EvidenceType.PW_TRACE.value),
    ("screenshot.png", EvidenceType.SCREENSHOT.value),
    (".png", EvidenceType.SCREENSHOT.value),
)

# 汇总/清单类文件不是"证据类型"，不参与必需证据判定
_NOT_EVIDENCE = frozenset({MANIFEST_NAME, "results.json"})

# job.kind → (adapter_type, oracle_type)
_KIND_TO_ADAPTER_ORACLE: dict[str, tuple[str, str]] = {
    "api": (AdapterType.API.value, OracleType.API.value),
    "web": (AdapterType.UI.value, OracleType.UI.value),
}
_FALLBACK_ADAPTER_ORACLE = (AdapterType.MANUAL.value, OracleType.UI.value)


def evidence_type_for(name: str) -> str | None:
    """按后缀判定证据类型；汇总文件与未识别后缀返回 None（未识别项会显式出现在结果里）。"""
    lowered = (name or "").strip().lower()
    if not lowered or lowered in _NOT_EVIDENCE:
        return None
    for suffix, evidence_type in FILE_TYPE_MAP:
        if lowered.endswith(suffix):
            return evidence_type
    return None


def adapter_oracle_for_kind(kind: str) -> tuple[str, str]:
    """未知 kind 走保守回退（MANUAL/UI），避免"没识别的类型被当成已满足"。"""
    return _KIND_TO_ADAPTER_ORACLE.get((kind or "").strip().lower(), _FALLBACK_ADAPTER_ORACLE)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_bundle(job_id: int, attempt: int, *, kind: str) -> dict:
    """校验一个 (job, attempt) 证据包。`kind` 决定必需证据（api→REQUEST+RESPONSE，web→SCREENSHOT+CONSOLE）。"""
    manifest = store.load_manifest(job_id, attempt)
    adapter_type, oracle_type = adapter_oracle_for_kind(kind)
    required = completeness.required_evidence(adapter_type, oracle_type)

    if manifest is None:
        return {
            "job_id": job_id,
            "attempt": attempt,
            "verdict": "missing",
            "files": [],
            "tampered": [],
            "missing": [],
            "extra": [],
            "unclassified": [],
            "completeness": {
                "required": required,
                "present": [],
                "missing": list(required),
                "complete": False,
            },
            "reason": "该任务在这一轮尝试下没有证据包（manifest 不存在）",
        }

    directory = store.bundle_dir(job_id, attempt)
    files: list[dict] = []
    tampered: list[str] = []
    missing: list[str] = []
    unclassified: list[str] = []
    # 只有"完好且被识别"的文件才计入必需证据（Design §2）
    usable_types: set[str] = set()
    manifest_names: set[str] = set()

    for entry in manifest.get("files", []):
        name = str(entry.get("name") or "")
        manifest_names.add(name)
        evidence_type = evidence_type_for(name)
        path = directory / name
        if not path.exists():
            missing.append(name)
            files.append(
                {
                    "name": name,
                    "evidence_type": evidence_type,
                    "status": "missing",
                    "expected_sha256": entry.get("sha256"),
                    "actual_sha256": None,
                }
            )
            continue
        actual = _sha256(path.read_bytes())
        status = "ok" if actual == entry.get("sha256") else "tampered"
        if status == "tampered":
            tampered.append(name)
        elif evidence_type:
            usable_types.add(evidence_type)
        if evidence_type is None:
            unclassified.append(name)
        files.append(
            {
                "name": name,
                "evidence_type": evidence_type,
                "status": status,
                "expected_sha256": entry.get("sha256"),
                "actual_sha256": actual,
            }
        )

    extra = sorted(
        path.name
        for path in directory.iterdir()
        if path.is_file() and path.name not in manifest_names and path.name != MANIFEST_NAME
    )

    present = [evidence_type for evidence_type in required if evidence_type in usable_types]
    missing_types = [evidence_type for evidence_type in required if evidence_type not in usable_types]
    complete = completeness.is_complete(usable_types, required)

    if tampered:
        verdict = "tampered"
    elif missing:
        verdict = "missing"
    elif not complete:
        verdict = "incomplete"
    else:
        verdict = "verified"

    return {
        "job_id": job_id,
        "attempt": attempt,
        "verdict": verdict,
        "files": files,
        "tampered": tampered,
        "missing": missing,
        "extra": extra,
        "unclassified": unclassified,
        "completeness": {
            "required": list(required),
            "present": present,
            "missing": missing_types,
            "complete": complete,
        },
    }
