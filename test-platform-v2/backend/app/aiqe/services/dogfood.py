"""AUD-011：真实跨系统 Mixed Workflow Dogfood（API → DB → Public API）。

v1.5 §02 AUD-011 要求：一个 TestRun 内真实执行 API + DB Read-only（+ 可选 Admin UI /
Public UI），动态输出必须来自**上一步真实 Driver**，每节点至少一个必需断言，Token 不得
出现在 RunContext/NodeRun/Event/Artifact。

本模块提供可执行 harness：

- ``build_sports_mixed_graph()``：登录 → 建赛事 → （可选）后台配置直播 → 公共 API 校验 →
  DB 只读校验 → （可选）前台 UI 校验；
- ``run_dogfood()``：真实调度循环（真实 ``node_executor`` / Target Policy / Query Registry /
  Assertion Engine / Secret Handle），绝不使用 Mock PASS；
- 缺少环境配置或缺少 VERIFIED Runner 时返回 ``BLOCKED``/``INCOMPLETE`` 并列出未验证平台，
  **不会**伪造 PASS。
"""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.aiqe.models.run import NodeRun, TestRun
from app.aiqe.redaction import assert_no_secret, redact_mapping
from app.aiqe.security import upsert_target_policy
from app.aiqe.services import dag_scheduler, node_executor, result_writer
from app.aiqe.services.run_context import RunContext
from app.aiqe.services.secret_vault import SecretVault, resolve_secret_handle


class DogfoodConfigError(ValueError):
    """缺少真实环境配置——不得降级为 Mock PASS。"""


@dataclass(frozen=True)
class DogfoodConfig:
    project_id: int
    base_url: str
    admin_url: str = ""
    admin_username: str = ""
    admin_password: str = ""
    db_query_key: str = ""
    db_match_param: str = "match_id"
    include_admin_ui: bool = False
    include_public_ui: bool = False
    include_mobile_ui: bool = False
    allow_private_targets: bool = False
    fixture_namespace: str = ""
    timeout_ms: int = 20000

    def validate(self) -> None:
        if not str(self.base_url or "").strip():
            raise DogfoodConfigError(
                "缺少 AIQE_DOGFOOD_BASE_URL：AUD-011 需要真实测试环境，禁止 Mock PASS"
            )
        if not self.base_url.startswith(("http://", "https://")):
            raise DogfoodConfigError("base_url 必须是 http(s) 地址")
        if self.include_admin_ui and (not self.admin_url or not self.admin_username):
            raise DogfoodConfigError("启用 Admin UI 节点需要 admin_url + 管理员账号")
        if (self.include_public_ui or self.include_mobile_ui) and not (
            self.base_url or self.admin_url
        ):
            raise DogfoodConfigError("启用 UI 节点需要配置被测前端地址")
        if not self.fixture_namespace:
            raise DogfoodConfigError("缺少 fixture_namespace：每个 Run 必须隔离测试数据")


@dataclass
class DogfoodReport:
    run_id: str = ""
    status: str = ""
    outcome: str | None = None
    node_statuses: dict[str, str] = field(default_factory=dict)
    assertions_total: int = 0
    assertions_failed: int = 0
    artifacts: int = 0
    secret_plaintext_hits: int = 0
    dynamic_propagation_ok: bool = False
    blocked_steps: list[dict[str, Any]] = field(default_factory=list)
    verified_platforms: list[str] = field(default_factory=list)
    unverified_platforms: list[str] = field(default_factory=list)
    fixture_namespace: str = ""
    production_safe: bool = True

    def payload(self) -> dict[str, Any]:
        return redact_mapping(
            {
                "run_id": self.run_id,
                "status": self.status,
                "outcome": self.outcome,
                "node_statuses": self.node_statuses,
                "assertions_total": self.assertions_total,
                "assertions_failed": self.assertions_failed,
                "artifacts": self.artifacts,
                "secret_plaintext_hits": self.secret_plaintext_hits,
                "dynamic_propagation_ok": self.dynamic_propagation_ok,
                "blocked_steps": self.blocked_steps,
                "verified_platforms": self.verified_platforms,
                "unverified_platforms": self.unverified_platforms,
                "fixture_namespace": self.fixture_namespace,
                "production_safe": self.production_safe,
            }
        )


def _assertion(key: str, *, source: str, path: str = "", operator: str = "equals",
               expected: Any = None, severity: str = "", required: bool = True) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "assertion_key": key,
        "source": source,
        "operator": operator,
        "expected": expected,
        "required": required,
        "severity": severity,
    }
    if path:
        payload["path"] = path
    return payload


def build_sports_mixed_graph(config: DogfoodConfig) -> dict[str, Any]:
    """按 AUD-011 的体育赛事链路构造真实 Workflow（不含任何 Mock）。"""
    base = config.base_url.rstrip("/")
    admin = (config.admin_url or base).rstrip("/")
    nodes: list[dict[str, Any]] = [
        {
            "key": "login",
            "driver": "http",
            "depends_on": [],
            "input": {
                "url": f"{base}/api/auth/login",
                "method": "POST",
                "json": {"username": config.admin_username, "password": config.admin_password},
                "timeout_ms": config.timeout_ms,
                "assertions": [
                    _assertion("login.http", source="http_status", operator="equals", expected=200),
                    _assertion(
                        "login.token",
                        source="http_body",
                        path="$.data.access_token",
                        operator="exists",
                        expected=True,
                    ),
                ],
                "outputs": {
                    "access_token": {"path": "$.data.access_token", "sensitive": True},
                    "user_id": {"path": "$.data.user.id"},
                },
            },
        },
        {
            "key": "create_match",
            "driver": "http",
            "depends_on": ["login"],
            "input": {
                "url": f"{base}/api/admin/matches",
                "method": "POST",
                "headers": {"Authorization": "Bearer ${nodes.login.outputs.access_token}"},
                "json": {"name": f"AIQE Dogfood {config.fixture_namespace}", "fixture": config.fixture_namespace},
                "timeout_ms": config.timeout_ms,
                "assertions": [
                    _assertion("match.created", source="http_status", operator="equals", expected=201),
                    _assertion(
                        "match.id",
                        source="http_body",
                        path="$.data.match_id",
                        operator="exists",
                        expected=True,
                    ),
                ],
                "outputs": {"match_id": {"path": "$.data.match_id"}},
            },
        },
        {
            "key": "verify_public_api",
            "driver": "http",
            "depends_on": ["create_match"],
            "input": {
                "url": f"{base}/api/public/matches/__MATCH__",
                "method": "GET",
                "timeout_ms": config.timeout_ms,
                "assertions": [
                    _assertion("public.http", source="http_status", operator="equals", expected=200),
                    _assertion(
                        "public.status",
                        source="http_body",
                        path="$.data.status",
                        operator="in",
                        expected=["live", "scheduled"],
                    ),
                ],
                "url_template": "${base}/api/public/matches/${nodes.create_match.outputs.match_id}",
            },
        },
    ]
    if config.db_query_key:
        nodes.append(
            {
                "key": "verify_db_readonly",
                "driver": "db",
                "depends_on": ["create_match"],
                "input": {
                    "query_key": config.db_query_key,
                    "params": {config.db_match_param: "${nodes.create_match.outputs.match_id}"},
                    "assertions": [
                        _assertion("db.row", source="db_query", path="$[0]", operator="exists", expected=True)
                    ],
                },
            }
        )
    if config.include_admin_ui:
        nodes.append(
            {
                "key": "admin_configure_live",
                "driver": "playwright",
                "depends_on": ["create_match"],
                "input": {
                    "url": f"{admin}/admin/matches",
                    "click_text": "发布",
                    "expect_text": "已发布",
                    "timeout_ms": max(config.timeout_ms, 30000),
                    "assertions": [
                        _assertion(
                            "admin.publish",
                            source="dom",
                            path="state",
                            operator="equals",
                            expected="published",
                        )
                    ],
                },
            }
        )
    if config.include_public_ui:
        nodes.append(
            {
                "key": "verify_frontend",
                "driver": "playwright",
                "depends_on": ["verify_public_api"],
                "input": {
                    "url": "${base}/match/${nodes.create_match.outputs.match_id}",
                    "expect_text": "直播",
                    "timeout_ms": max(config.timeout_ms, 30000),
                    "assertions": [
                        _assertion("ui.live_entry", source="dom", path="live_entry", operator="exists", expected=True)
                    ],
                },
            }
        )
    return {
        "schema_version": "1.0",
        "nodes": nodes,
        "edges": [],
        "run_policy": {
            "max_parallel_nodes": 1,
            "fail_fast": False,
            "cleanup_node": "",
            "fixture_namespace": config.fixture_namespace,
        },
        "retry": {"max_attempts": 1},
    }


def _extract_outputs(body: Any, spec: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    from app.aiqe.assertions.observation import resolve_json_path

    outputs: dict[str, Any] = {}
    sensitive: dict[str, Any] = {}
    for key, decl in (spec or {}).items():
        path = str((decl or {}).get("path") or "")
        found, value = resolve_json_path(body, path) if path else (True, body)
        if not found:
            continue
        if (decl or {}).get("sensitive"):
            sensitive[key] = value
        else:
            outputs[key] = value
    return outputs, sensitive


def _with_base(value: Any, base: str) -> Any:
    """把 `${base}` 常量替换成被测环境地址（RunContext 只认 nodes/secrets/handles）。"""
    if isinstance(value, str):
        return value.replace("${base}", base.rstrip("/"))
    if isinstance(value, dict):
        return {key: _with_base(item, base) for key, item in value.items()}
    if isinstance(value, list):
        return [_with_base(item, base) for item in value]
    return value


def _resolve_url(url: str, *, base: str, run_ctx: RunContext, secrets: dict[str, str],
                 node_key: str) -> str:
    template = url.replace("${base}", base.rstrip("/"))
    return str(run_ctx.resolve_inputs(node_key, template, secrets=secrets))


def run_dogfood(
    db: Session,
    config: DogfoodConfig,
    *,
    runs: int = 1,
    vault: SecretVault | None = None,
    now: datetime | None = None,
) -> list[DogfoodReport]:
    """连续执行 ``runs`` 次真实混合工作流；任一次失败立即返回已产生的报告。"""
    config.validate()
    reports: list[DogfoodReport] = []
    for index in range(max(1, int(runs))):
        namespace = f"{config.fixture_namespace}-{index + 1}-{uuid.uuid4().hex[:6]}"
        reports.append(
            _run_once(
                db,
                config=config,
                fixture_namespace=namespace,
                vault=vault,
                now=now,
            )
        )
        if reports[-1].status != "COMPLETED":
            break
    return reports


def _ensure_target_policy(db: Session, config: DogfoodConfig) -> None:
    from urllib.parse import urlsplit

    hosts: list[str] = []
    for url in (config.base_url, config.admin_url):
        if not url:
            continue
        host = urlsplit(url).hostname
        if host:
            hosts.append(host)
    policy: dict[str, Any] = {
        "allowed_hosts": sorted(set(hosts)),
        "allowed_methods": ["GET", "POST", "PUT", "PATCH", "DELETE"],
        "max_redirects": 0,
    }
    if config.allow_private_targets:
        policy["allow_private_cidrs"] = ["127.0.0.0/8", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "::1/128"]
    if config.base_url.startswith("http://"):
        policy["allowed_ports"] = [80]
    else:
        policy["allowed_ports"] = [443]
    ports = set(policy["allowed_ports"])
    for url in (config.base_url, config.admin_url):
        if not url:
            continue
        parsed = urlsplit(url)
        if parsed.port:
            ports.add(parsed.port)
    policy["allowed_ports"] = sorted(ports)
    upsert_target_policy(
        db, project_id=config.project_id, environment_id=None, policy=policy, name="dogfood"
    )


def _run_once(
    db: Session,
    *,
    config: DogfoodConfig,
    fixture_namespace: str,
    vault: SecretVault | None,
    now: datetime | None,
) -> DogfoodReport:
    _ensure_target_policy(db, config)
    graph = build_sports_mixed_graph(config)
    run = TestRun(
        project_id=config.project_id,
        run_key=f"DOGFOOD-{fixture_namespace}",
        source_type="dogfood",
        status="QUEUED",
        environment_snapshot_json={"fixture_namespace": fixture_namespace},
    )
    db.add(run)
    db.flush()
    dag_scheduler.create_node_runs(db, run.id, graph)
    db.flush()

    report = DogfoodReport(
        run_id=run.id,
        fixture_namespace=fixture_namespace,
        unverified_platforms=[
            platform
            for platform, enabled in (
                ("web_desktop", config.include_public_ui),
                ("web_admin", config.include_admin_ui),
                ("mobile_web", config.include_mobile_ui),
            )
            if enabled
        ],
    )
    secrets = {
        "admin_username": config.admin_username,
        "admin_password": config.admin_password,
    }
    run_ctx = RunContext(
        db,
        run.id,
        handle_resolver=lambda handle_id, node_key: resolve_secret_handle(
            db,
            handle_id,
            project_id=config.project_id,
            run_id=run.id,
            consumer_node_key=node_key,
            vault=vault,
        ),
    )
    dag_scheduler.schedule(db, run.id, graph)
    db.flush()

    ordered = list(
        db.scalars(select(NodeRun).where(NodeRun.run_id == run.id).order_by(NodeRun.id))
    )
    by_key = {node.node_key: node for node in ordered}
    graph_order = [item["key"] for item in graph["nodes"]]
    failed = False
    while not failed:
        # 每一轮都由调度器按依赖/并行度把可执行节点推进到 READY（含 attempt 计数），
        # 保证 complete_node 不会把首次执行误判为"重试"。
        dag_scheduler.schedule(db, run.id, graph)
        db.flush()
        executed = False
        for key in graph_order:
            node = by_key[key]
            if node.status != "READY":
                continue
            executed = True
            defs = next(item for item in graph["nodes"] if item["key"] == key)
            input_spec = dict(defs.get("input") or {})
            spec_with_base = _with_base(input_spec, config.base_url)
            resolved_input: dict[str, Any] = {}
            for input_key, value in spec_with_base.items():
                # 递归解析：url / headers / json / params 中任何 `${nodes.*}`、
                # `${secret_handles.*}` 引用都走 RunContext（含 Secret Handle 作用域校验）。
                resolved_input[input_key] = run_ctx.resolve_inputs(
                    node.node_key, value, secrets=secrets
                )
            template = str(spec_with_base.get("url_template") or "")
            if template:
                resolved_input["url"] = str(
                    run_ctx.resolve_inputs(node.node_key, template, secrets=secrets)
                )
            node.input_ref = resolved_input
            db.flush()

            # AUD-005/020：外部 Driver（playwright/appium 等）必须先有可用/已验证节点，
            # 否则 Launch 前 BLOCKED —— 绝不因为本机恰好能启动浏览器就宣称平台通过。
            from app.aiqe.services import preflight as preflight_service

            preflight_result = preflight_service.preflight_node_run(
                db, node, run=run, graph=graph
            )
            if not preflight_result.allowed:
                dag_scheduler.complete_node(
                    db,
                    run.id,
                    node.node_key,
                    "BLOCKED",
                    graph,
                    error_class="PREFLIGHT_BLOCKED",
                    outputs={"preflight": preflight_result.payload()},
                )
                db.flush()
                report.blocked_steps.append(
                    {
                        "node_key": node.node_key,
                        "status": "BLOCKED",
                        "error_class": "PREFLIGHT_BLOCKED",
                        "blockers": [item.payload() for item in preflight_result.blockers],
                    }
                )
                failed = True
                break

            dag_scheduler.mark_running(db, run.id, node.node_key)
            result = node_executor.execute_node(node, db=db)
            observation = result_writer.observation_from_payload(result.observation)
            mapped_status, mapped_error, outcomes = result_writer.evaluate_node_assertions(
                db,
                run_id=run.id,
                node=node,
                observation=observation,
                driver_status=result.status,
                driver_error=result.error_class or None,
            )
            status = mapped_status or result.status
            error_class = mapped_error or result.error_class or None

            if status == "PASSED":
                body = observation.body if observation is not None else None
                outputs_spec = dict(input_spec.get("outputs") or {})
                plain_outputs, sensitive_outputs = _extract_outputs(body, outputs_spec)
                if plain_outputs:
                    run_ctx.set_output(node.node_key, plain_outputs)
                if sensitive_outputs:
                    run_ctx.set_output_secure(
                        node.node_key,
                        sensitive_outputs,
                        project_id=config.project_id,
                        allowed_consumer_nodes=tuple(
                            others["key"]
                            for others in graph["nodes"]
                            if node.node_key in others.get("depends_on", [])
                        ),
                        schema={key: {"sensitive": True} for key in sensitive_outputs},
                        vault=vault,
                    )
            dag_scheduler.complete_node(
                db,
                run.id,
                node.node_key,
                status,
                graph,
                error_class=error_class,
                outputs={
                    "assertions": [item.payload() for item in outcomes],
                    "execution": result.detail,
                },
            )
            db.flush()
            if status in {"BLOCKED", "FAILED", "ERROR"}:
                report.blocked_steps.append(
                    {"node_key": node.node_key, "status": status, "error_class": error_class}
                )
                failed = True
                break
        if not executed and not failed:
            break

    if not failed:
        # 收口：所有节点终态但 Run 仍 RUNNING 时由调度器聚合终态
        dag_scheduler.finalize_run(db, run.id, graph)

    db.commit()
    db.refresh(run)
    report.status = run.status
    report.outcome = run.outcome
    report.node_statuses = {
        node.node_key: node.status
        for node in db.scalars(select(NodeRun).where(NodeRun.run_id == run.id))
    }
    from app.aiqe.models.run import RunAssertionResult, StepAttempt

    assertion_rows = db.execute(
        select(RunAssertionResult, StepAttempt)
        .join(StepAttempt, StepAttempt.id == RunAssertionResult.step_attempt_id)
        .join(NodeRun, NodeRun.id == StepAttempt.node_run_id)
        .where(NodeRun.run_id == run.id)
    ).all()
    report.assertions_total = len(assertion_rows)
    report.assertions_failed = sum(
        1 for assertion, _attempt in assertion_rows if assertion.status == "FAIL"
    )
    from app.aiqe.models.artifact import RunArtifact

    report.artifacts = len(
        list(db.scalars(select(RunArtifact).where(RunArtifact.run_id == run.id)))
    )
    report.dynamic_propagation_ok = _has_dynamic_propagation(db, run.id)
    report.secret_plaintext_hits = _count_plaintext_secrets(db, run.id, config)
    platform_nodes = {
        "web_admin": "admin_configure_live",
        "web_desktop": "verify_frontend",
    }
    report.verified_platforms = [
        platform
        for platform, node_key in platform_nodes.items()
        if report.node_statuses.get(node_key) == "PASSED"
    ]
    if report.secret_plaintext_hits:
        report.production_safe = False
    assert_no_secret(
        {"node_statuses": report.node_statuses, "blocked": report.blocked_steps},
        where="dogfood_report",
    )
    return report


def _has_dynamic_propagation(db: Session, run_id: str) -> bool:
    rows = list(db.scalars(select(NodeRun).where(NodeRun.run_id == run_id)))
    created = next((row for row in rows if row.node_key == "create_match"), None)
    verify = next((row for row in rows if row.node_key == "verify_public_api"), None)
    if created is None or verify is None:
        return False
    match_id = str((created.output_ref or {}).get("match_id") or "")
    if not match_id:
        return False
    return match_id in str((verify.input_ref or {}).get("url") or "")


def _count_plaintext_secrets(db: Session, run_id: str, config: DogfoodConfig) -> int:
    """扫描可展示字段中是否出现明文密码/Token（canary 语义）。"""
    from app.aiqe.models.event import RunEvent

    needles = [value for value in (config.admin_password,) if value]
    if not needles:
        return 0
    hits = 0
    for node in db.scalars(select(NodeRun).where(NodeRun.run_id == run_id)):
        blob = json.dumps(node.output_ref or {}, ensure_ascii=False)
        hits += sum(1 for needle in needles if needle in blob)
    for event in db.scalars(select(RunEvent).where(RunEvent.run_id == run_id)):
        blob = json.dumps(event.payload_json or {}, ensure_ascii=False)
        hits += sum(1 for needle in needles if needle in blob)
    return hits


def report_digest(report: DogfoodReport) -> str:
    payload = json.dumps(report.payload(), sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


__all__ = [
    "DogfoodConfig",
    "DogfoodConfigError",
    "DogfoodReport",
    "build_sports_mixed_graph",
    "report_digest",
    "run_dogfood",
]
