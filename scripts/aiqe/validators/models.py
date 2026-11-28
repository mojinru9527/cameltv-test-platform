"""Gate 校验结果模型。

每个 validator 只做一件事：读取一类原始事实并返回 ``GateCheck``。
validator 不允许修改输入、不允许把缺失证据折算成 PASS。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from statuses import FAIL, NOT_PROVEN, PASS, aggregate, normalize


@dataclass(slots=True)
class GateCheck:
    status: str = NOT_PROVEN
    reasons: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.status = normalize(self.status)
        self.reasons = [str(item) for item in self.reasons if str(item).strip()]
        self.evidence_refs = [str(item) for item in self.evidence_refs if str(item).strip()]
        self.notes = [str(item) for item in self.notes if str(item).strip()]

    @classmethod
    def ok(cls, reason: str = "", *, evidence: list[str] | None = None) -> "GateCheck":
        return cls(PASS, [reason] if reason else [], list(evidence or []))

    @classmethod
    def fail(cls, reason: str, *, evidence: list[str] | None = None) -> "GateCheck":
        return cls(FAIL, [reason], list(evidence or []))

    @classmethod
    def unproven(cls, reason: str, *, evidence: list[str] | None = None) -> "GateCheck":
        return cls(NOT_PROVEN, [reason], list(evidence or []))

    def add(self, reason: str, *, demote_to: str = NOT_PROVEN) -> "GateCheck":
        """追加一条阻断原因，并把状态降到不超过 ``demote_to``。"""
        if str(reason).strip():
            self.reasons.append(str(reason))
            if demote_to:
                self.demote(demote_to)
        return self

    def note(self, reason: str) -> "GateCheck":
        """追加说明，不改变状态，也不进入 blocking 列表。"""
        if str(reason).strip():
            self.notes.append(str(reason))
        return self

    def demote(self, status: str) -> "GateCheck":
        """只允许向更严重方向降级，避免后续检查把 FAIL 改回 PASS。"""
        merged = aggregate([self.status, status], empty=NOT_PROVEN)
        self.status = merged
        return self

    def merge(self, other: "GateCheck") -> "GateCheck":
        self.status = aggregate([self.status, other.status], empty=NOT_PROVEN)
        self.reasons.extend(other.reasons)
        for note in other.notes:
            if note not in self.notes:
                self.notes.append(note)
        for ref in other.evidence_refs:
            if ref not in self.evidence_refs:
                self.evidence_refs.append(ref)
        return self

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reasons": list(self.reasons),
            "notes": list(self.notes),
            "evidence_refs": list(self.evidence_refs),
        }


def combine(*checks: GateCheck, empty_reason: str = "无可用证据") -> GateCheck:
    if not checks:
        return GateCheck.unproven(empty_reason)
    result = GateCheck(PASS, [])
    for check in checks:
        result.merge(check)
    return result


__all__ = ["GateCheck", "combine"]
