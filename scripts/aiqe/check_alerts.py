"""V16-024：告警规则校验器（指标覆盖/严重级别/必填字段）。

用法：python scripts/aiqe/check_alerts.py [--file docs/aiqe/v1.6/observability/aiqe-alerts.yaml]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FILE = ROOT / "docs" / "aiqe" / "v1.6" / "observability" / "aiqe-alerts.yaml"
REQUIRED_METRICS = (
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
SEVERITIES = {"P0", "P1", "P2", "P3"}
METRIC_RE = re.compile(r"\b(aiqe_[a-zA-Z0-9_]+)")
SENSITIVE_RE = re.compile(r"(token\s*=|password\s*=|secret\s*=|BEGIN [A-Z ]+PRIVATE KEY)", re.I)


class AlertConfigError(ValueError):
    pass


def validate(document: dict) -> dict:
    groups = document.get("groups") if isinstance(document, dict) else None
    if not isinstance(groups, list) or not groups:
        raise AlertConfigError("groups 必须是非空数组")
    alerts: list[str] = []
    referenced: set[str] = set()
    for group in groups:
        if not isinstance(group, dict) or not group.get("name"):
            raise AlertConfigError("group 必须有 name")
        rules = group.get("rules")
        if not isinstance(rules, list) or not rules:
            raise AlertConfigError(f"group {group.get('name')} 没有 rules")
        for rule in rules:
            alert = str(rule.get("alert") or "").strip()
            expr = str(rule.get("expr") or "").strip()
            if not alert:
                raise AlertConfigError(f"group {group['name']}: rule 缺 alert")
            if alert in alerts:
                raise AlertConfigError(f"重复 alert: {alert}")
            if not expr:
                raise AlertConfigError(f"{alert}: expr 不能为空")
            if SENSITIVE_RE.search(expr):
                raise AlertConfigError(f"{alert}: expr 不得包含凭据")
            if not METRIC_RE.search(expr):
                raise AlertConfigError(f"{alert}: expr 必须引用 aiqe_ 指标")
            labels = rule.get("labels") or {}
            severity = str(labels.get("severity") or "").strip().upper()
            if severity not in SEVERITIES:
                raise AlertConfigError(f"{alert}: severity 必须是 {sorted(SEVERITIES)}")
            annotations = rule.get("annotations") or {}
            if not str(annotations.get("summary") or "").strip():
                raise AlertConfigError(f"{alert}: 缺 annotations.summary")
            if not str(rule.get("for") or "").strip():
                raise AlertConfigError(f"{alert}: 缺 for 窗口")
            for metric in METRIC_RE.findall(expr):
                for suffix in ("_bucket", "_count", "_sum"):
                    if metric.endswith(suffix):
                        metric = metric[: -len(suffix)]
                        break
                referenced.add(metric)
            alerts.append(alert)
    missing = sorted(set(REQUIRED_METRICS) - referenced)
    if missing:
        raise AlertConfigError(f"以下必需指标未被任何告警引用: {missing}")
    canary = [
        rule
        for group in groups
        for rule in group.get("rules") or []
        if "aiqe_secret_canary_detected_total" in str(rule.get("expr") or "")
    ]
    if not canary:
        raise AlertConfigError("缺少 Secret Canary 告警")
    if not any(
        str((rule.get("labels") or {}).get("severity", "")).upper() == "P0" for rule in canary
    ):
        raise AlertConfigError("Secret Canary 告警必须是 P0")
    return {"alerts": alerts, "referenced": sorted(referenced)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default=str(DEFAULT_FILE))
    args = parser.parse_args(argv)
    try:
        document = yaml.safe_load(Path(args.file).read_text(encoding="utf-8"))
        report = validate(document)
    except (OSError, yaml.YAMLError, AlertConfigError) as exc:
        print(f"::error::alerts: {exc}", file=sys.stderr)
        return 1
    print(f"alerts: {len(report['alerts'])}, metrics: {len(report['referenced'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
