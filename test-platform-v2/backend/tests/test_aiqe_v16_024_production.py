"""V16-024 验收：指标、告警、限流、Canary、容器 egress 与生产文档。"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from app.aiqe.observability.metrics import MetricsRegistry, metrics
from app.aiqe.observability.rate_limits import RateLimited, enforce, launch_limiter
from app.core.config import settings
from app.core.exceptions import APIException

ROOT = Path(__file__).resolve().parents[3]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_metrics_registry_low_cardinality_and_render():
    registry = MetricsRegistry()
    registry.inc("aiqe_ssrf_blocked_total", {"project_id": "1", "driver": "http"})
    registry.inc(
        "aiqe_target_policy_denied_total",
        {"project_id": "1", "url": "https://evil.test/?token=abc"},
    )
    registry.observe("aiqe_run_terminal_latency_seconds", 12.5, {"outcome": "PASS"})
    text = registry.render()
    assert 'aiqe_ssrf_blocked_total{driver="http",project_id="1"} 1' in text
    # 非白名单 label 被丢弃、敏感值被 redacted
    assert "evil.test" not in text
    assert "https://" not in text
    assert "aiqe_run_terminal_latency_seconds_count" in text
    assert registry.value("aiqe_ssrf_blocked_total", {"driver": "http", "project_id": "1"}) == 1


def test_metrics_endpoint_token_and_production_fail_closed(monkeypatch):
    from app.api.v1.aiqe_metrics import get_aiqe_metrics

    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "aiqe_metrics_token", "")
    assert get_aiqe_metrics().status_code == 200

    monkeypatch.setattr(settings, "aiqe_metrics_token", "s3cret")
    with pytest.raises(APIException):
        get_aiqe_metrics(x_aiqe_metrics_token=None)
    with pytest.raises(APIException):
        get_aiqe_metrics(x_aiqe_metrics_token="wrong")
    assert get_aiqe_metrics(x_aiqe_metrics_token="s3cret").status_code == 200

    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "aiqe_metrics_token", "")
    with pytest.raises(APIException):
        get_aiqe_metrics()


def test_rate_limit_enforced_only_in_production(monkeypatch):
    import app.aiqe.observability.rate_limits as rate_limits
    from app.core.rate_limit import RateLimiter

    small = RateLimiter(max_requests=1, window_seconds=60)
    monkeypatch.setitem(rate_limits._BUCKETS, "launch", small)
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "aiqe_rate_limit_enforce", False)
    enforce("launch", project_id=1)
    with pytest.raises(RateLimited):
        enforce("launch", project_id=1)

    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "aiqe_rate_limit_enforce", False)
    enforce("launch", project_id=2)  # 非生产默认不启用


def test_canary_detection_increments_metric():
    from app.aiqe.security.output_sanitizer import note_canary

    before = metrics.value("aiqe_secret_canary_detected_total")
    note_canary("CANARY-PASSWORD-123")
    assert metrics.value("aiqe_secret_canary_detected_total") == before + 1
    note_canary("normal-secret")
    assert metrics.value("aiqe_secret_canary_detected_total") == before + 1


def test_alert_rules_cover_required_metrics():
    module = _load("check_alerts", ROOT / "scripts" / "aiqe" / "check_alerts.py")
    document = module.yaml.safe_load(module.DEFAULT_FILE.read_text(encoding="utf-8"))
    report = module.validate(document)
    assert len(report["referenced"]) >= len(module.REQUIRED_METRICS)
    canary = [
        rule
        for group in document["groups"]
        for rule in group["rules"]
        if "aiqe_secret_canary_detected_total" in rule["expr"]
    ]
    assert canary and canary[0]["labels"]["severity"] == "P0"


def test_alert_validator_rejects_missing_metric_or_bad_severity():
    module = _load("check_alerts_bad", ROOT / "scripts" / "aiqe" / "check_alerts.py")
    with pytest.raises(module.AlertConfigError):
        module.validate(
            {
                "groups": [
                    {
                        "name": "x",
                        "rules": [
                            {
                                "alert": "X",
                                "expr": "increase(aiqe_ssrf_blocked_total[5m]) > 0",
                                "for": "0m",
                                "labels": {"severity": "P0"},
                                "annotations": {"summary": "x"},
                            }
                        ],
                    }
                ]
            }
        )
    document = module.yaml.safe_load(module.DEFAULT_FILE.read_text(encoding="utf-8"))
    document["groups"][0]["rules"][0]["labels"]["severity"] = "WARN"
    with pytest.raises(module.AlertConfigError):
        module.validate(document)


def test_container_egress_policy_deny_by_default():
    module = _load("check_egress", ROOT / "scripts" / "aiqe" / "check_container_egress.py")
    documents = module.load(module.DEFAULT_FILE)
    report = module.validate(documents)
    assert report["policies"] >= 2
    # 去掉默认拒绝策略 → 必须失败
    policies = [doc for doc in documents if doc.get("kind") == "NetworkPolicy"]
    with pytest.raises(module.EgressPolicyError):
        module.validate(
            [doc for doc in documents if doc not in policies[:1]]
            + [policies[1]]
        )


def test_production_docs_and_rollout_plan_exist():
    monitoring = (ROOT / "docs" / "aiqe" / "v1.6" / "observability" / "Monitoring-and-Alerts.md").read_text(
        encoding="utf-8"
    )
    readiness = (ROOT / "docs" / "aiqe" / "v1.6" / "Production-Readiness.md").read_text(
        encoding="utf-8"
    )
    assert "aiqe_secret_canary_detected_total" in monitoring
    assert "P0" in monitoring
    for stage in ("Shadow", "Dogfood", "小流量", "GA"):
        assert stage in readiness
    assert "停止条件" in readiness
    assert "备份" in readiness and "回滚" in readiness
