"""V1.6.2（FIX-005 / FIX-006）服务层验收：AgentTask 证据边界 + Benchmark 可复算。

覆盖规格（手册 §6 / §7）：

FIX-005
- AgentTask 变更范围（base_sha/head_sha）校验与注入；
- 未审批（含状态被外部改写、缺少审批人/审批时间）不得入队/执行；
- A5 缺 SHA 或无 ALLOW 的 ``read_git_diff`` 审计 → 任务 ``BLOCKED/A5_NOT_PROVEN``；
- A5 有真实 SHA → 通过 BoundToolRegistry 调用 ``read_git_diff`` 并落审计；
- Agent 写工具（create_draft）无人工审批 → DENY + 任务不得 COMPLETED；
- Worker 模型边界 ``resolve_project_llm``：未配置 Provider fail-closed。

FIX-006
- 固定小 fixture 的 Precision/Recall/F1/TP/FP/FN/TN 手工可复算；
- 篡改 ``metrics_json`` summary → 服务端拒绝；
- Dataset 口径：total = valid + excluded，剔除逐条记录原因（43 = 37 + 6）；
- Dataset hash 变化 / Run 被挪到别的 Dataset → 旧 Run 不可冒充；
- 重复样本 id / 非法标签 / 空数据集 / 全负类有定义明确的结果；
- Learning Candidate：同一用户审批拒绝、角色字符串拒绝、禁用账号拒绝、
  状态错误/未审批不得发布、发布事件绑定真实用户 id。

LLM 边界：仅 ``A5`` 用例使用 deterministic stub（``controlled_llm_test``），
证明的是工具/审计/阻断链路，不是生产模型质量。
"""
from __future__ import annotations

import subprocess
import uuid
from pathlib import Path

import pytest
from sqlalchemy import select

from app.aiqe.models.benchmark import BenchmarkRun, BenchmarkSample
from app.aiqe.models.learning import LearningCandidate
from app.aiqe.services import agent_task_service, benchmark_service
from app.aiqe.services.agent_task_service import (
    A5_NOT_PROVEN,
    AgentTaskError,
    approve_task,
    create_task,
    enqueue_task_job,
    get_task,
    run_task,
    task_change_scope,
)
from app.aiqe.services.benchmark_service import (
    BenchmarkError,
    add_sample,
    compute_content_hash,
    compute_metrics,
    create_dataset,
    freeze_dataset,
    metrics_of,
    partition_samples,
    recompute_metrics,
    run_benchmark,
)
from app.aiqe.services.learning_service import (
    LearningError,
    approve_candidate,
    create_candidate,
    evaluate_candidate,
    publish_candidate,
)
from app.aiqe.services.tool_registry import (
    ToolApprovalRequired,
    ToolSpec,
    ToolUnavailable,
    build_bound_registry,
    default_specs,
)
from app.models.project import Project
from app.models.user import User

MAX_SHA = "a" * 40
MIN_SHA = "b" * 40


# ── 公共 helper ────────────────────────────────────────────
def _project(db, project_id: int = 1) -> None:
    if db.get(Project, project_id) is None:
        db.add(
            Project(
                id=project_id,
                code=f"P{project_id}",
                name=f"Project {project_id}",
                owner_id=1,
                status=1,
            )
        )
        db.flush()


def _user(db, user_id: int, *, status: int = 1) -> User:
    row = db.get(User, user_id)
    if row is None:
        row = User(
            id=user_id,
            username=f"user-{user_id}",
            password="x",
            nickname=f"U{user_id}",
            email=f"u{user_id}@test.local",
            status=status,
        )
        db.add(row)
        db.flush()
    return row


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=_repo_root(),
        capture_output=True,
        text=True,
        check=True,
        encoding="utf-8",
        errors="replace",
    ).stdout.strip()


def _repo_commit_pair() -> tuple[str, str]:
    """真实相邻提交对；没有 git 历史时显式跳过（不伪造 SHA）。"""
    try:
        head = _git("rev-parse", "HEAD")
        base = _git("rev-parse", "HEAD~1")
        changed = _git("diff", "--name-only", f"{base}..{head}")
    except (OSError, subprocess.CalledProcessError) as exc:
        pytest.skip(f"BLOCKED: 无法解析真实 git 提交对（{exc}）")
    if len(base) != 40 or len(head) != 40 or not changed:
        pytest.skip("BLOCKED: 当前 checkout 没有非空 diff 的相邻提交")
    return base, head


def _impact_llm(system: str, prompt: str) -> str:
    assert "变更影响" in system, system[:80]
    return (
        '{"impacted_areas":["api"],"candidate_suites":["api-suite","smoke-suite"],'
        '"forced_suites":[],"rationale":"controlled_llm_test"}'
    )


def _benchmark_dataset(
    db, *, samples: int = 40, fp_ratio: float = 0.025, key: str | None = None
):
    _project(db)
    dataset = create_dataset(
        db,
        project_id=1,
        dataset_key=key or f"v162-ds-{uuid.uuid4().hex[:8]}",
        task_type="learning",
    )
    for index in range(samples):
        add_sample(
            db,
            dataset.id,
            sample_id=f"s-{index:03d}",
            golden_labels=["A"],
            labeler="qa",
            reviewer="lead",
        )
    freeze_dataset(db, dataset.id)
    return dataset


def _benchmark_run(db, dataset, *, fp_ratio: float = 0.025):
    fps = int(round(int(dataset.sample_count or 0) * fp_ratio))

    def predictor(sample):
        index = int(str(sample.sample_id).split("-")[1])
        return {"labels": ["B"] if index < fps else ["A"]}

    return run_benchmark(
        db,
        dataset_id=dataset.id,
        agent_key="A6",
        agent_version="1.6.2",
        prompt_hash="sha256:p162",
        model_provider="deepseek",
        model_name="deepseek-chat",
        predictor=predictor,
    )


# ══════════════════════════════════════════════════════════
# FIX-005：AgentTask 变更范围 / 审批事实 / A5 证据
# ══════════════════════════════════════════════════════════
def test_change_scope_validation_is_fail_closed():
    with pytest.raises(AgentTaskError) as exc:
        agent_task_service.normalize_change_scope(base_sha=MAX_SHA)
    assert exc.value.code == "SHA_INCOMPLETE"
    for bad in ("a" * 39, "a" * 41, "z" * 40, "HEAD"):
        with pytest.raises(AgentTaskError) as exc:
            agent_task_service.normalize_change_scope(base_sha=bad, head_sha=MIN_SHA)
        assert exc.value.code == "SHA_INVALID", bad
    with pytest.raises(AgentTaskError) as exc:
        agent_task_service.normalize_change_scope(base_sha=MAX_SHA, head_sha=MAX_SHA)
    assert exc.value.code == "SHA_INVALID"
    # 大写 hex 会被规范化为小写（服务端契约要求小写，输入端宽容）
    scope = agent_task_service.normalize_change_scope(
        base_sha=MAX_SHA.upper(), head_sha=MIN_SHA.upper()
    )
    assert scope == {"base_sha": MAX_SHA, "head_sha": MIN_SHA}


def test_change_scope_persisted_in_plan_params(db_session):
    _project(db_session)
    task = create_task(
        db_session,
        project_id=1,
        goal="变更影响",
        include=("a5_impact",),
        requested_by=1,
        idempotency_key="v162-scope",
        base_sha=MAX_SHA,
        head_sha=MIN_SHA,
        repo="cameltv-test-platform",
    )
    assert task_change_scope(task) == {
        "base_sha": MAX_SHA,
        "head_sha": MIN_SHA,
        "repo": "cameltv-test-platform",
    }
    # plan_hash 只覆盖计划本身（SHA 是执行上下文，不进审批 hash）
    assert task.plan_hash.startswith("sha256:")
    assert "base_sha" not in str(sorted((task.plan_json or {}).keys()))

    # 被篡改成非法 SHA 时，读取侧忽略（不会把坏参数送进工具层）
    task.plan_json = {**(task.plan_json or {}), "params": {"base_sha": "x", "head_sha": "y"}}
    db_session.flush()
    assert task_change_scope(task) == {}


def test_enqueue_requires_approved_status(db_session):
    _project(db_session)
    task = create_task(
        db_session,
        project_id=1,
        goal="未审批",
        include=("a1_requirement",),
        requested_by=1,
        idempotency_key="v162-enqueue-guard",
    )
    with pytest.raises(AgentTaskError) as exc:
        enqueue_task_job(db_session, task)
    assert exc.value.code == "APPROVAL_REQUIRED"
    assert get_task(db_session, task.id, project_id=1).status == "DRAFT"


def test_run_requires_approval_provenance_even_if_status_rewritten(db_session):
    _project(db_session)
    task = create_task(
        db_session,
        project_id=1,
        goal="审批事实",
        include=("a1_requirement",),
        requested_by=1,
        idempotency_key="v162-approval-provenance",
    )
    approve_task(db_session, task.id, project_id=1, approved_by=2)
    row = get_task(db_session, task.id, project_id=1)
    row.approved_by = None
    row.approved_at = None
    db_session.flush()
    with pytest.raises(AgentTaskError) as exc:
        run_task(db_session, task.id, project_id=1)
    assert exc.value.code == "APPROVAL_REQUIRED"


def test_a5_without_sha_is_not_proven(db_session):
    """A5 缺 SHA：任务必须 BLOCKED/A5_NOT_PROVEN，A5 执行记录不可采信。"""
    _project(db_session)
    task = create_task(
        db_session,
        project_id=1,
        goal="无 SHA 的变更影响",
        include=("a5_impact",),
        requested_by=1,
        idempotency_key="v162-a5-no-sha",
    )
    approve_task(db_session, task.id, project_id=1, approved_by=2)
    result = run_task(db_session, task.id, project_id=1, llm=_impact_llm)
    assert result["task"]["status"] == "BLOCKED", result
    assert result["task"]["error_code"] == A5_NOT_PROVEN
    executions = result["executions"]
    assert len(executions) == 1
    assert executions[0]["agent_key"] == "A5"
    assert executions[0]["status"] == "BLOCKED"
    assert executions[0]["needs_human"] is True
    assert "NOT_PROVEN" in executions[0]["error_text"]
    from app.aiqe.models.agent import AgentExecution

    execution = db_session.get(AgentExecution, executions[0]["id"])
    assert "A5_NOT_PROVEN" in list(execution.warnings_json or [])


def test_a5_with_real_sha_audits_read_git_diff(db_session):
    """controlled_llm_test：真实 SHA → read_git_diff 被调用并写 ToolExecutionAudit。"""
    from app.aiqe.models.tool import ToolExecutionAudit

    _project(db_session)
    base_sha, head_sha = _repo_commit_pair()
    task = create_task(
        db_session,
        project_id=1,
        goal="有 SHA 的变更影响",
        include=("a5_impact",),
        requested_by=1,
        idempotency_key="v162-a5-with-sha",
        base_sha=base_sha,
        head_sha=head_sha,
    )
    approve_task(db_session, task.id, project_id=1, approved_by=2)
    result = run_task(db_session, task.id, project_id=1, llm=_impact_llm)
    assert result["task"]["status"] == "COMPLETED", result
    audits = list(
        db_session.scalars(
            select(ToolExecutionAudit).where(
                ToolExecutionAudit.task_id == task.id,
                ToolExecutionAudit.tool_name == "read_git_diff",
            )
        )
    )
    assert audits, "A5 必须留下 read_git_diff 审计"
    assert audits[0].decision == "ALLOW"
    assert audits[0].args_summary_json.get("base_sha") == base_sha
    assert audits[0].args_summary_json.get("head_sha") == head_sha
    # SHA 注入 A5 输入（AgentExecution.input_text 保留注入事实，可审计回查）
    from app.aiqe.models.agent import AgentExecution

    a5_execution = db_session.get(AgentExecution, result["executions"][0]["id"])
    assert base_sha in (a5_execution.input_text or "")
    assert head_sha in (a5_execution.input_text or "")


def test_a5_read_git_diff_denied_blocks_task(db_session):
    """SHA 不在仓库历史 → read_git_diff 拒绝（DENY）→ 任务不得 COMPLETED。"""
    _project(db_session)
    task = create_task(
        db_session,
        project_id=1,
        goal="不存在的 SHA",
        include=("a5_impact",),
        requested_by=1,
        idempotency_key="v162-a5-bad-sha",
        base_sha="0" * 40,
        head_sha="1" * 40,
    )
    approve_task(db_session, task.id, project_id=1, approved_by=2)
    result = run_task(db_session, task.id, project_id=1, llm=_impact_llm)
    assert result["task"]["status"] == "BLOCKED", result
    assert result["task"]["error_code"] == A5_NOT_PROVEN
    assert "READ_GIT_DIFF_NOT_EXECUTED" in result["task"]["error_text"]


def test_write_tool_cannot_be_called_without_human_approval(db_session):
    """Agent 没有人工审批 token：WRITE 工具必须 DENY，任务不得 COMPLETED。"""
    from app.aiqe.agents.protocol import AgentResult
    from app.aiqe.models.tool import ToolExecutionAudit

    _project(db_session)
    task = create_task(
        db_session,
        project_id=1,
        goal="写工具边界",
        include=("a1_requirement", "a2_test_design"),
        requested_by=1,
        idempotency_key="v162-write-tool",
    )
    approve_task(db_session, task.id, project_id=1, approved_by=2)
    specs = dict(default_specs())
    specs["create_draft"] = ToolSpec(
        name="create_draft",
        side_effect_level="WRITE",
        requires_human_approval=True,
        handler=lambda db, project_id, **kwargs: {"created": True},
    )
    registry = build_bound_registry(
        db_session, project_id=1, task_id=task.id, specs=specs
    )

    def executor(plan_task, context, request):  # noqa: ARG001
        if plan_task.agent_key == "A1":
            return AgentResult(
                agent_key="A1",
                agent_version="1.0.0",
                status="COMPLETED",
                output={"note": "a1 ok"},
            )
        with pytest.raises(ToolApprovalRequired):
            context.tool_executor.call("create_draft")
        return AgentResult(
            agent_key=plan_task.agent_key,
            agent_version="1.0.0",
            status="FAILED",
            error_code="TOOL_APPROVAL_REQUIRED",
        )

    result = run_task(db_session, task.id, project_id=1, tools=registry, executor=executor)
    assert result["task"]["status"] == "FAILED"
    audits = list(
        db_session.scalars(
            select(ToolExecutionAudit).where(ToolExecutionAudit.task_id == task.id)
        )
    )
    assert audits and audits[0].tool_name == "create_draft"
    assert audits[0].agent_key == "A2"
    assert audits[0].decision == "DENY"
    assert audits[0].side_effect_level == "WRITE"


def test_create_draft_is_unavailable_by_default(db_session):
    _project(db_session)
    registry = build_bound_registry(db_session, project_id=1, task_id="t-unavailable")
    with pytest.raises(ToolUnavailable):
        registry.resolve("A2", "create_draft")


def test_worker_llm_boundary_fail_closed_without_provider(db_session, monkeypatch):
    from app.services import ai_client

    monkeypatch.setattr(ai_client, "is_configured", lambda db, pid: False)
    assert agent_task_service.resolve_project_llm(db_session, 1) is None


def test_worker_llm_boundary_uses_project_provider(db_session, monkeypatch):
    from app.services import ai_client

    monkeypatch.setattr(ai_client, "is_configured", lambda db, pid: True)
    captured: dict = {}

    def fake_chat(db, project_id, **kwargs):
        captured.update({"project_id": project_id, **kwargs})
        return {"content": '{"ok":true}'}

    monkeypatch.setattr(ai_client, "chat_completions_full", fake_chat)
    llm = agent_task_service.resolve_project_llm(db_session, 1)
    assert llm is not None
    assert llm("system", "user") == '{"ok":true}'
    assert captured["project_id"] == 1
    assert captured["json_mode"] is True


# ══════════════════════════════════════════════════════════
# FIX-006：指标复算 / 口径 / 数据集绑定
# ══════════════════════════════════════════════════════════
def test_metrics_fixed_fixture_manually_recomputable():
    """5 样本固定 fixture：TP=3 / FP=1 / FN=2 / known=1（手工可复算）。"""
    samples = [
        BenchmarkSample(dataset_id="d", sample_id=f"s-{index}", golden_labels_json=["A"])
        for index in range(5)
    ]
    predictions = {"s-0": ["A"], "s-1": ["A"], "s-2": ["A"], "s-3": ["B"], "s-4": ["UNKNOWN"]}
    metrics = compute_metrics(samples, predictions)
    assert metrics.samples == 5
    assert metrics.true_positives == 3
    assert metrics.false_positives == 1
    assert metrics.false_negatives == 2
    assert metrics.precision == pytest.approx(0.75)
    assert metrics.recall == pytest.approx(0.6)
    assert metrics.f1 == pytest.approx(0.6667, abs=1e-3)
    assert metrics.unknown_rate == pytest.approx(0.2)
    # 样本级 2x2：4 个可用预测（含 1 个错类），1 个弃权
    assert metrics.sample_true_positives == 4
    assert metrics.sample_false_negatives == 1
    assert metrics.sample_false_positives == 0
    assert metrics.sample_true_negatives == 0
    # 同一实现从逐样本记录复算结果必须一致
    recomputed = recompute_metrics(
        [
            {"golden": ["A"], "predicted": sorted(list(pred))}
            for pred in (
                ["A"],
                ["A"],
                ["A"],
                ["B"],
                ["UNKNOWN"],
            )
        ]
    )
    assert recomputed.payload() == metrics.payload()


def test_empty_and_all_negative_metrics_are_defined():
    empty = compute_metrics([], {})
    assert empty.samples == 0
    assert empty.precision == 0.0 and empty.recall == 0.0 and empty.f1 == 0.0
    assert empty.unknown_rate == 0.0
    assert empty.gate_eligible is False and empty.meets_thresholds is False

    # 全负类（golden 为空）：模型弃权 → TN
    negative = compute_metrics(
        [BenchmarkSample(dataset_id="d", sample_id="n-1", golden_labels_json=[])],
        {"n-1": ["UNKNOWN"]},
    )
    assert negative.sample_true_negatives == 1
    assert negative.true_positives == 0 and negative.false_positives == 0
    # 全负类上模型给出预测 → FP（样本级）
    noisy = compute_metrics(
        [BenchmarkSample(dataset_id="d", sample_id="n-2", golden_labels_json=[])],
        {"n-2": ["A"]},
    )
    assert noisy.sample_false_positives == 1
    assert noisy.false_positives == 1


def test_metrics_tampering_is_rejected(db_session):
    dataset = _benchmark_dataset(db_session, samples=40)
    run = _benchmark_run(db_session, dataset)
    assert run.result_status == "PASS_GATE"
    baseline = metrics_of(db_session, run.id)
    assert baseline["samples"] == 40

    # 人工把 summary 改成“满分”，逐样本预测未变 → 服务端必须拒绝
    tampered = {**dict(run.metrics_json), "precision": 0.999, "recall": 0.999, "f1": 0.999}
    run.metrics_json = tampered
    db_session.flush()
    with pytest.raises(BenchmarkError) as exc:
        metrics_of(db_session, run.id)
    assert "METRICS_TAMPERED" in str(exc.value)


def test_result_status_tampering_is_rejected(db_session):
    dataset = _benchmark_dataset(db_session, samples=40, fp_ratio=0.5)
    run = _benchmark_run(db_session, dataset, fp_ratio=0.5)
    assert run.result_status != "PASS_GATE"
    run.result_status = "PASS_GATE"
    db_session.flush()
    with pytest.raises(BenchmarkError) as exc:
        metrics_of(db_session, run.id)
    assert "RESULT_STATUS_MISMATCH" in str(exc.value)


def test_dataset_accounting_43_equals_37_plus_6_excluded(db_session):
    """43 条样本 = 37 有效 + 6 剔除（缺 golden labels）；剔除原因逐条记录。"""
    _project(db_session)
    dataset = create_dataset(
        db_session, project_id=1, dataset_key="v162-43", task_type="learning"
    )
    for index in range(43):
        if index < 37:
            add_sample(
                db_session,
                dataset.id,
                sample_id=f"ok-{index:02d}",
                golden_labels=["A"],
            )
        else:
            # 口径缺口：非法/缺失标签的样本只能由历史数据或坏导入产生，这里显式构造。
            db_session.add(
                BenchmarkSample(
                    dataset_id=dataset.id,
                    sample_id=f"bad-{index:02d}",
                    task_type="learning",
                    golden_labels_json=[],
                )
            )
    db_session.flush()
    freeze_dataset(db_session, dataset.id)
    dataset = benchmark_service.get_dataset(db_session, dataset.id)
    assert dataset.sample_count == 43
    assert dataset.gate_eligible is True

    valid, excluded = partition_samples(
        benchmark_service.list_samples(db_session, dataset.id)
    )
    assert len(valid) == 37
    assert len(excluded) == 6
    assert {item["reason"] for item in excluded} == {"MISSING_GOLDEN_LABELS"}

    run = run_benchmark(
        db_session,
        dataset_id=dataset.id,
        agent_key="A6",
        agent_version="1.6.2",
        predictor=lambda sample: {"labels": ["A"]},
    )
    metrics = metrics_of(db_session, run.id)
    assert metrics["total_samples"] == 43
    assert metrics["samples"] == 37
    assert metrics["excluded_samples"] == 6
    assert len(metrics["exclusions"]) == 6
    assert metrics["samples"] + metrics["excluded_samples"] == metrics["total_samples"]
    stored = dict(run.metrics_json["dataset_snapshot"])
    assert stored["sample_count"] == 43
    assert stored["valid_samples"] == 37
    assert stored["excluded_samples"] == 6


def test_dataset_hash_change_invalidates_old_run(db_session):
    dataset = _benchmark_dataset(db_session, samples=40)
    run = _benchmark_run(db_session, dataset)
    metrics_of(db_session, run.id)  # 变化前可引用

    sample = db_session.scalar(
        select(BenchmarkSample)
        .where(BenchmarkSample.dataset_id == dataset.id)
        .order_by(BenchmarkSample.sample_id)
    )
    sample.golden_labels_json = ["B"]
    db_session.flush()
    assert compute_content_hash(
        benchmark_service.list_samples(db_session, dataset.id)
    ) != dataset.content_hash

    with pytest.raises(BenchmarkError) as exc:
        metrics_of(db_session, run.id)
    assert "DATASET_BINDING_STALE" in str(exc.value)

    candidate = create_candidate(
        db_session, project_id=1, rule={"pattern": "HASH_DRIFT"}, source="bug", created_by=5
    )
    with pytest.raises(LearningError):
        evaluate_candidate(db_session, candidate.id, benchmark_run_id=run.id)


def test_old_run_cannot_masquerade_as_new_dataset(db_session):
    first = _benchmark_dataset(db_session, samples=40, key="v162-masq")
    run = _benchmark_run(db_session, first)
    second = _benchmark_dataset(db_session, samples=41, key="v162-masq-next")
    assert second.id != first.id

    # 把旧 Run 挂到新 Dataset 上：绑定快照不一致 → 拒绝
    run.dataset_id = second.id
    db_session.flush()
    with pytest.raises(BenchmarkError) as exc:
        metrics_of(db_session, run.id)
    assert "DATASET_BINDING_STALE" in str(exc.value)


def test_duplicate_and_illegal_samples_rejected(db_session):
    _project(db_session)
    dataset = create_dataset(
        db_session, project_id=1, dataset_key="v162-intake", task_type="learning"
    )
    add_sample(db_session, dataset.id, sample_id="dup-1", golden_labels=["A"])
    with pytest.raises(BenchmarkError) as exc:
        add_sample(db_session, dataset.id, sample_id="dup-1", golden_labels=["A"])
    assert "DUPLICATE_SAMPLE_ID" in str(exc.value)
    with pytest.raises(BenchmarkError) as exc:
        add_sample(db_session, dataset.id, sample_id="bad-label", golden_labels=["bad label!"])
    assert "INVALID_LABEL" in str(exc.value)
    with pytest.raises(BenchmarkError):
        add_sample(db_session, dataset.id, sample_id="no-label", golden_labels=[])


def test_dataset_sample_count_mismatch_rejected(db_session):
    dataset = _benchmark_dataset(db_session, samples=31)
    dataset.sample_count = 30  # 字段口径被篡改
    db_session.flush()
    with pytest.raises(BenchmarkError) as exc:
        benchmark_service.verify_dataset_integrity(db_session, dataset)
    assert "DATASET_SAMPLE_COUNT_MISMATCH" in str(exc.value)


# ══════════════════════════════════════════════════════════
# FIX-006：Learning Candidate 审批/发布身份与状态
# ══════════════════════════════════════════════════════════
def _benchmarked_candidate(db, *, owner: int | None = 5, pattern: str = "V162_PATTERN"):
    dataset = _benchmark_dataset(db, samples=40)
    run = _benchmark_run(db, dataset)
    assert run.result_status == "PASS_GATE"
    candidate = create_candidate(
        db,
        project_id=1,
        rule={"pattern": pattern, "description": "v162"},
        source="bug",
        created_by=owner,
    )
    evaluated = evaluate_candidate(db, candidate.id, benchmark_run_id=run.id)
    assert evaluated.status == "benchmarked", (evaluated.status, evaluated.gate_reasons_json)
    return candidate, run


def test_same_user_approval_rejected(db_session):
    _project(db_session)
    _user(db_session, 5)
    candidate, _ = _benchmarked_candidate(db_session, owner=5)
    with pytest.raises(LearningError) as exc:
        approve_candidate(db_session, candidate.id, approved_by=5)
    assert "OWNER_APPROVER_SAME_USER" in str(exc.value)


def test_approver_role_string_rejected(db_session):
    _project(db_session)
    candidate, _ = _benchmarked_candidate(db_session, owner=5)
    with pytest.raises(LearningError) as exc:
        approve_candidate(db_session, candidate.id, approved_by="QA-Lead")
    assert "APPROVER_ID_INVALID" in str(exc.value)
    with pytest.raises(LearningError):
        approve_candidate(db_session, candidate.id, approved_by=True)


def test_disabled_approver_rejected(db_session):
    _project(db_session)
    _user(db_session, 9, status=0)
    candidate, _ = _benchmarked_candidate(db_session, owner=5)
    with pytest.raises(LearningError) as exc:
        approve_candidate(db_session, candidate.id, approved_by=9)
    assert "APPROVER_DISABLED" in str(exc.value)


def test_approval_and_publish_record_real_user_ids(db_session):
    _project(db_session)
    candidate, _ = _benchmarked_candidate(db_session, owner=5)
    approved = approve_candidate(
        db_session, candidate.id, approved_by=6, approval_reason="two-person"
    )
    assert approved.status == "approved"
    assert approved.approved_by == 6
    event = dict((approved.benchmark_json or {}).get("approval") or {})
    assert event["approved_by_user_id"] == 6
    assert event["owner_user_id"] == 5
    assert event["two_person_policy"] is True

    pattern = publish_candidate(db_session, candidate.id, approved_by=6)
    assert pattern is not None
    published = db_session.get(LearningCandidate, candidate.id)
    assert published.status == "active"
    event = dict((published.benchmark_json or {}).get("approval") or {})
    assert event["published_by_user_id"] == 6
    assert event["approver_user_id"] == 6
    assert event["pattern_key"] == "V162_PATTERN"


def test_publish_requires_approved_state(db_session):
    _project(db_session)
    candidate, _ = _benchmarked_candidate(db_session, owner=5)
    with pytest.raises(LearningError) as exc:
        publish_candidate(db_session, candidate.id, approved_by=6)
    assert "approved" in str(exc.value)

    # 状态被改成 approved 但没有审批记录 → 仍然禁止发布
    candidate.status = "approved"
    db_session.flush()
    with pytest.raises(LearningError) as exc:
        publish_candidate(db_session, candidate.id, approved_by=6)
    assert "审批记录" in str(exc.value)


def test_publish_by_owner_rejected(db_session):
    _project(db_session)
    candidate, _ = _benchmarked_candidate(db_session, owner=5)
    approve_candidate(db_session, candidate.id, approved_by=6)
    with pytest.raises(LearningError) as exc:
        publish_candidate(db_session, candidate.id, approved_by=5)
    assert "OWNER_APPROVER_SAME_USER" in str(exc.value)


def test_duplicate_publish_rejected(db_session):
    _project(db_session)
    candidate, _ = _benchmarked_candidate(db_session, owner=5)
    approve_candidate(db_session, candidate.id, approved_by=6)
    publish_candidate(db_session, candidate.id, approved_by=6)
    with pytest.raises(LearningError):
        publish_candidate(db_session, candidate.id, approved_by=6)


def test_approved_candidate_cannot_be_reevaluated(db_session):
    _project(db_session)
    candidate, run = _benchmarked_candidate(db_session, owner=5)
    approve_candidate(db_session, candidate.id, approved_by=6)
    with pytest.raises(LearningError) as exc:
        evaluate_candidate(db_session, candidate.id, benchmark_run_id=run.id)
    assert "INVALID_STATUS" in str(exc.value)


def test_candidate_benchmark_binding_mismatch_rejected(db_session):
    _project(db_session)
    candidate, _ = _benchmarked_candidate(db_session, owner=5)
    other = _benchmark_dataset(db_session, samples=40, key="v162-other-ds")
    candidate.benchmark_json = {
        **dict(candidate.benchmark_json or {}),
        "dataset_id": other.id,
    }
    db_session.flush()
    with pytest.raises(LearningError) as exc:
        approve_candidate(db_session, candidate.id, approved_by=6)
    assert "数据集" in str(exc.value)


def test_candidate_run_from_other_project_rejected(db_session):
    _project(db_session)
    _project(db_session, 2)
    other_dataset = create_dataset(
        db_session, project_id=2, dataset_key="v162-p2", task_type="learning"
    )
    for index in range(40):
        add_sample(
            db_session,
            other_dataset.id,
            project_id=2,
            sample_id=f"p2-{index:03d}",
            golden_labels=["A"],
        )
    freeze_dataset(db_session, other_dataset.id, project_id=2)
    other_run = run_benchmark(
        db_session,
        dataset_id=other_dataset.id,
        project_id=2,
        agent_key="A6",
        predictor=lambda sample: {"labels": ["A"]},
    )
    candidate = create_candidate(
        db_session, project_id=1, rule={"pattern": "P1_ONLY"}, created_by=5
    )
    with pytest.raises(LearningError):
        evaluate_candidate(db_session, candidate.id, benchmark_run_id=other_run.id)


def test_legacy_run_without_dataset_snapshot_cannot_be_used(db_session):
    """旧 Run（无 dataset_snapshot）不得作为当前数据集证据。"""
    _project(db_session)
    dataset = _benchmark_dataset(db_session, samples=31)
    run = _benchmark_run(db_session, dataset, fp_ratio=0.0)
    legacy = BenchmarkRun(
        project_id=1,
        dataset_id=dataset.id,
        agent_key="A6",
        status="COMPLETED",
        result_status=run.result_status,
        metrics_json={k: v for k, v in dict(run.metrics_json).items() if k != "dataset_snapshot"},
        per_sample_json=run.per_sample_json,
    )
    db_session.add(legacy)
    db_session.flush()
    with pytest.raises(BenchmarkError) as exc:
        metrics_of(db_session, legacy.id)
    assert "DATASET_SNAPSHOT_MISSING" in str(exc.value)
