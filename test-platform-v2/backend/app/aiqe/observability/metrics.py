"""V16-024：AIQE Prometheus 指标注册表（低基数、可测试、无外部依赖）。

- 指标名固定白名单（规格 §8.2）；
- 标签只允许低基数 key（project_id/status/driver/outcome/reason/tool/agent/platform）；
- 标签值禁止 URL/query/SQL/Token 等敏感内容，超长截断并替换为 redacted；
- 成功/失败/拒绝都可计数，禁止把用户输入全文写入 label。
"""
from __future__ import annotations

import hashlib
import math
import re
from collections import defaultdict
from threading import Lock
from typing import Any
from collections.abc import Mapping

REQUIRED_METRICS: tuple[str, ...] = (
    "aiqe_run_queued_age_seconds",
    "aiqe_job_pending_age_seconds",
    "aiqe_job_lease_expired_total",
    "aiqe_job_fencing_rejected_total",
    "aiqe_run_terminal_latency_seconds",
    "aiqe_run_without_job_total",
    "aiqe_node_without_assertion_total",
    "aiqe_reconciler_repair_total",
    "aiqe_target_policy_denied_total",
    "aiqe_target_policy_unavailable_total",
    "aiqe_ssrf_blocked_total",
    "aiqe_secret_canary_detected_total",
    "aiqe_secret_handle_resolve_denied_total",
    "aiqe_cross_project_access_denied_total",
    "aiqe_db_query_policy_denied_total",
    "aiqe_agent_task_failure_total",
    "aiqe_agent_tool_unavailable_total",
    "aiqe_agent_invalid_evidence_total",
    "aiqe_benchmark_gate_rejected_total",
    "aiqe_learning_publish_total",
    "aiqe_learning_rollback_total",
)
ALLOWED_LABELS = frozenset(
    {"project_id", "status", "driver", "outcome", "reason", "tool", "agent", "platform", "env"}
)
SENSITIVE_LABEL_RE = re.compile(
    r"(https?://|token|password|secret|select\s|insert\s|update\s|delete\s|bearer\s)", re.I
)
VALUE_MAX_LEN = 64


def _sanitize_labels(labels: Mapping[str, Any] | None) -> dict[str, str]:
    clean: dict[str, str] = {}
    for key, value in (labels or {}).items():
        name = str(key)
        if name not in ALLOWED_LABELS:
            continue
        text = str(value)
        if SENSITIVE_LABEL_RE.search(text) or len(text) > VALUE_MAX_LEN:
            text = "redacted"
        clean[name] = text
    return clean


class MetricsRegistry:
    def __init__(self) -> None:
        self._counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = defaultdict(float)
        self._gauges: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}
        self._histograms: dict[tuple[str, tuple[tuple[str, str], ...]], list[float]] = defaultdict(list)
        self._lock = Lock()

    @staticmethod
    def _key(name: str, labels: Mapping[str, Any] | None) -> tuple:
        clean = _sanitize_labels(labels)
        return str(name), tuple(sorted(clean.items()))

    def inc(self, name: str, labels: Mapping[str, Any] | None = None, value: float = 1.0) -> None:
        if not str(name).startswith("aiqe_"):
            raise ValueError("AIQE metric 名称必须以 aiqe_ 开头")
        with self._lock:
            self._counters[self._key(name, labels)] += float(value)

    def set_gauge(self, name: str, value: float, labels: Mapping[str, Any] | None = None) -> None:
        with self._lock:
            self._gauges[self._key(name, labels)] = float(value)

    def observe(self, name: str, value: float, labels: Mapping[str, Any] | None = None) -> None:
        with self._lock:
            self._histograms[self._key(name, labels)].append(float(value))

    def value(self, name: str, labels: Mapping[str, Any] | None = None) -> float:
        key = self._key(name, labels)
        with self._lock:
            if key in self._counters:
                return self._counters[key]
            if key in self._gauges:
                return self._gauges[key]
            return sum(self._histograms.get(key, [])) if key in self._histograms else 0.0

    def count(self, name: str, labels: Mapping[str, Any] | None = None) -> int:
        key = self._key(name, labels)
        return len(self._histograms.get(key, []))

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()

    def render(self) -> str:
        lines: list[str] = []
        with self._lock:
            for (name, labels), value in sorted(self._counters.items()):
                lines.append(f"{name}{_label_text(labels)} {value:g}")
            for (name, labels), value in sorted(self._gauges.items()):
                lines.append(f"{name}{_label_text(labels)} {value:g}")
            for (name, labels), values in sorted(self._histograms.items()):
                if not values:
                    continue
                total = math.fsum(values)
                lines.append(f"{name}_count{_label_text(labels)} {len(values)}")
                lines.append(f"{name}_sum{_label_text(labels)} {total:g}")
        return "\n".join(lines) + ("\n" if lines else "")


def _label_text(labels: tuple[tuple[str, str], ...]) -> str:
    if not labels:
        return ""
    body = ",".join(f'{key}="{value}"' for key, value in labels)
    return "{" + body + "}"


metrics = MetricsRegistry()


def token_fingerprint(token: str) -> str:
    """指标端点 token 只比较指纹，避免日志泄露。"""
    return hashlib.sha256(str(token).encode()).hexdigest()[:12]


__all__ = [
    "ALLOWED_LABELS",
    "REQUIRED_METRICS",
    "MetricsRegistry",
    "metrics",
    "token_fingerprint",
]
