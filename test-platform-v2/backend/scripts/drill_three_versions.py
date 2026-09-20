"""体育试点「连续 3 个版本」演练驱动（Batch 261 / B4-3/4/5）。

用途：在**有环境的机器**（接 VPN、库内有体育资产、本机跑着 cameltv-node）上一条命令跑完 3 个版本，
产出 09 §2.3 四项 DoD 的数字（≤1 人日/版本、证据完整率 100%、复用命中率 ≥50%、连续 ≥3 版）。

用法：
    python scripts/drill_three_versions.py \
        --project-id 1 --environment-id 9 --account-slot sports-tester-01 \
        --base-url https://swiftbugs.cn --target-url http://camel-api-gateway05.svc.elelive.cn \
        --user-token <用户 JWT> --versions 3 --person-hours-per-version 1.5

凭据口径（Batch 265 修正）：
  - 「登记任务 / 查任务 / 校验证据包」属于**用户**端点（`execution:manage` / `execution:view`），
    必须用用户 JWT（`--user-token`，或用 `--username/--password` 现登录取 JWT）；
  - `--node-token` 只是**节点侧**凭据（认领/心跳/上报由 cameltv-node 使用），**不能**用于登记任务；
    本脚本不再用它发 HTTP 请求，保留参数仅为兼容旧命令行并给出明确提示。

**诚实原则（不可绕过）**：
  - 前置检查不过 → 打印**具体缺哪一环**并以退出码 4 结束，**不会继续跑**；
  - 被测系统不可达时**不会用本地替身顶替**体育验收（这正是 C258-1 的成因）；
  - 单版本"需求→方案"的人工耗时无法自动测量，必须由执行者用 --person-hours-per-version 如实提供。

退出码：0 = SLO 达成；4 = 环境未就绪（含阻塞清单）；5 = 跑完但 SLO 未达成。
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx  # noqa: E402
from sqlalchemy import func, select  # noqa: E402

from app.core.db import SessionLocal  # noqa: E402
from app.models.ai_job import AiAgent  # noqa: E402
from app.models.test_case import TestCase  # noqa: E402
from app.modules.aitde.continuous.models import EnvironmentFingerprint  # noqa: E402
from app.services import pilot_dataset_service, pilot_slo_service  # noqa: E402

EXIT_OK = 0
EXIT_NOT_READY = 4
EXIT_SLO_NOT_MET = 5

# C269-2：瞬断重试的口径（测试可覆盖这两个常量以避免真的 sleep）
RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 1.5


def collect_preflight(args) -> dict:
    checks = {
        "database_ok": False,
        "dataset_meets_target": False,
        "fingerprint_present": False,
        "node_online": False,
        "target_reachable": False,
        "account_slot_configured": bool(args.account_slot.strip()),
    }
    dataset: dict = {}
    try:
        with SessionLocal() as db:
            checks["database_ok"] = True
            dataset = pilot_dataset_service.select_pilot_cases(
                db,
                project_id=args.project_id,
                api_limit=args.api_limit,
                web_limit=args.web_limit,
                module_prefix=args.module_prefix,
            )
            checks["dataset_meets_target"] = bool(dataset.get("meets_target"))
            checks["fingerprint_present"] = bool(
                db.scalar(
                    select(func.count())
                    .select_from(EnvironmentFingerprint)
                    .where(EnvironmentFingerprint.environment_id == args.environment_id)
                )
            )
            checks["node_online"] = bool(
                db.scalar(
                    select(func.count())
                    .select_from(AiAgent)
                    .where(AiAgent.status == "online", AiAgent.project_scope == args.project_id)
                )
            )
    except Exception as exc:  # noqa: BLE001 - 预检失败要变成可读结论，不是堆栈
        print(f"[preflight] 数据库检查失败: {type(exc).__name__}: {str(exc)[:200]}")

    if args.target_url:
        try:
            httpx.get(args.target_url, timeout=args.target_timeout, trust_env=False)
            checks["target_reachable"] = True
        except httpx.HTTPError as exc:
            print(f"[preflight] 被测系统不可达: {type(exc).__name__}: {str(exc)[:160]}")
    return checks, dataset


def _api_client(args) -> httpx.Client:
    return httpx.Client(base_url=args.base_url.rstrip("/"), timeout=120, trust_env=False)


def _json_or(raw, default):
    if raw in (None, ""):
        return default
    if isinstance(raw, (dict, list)):
        return raw
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return default


def _load_executable_cases(args, dataset: dict) -> tuple[list[dict], list[dict], list[str]]:
    """把试点集选中项换成**可执行定义**（Batch 266 / C264-3）。

    此前 driver 把 `select_pilot_cases` 的 brief（只有 id/title/module/priority）直接当 payload，
    节点拿不到 method/path/断言与 url/steps：
      - API 侧回落成裸 `GET <base>/` → 404；
      - Web 侧 `steps=[]` → 截图即通过（**空过**）。
    现在按 case id 从平台库取结构化字段；取不到可执行定义就**明确报错**，不再空过。
    """
    api_briefs = dataset.get("api", [])
    web_briefs = dataset.get("web", [])
    ids = [int(c["id"]) for c in api_briefs + web_briefs if str(c.get("id", "")).isdigit()]
    rows: dict[int, TestCase] = {}
    if ids:
        with SessionLocal() as db:
            rows = {row.id: row for row in db.scalars(select(TestCase).where(TestCase.id.in_(ids))).all()}

    api_cases: list[dict] = []
    web_cases: list[dict] = []
    unexecutable: list[str] = []

    for brief in api_briefs:
        row = rows.get(int(brief["id"])) if str(brief.get("id", "")).isdigit() else None
        endpoint = (getattr(row, "api_endpoint", "") or "").strip()
        if row is None or not endpoint:
            unexecutable.append(f"api:{brief.get('id')}")
            continue
        api_cases.append({
            "id": f"case:{row.id}",
            "name": row.title,
            "request": {
                "method": (row.api_method or "GET").upper(),
                "url": endpoint,
                "headers": _json_or(row.api_headers, {}),
                "body": _json_or(row.api_body, None),
            },
            "assertions": _json_or(row.api_assertions, []),
        })

    for brief in web_briefs:
        row = rows.get(int(brief["id"])) if str(brief.get("id", "")).isdigit() else None
        steps = _json_or(getattr(row, "steps", "[]"), []) if row is not None else []
        executable = [s for s in steps if isinstance(s, dict) and s.get("action")]
        if row is None or not executable:
            unexecutable.append(f"web:{brief.get('id')}")
            continue
        web_cases.append({"id": f"case:{row.id}", "name": row.title, "steps": executable})

    return api_cases, web_cases, unexecutable


def _auth_headers(args) -> dict[str, str]:
    """用户态请求头（Batch 265 / C264-3）。

    `POST /api/v1/execution-jobs` 等端点依赖 `require_permission("execution:manage")`，
    只认用户 JWT；早期版本误用节点令牌（`X-AI-Agent-Token`）导致必然 401。
    """
    token = (args.user_token or "").strip()
    if not token and args.username:
        with _api_client(args) as client:
            resp = client.post(
                "/api/v1/auth/login",
                json={"username": args.username, "password": args.password or ""},
            )
            resp.raise_for_status()
            token = ((resp.json().get("data") or {}).get("access_token") or "").strip()
    if not token:
        raise SystemExit(
            "缺少用户凭据：请用 --user-token <JWT> 或 --username/--password 登录。"
            "节点令牌（--node-token）只用于节点侧认领，不能登记任务（见 C264-3）。"
        )
    return {"Authorization": f"Bearer {token}", "X-Project-Id": str(args.project_id)}


def _platform_reuse_stats(client, headers: dict) -> tuple[int, int]:
    """读平台埋点的复用建议命中率（Batch 268 / C267-3）。

    B3-4 的 `reuse_suggestion_event` 现已在"建任务带出建议"时写入；驱动应**读平台指标**
    而不是依赖人工输入（人工口径保留为回退）。返回 (suggested, adopted)。
    """
    data = _reuse_stats_full(client, headers)
    return int(data.get("suggested") or 0), int(data.get("adopted") or 0)


def _request_with_retry(
    client,
    method: str,
    url: str,
    *,
    attempts: int | None = None,
    backoff: float | None = None,
    **kwargs,
):
    """C269-2：只对**瞬时传输错误**（以及幂等 GET 的 5xx）做有界重试。

    Batch 269 实测：本机试点实例（单进程 uvicorn + SQLite）会在负载下重置 localhost
    连接，一次 `httpx.ReadError` 就让整轮 3 版本演练白跑（4 次尝试全废，每次约 20 分钟）。
    这里重试的是"可能只是抖动"的情况；**HTTP 4xx 与断言失败一律不重试**——那是真问题，
    不能靠重试掩盖。POST 的 5xx 也不重试，避免重复登记任务。
    """
    attempts = RETRY_ATTEMPTS if attempts is None else attempts
    backoff = RETRY_BACKOFF_SECONDS if backoff is None else backoff
    retry_5xx = method.upper() == "GET"
    total = max(1, attempts)
    for index in range(total):
        last_attempt = index + 1 >= total
        try:
            resp = client.request(method, url, **kwargs)
        except httpx.TransportError:
            if last_attempt:
                raise
            time.sleep(backoff * (index + 1))
            continue
        if retry_5xx and resp.status_code >= 500 and not last_attempt:
            time.sleep(backoff * (index + 1))
            continue
        return resp
    raise RuntimeError("unreachable")  # pragma: no cover - 循环内必然 return 或 raise


def _get(client, url: str, **kwargs):
    return _request_with_retry(client, "GET", url, **kwargs)


def _post(client, url: str, **kwargs):
    return _request_with_retry(client, "POST", url, **kwargs)


def _reuse_stats_full(client, headers: dict) -> dict:
    """平台累计复用读数（失败即返回空 dict，调用方按缺失处理，不编数字）。"""
    try:
        resp = _get(client, "/api/v1/version-tasks/knowledge/reuse-stats", headers=headers)
    except httpx.HTTPError:
        return {}
    if resp.status_code != 200:
        return {}
    return (resp.json() or {}).get("data") or {}


def _suggestion_refs(client, headers: dict) -> list[tuple[str, str]]:
    """(suggestion_ref, title) —— 必须与 `version_task_service.create_task` 写入的 ref 同构。

    create_task 用 `f"knowledge:{记录id}:{条目标题}"` 写 `decision='suggested'`；这里读同一个
    数据源（`GET /version-tasks/knowledge/reuse`）重建 ref，才能命中 `record_decision` 的守卫。
    """
    resp = _get(
        client,
        "/api/v1/version-tasks/knowledge/reuse",
        headers=headers,
        params={"limit": 5},
    )
    if resp.status_code != 200:
        return []
    out: list[tuple[str, str]] = []
    for record in (resp.json() or {}).get("data") or []:
        for title in record.get("reuse") or []:
            out.append((f"knowledge:{record.get('id')}:{title}", str(title)))
    return out


def _load_decisions(raw: str) -> dict:
    """逐版本复用决策文件：`{ "<版本>": {"adopted": [...], "rejected": [...], "reason": "..."} }`。"""
    if not raw:
        return {}
    path = Path(raw)
    if not path.exists():
        raise SystemExit(f"决策文件不存在：{path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SystemExit(f"决策文件无法解析：{exc}") from exc


def _decisions_for(decisions: dict, version: str) -> dict:
    entry = decisions.get(version) or decisions.get("_default") or {}
    return {
        "adopted": [str(x) for x in entry.get("adopted") or []],
        "rejected": [str(x) for x in entry.get("rejected") or []],
        "reason": str(entry.get("reason") or ""),
    }


def _apply_decisions(client, headers: dict, task_id: int, refs, decisions: dict) -> dict:
    """把操作者对**本版本**建议的采纳/否掉写回平台（只认本版本真正带出过的 ref）。"""
    ref_by_title: dict[str, str] = {}
    for ref, title in refs:
        ref_by_title.setdefault(title, ref)
    applied: dict = {
        "adopted": [],
        "rejected": [],
        "missing": [],
        "reason": decisions.get("reason", ""),
    }
    for decision in ("adopted", "rejected"):
        for title in decisions.get(decision) or []:
            ref = ref_by_title.get(title)
            if not ref:
                applied["missing"].append(f"{decision}:{title}")
                continue
            resp = _post(
                client,
                "/api/v1/version-tasks/knowledge/reuse-decisions",
                json={"task_id": task_id, "suggestion_ref": ref, "decision": decision},
                headers=headers,
            )
            if resp.status_code >= 400:
                applied["missing"].append(f"{decision}:{title}:HTTP{resp.status_code}")
                continue
            applied[decision].append(title)
    return applied


def _write_report(path: str, payload: dict) -> None:
    """C269-2：每完成一版就落盘一次，崩溃不再丢全部进度。"""
    if not path:
        return
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def run_versions(args, dataset: dict) -> list[dict]:
    """逐版本：登记任务 → 等节点跑完 → 校验证据包 → 记录指标。"""
    api_cases, web_cases, unexecutable = _load_executable_cases(args, dataset)
    if unexecutable:
        raise SystemExit(
            "以下试点用例缺少可执行定义（api_endpoint 或 steps[].action）："
            + ", ".join(unexecutable[:10])
            + (" …" if len(unexecutable) > 10 else "")
            + "；请先补齐用例定义再跑（不空过，见 C264-3）"
        )
    case_refs = [c["id"] for c in api_cases + web_cases]
    payload = {
        "api": {"base_url": args.target_url, "cases": api_cases},
        "web": {"base_url": args.web_target_url or args.target_url, "cases": web_cases},
    }
    decisions_cfg = _load_decisions(getattr(args, "decisions_json", ""))
    reuse_mode = getattr(args, "reuse_mode", "version-task")
    versions: list[dict] = []
    with _api_client(args) as client:
        headers = _auth_headers(args)
        for index in range(args.versions):
            version_label = f"{args.version_prefix}{index + 1}"
            started = datetime.now()

            # ① C269-1：**逐版本走版本任务流程**。建任务这一刻平台才会自动带出上版复用建议并写
            #    `decision='suggested'` 事件——Batch 269 的教训是"只登记执行任务"会让被验收的版本
            #    既没有版本记录、也不产生任何复用数据（命中率只能读到别的流程留下的旧数字）。
            stats_before: dict = {}
            task_id: int | None = None
            suggested_self = adopted_self = rejected_self = 0
            decisions_applied: dict = {}
            if reuse_mode == "version-task":
                stats_before = _reuse_stats_full(client, headers)
                created_task = _post(
                    client,
                    "/api/v1/version-tasks",
                    json={
                        "title": f"{version_label} 连续验收（drill）",
                        "version": version_label,
                        "environment_id": args.environment_id,
                    },
                    headers=headers,
                )
                if created_task.status_code >= 400:
                    # Batch 270 实跑命中：version_task 有 (project_id, version) 唯一约束，
                    # 重复用同一版本号时平台返回 500（不是 409），裸栈很难读懂 → 这里给出可操作提示。
                    raise SystemExit(
                        f"建版本任务失败：HTTP {created_task.status_code} "
                        f"（version={version_label}）。若该版本号已存在"
                        "（version_task 的 project_id+version 唯一），请用 `--version-prefix` "
                        "换一个版本系列后重跑；不要删既有版本记录来腾位置。"
                    )
                task_id = int((created_task.json() or {})["data"]["id"])

            # ② 跑该版本的执行任务（接口 + Web）
            job_ids: list[int] = []
            for kind in ("api", "web"):
                spec = payload[kind]
                if not spec["cases"]:
                    continue
                created = _post(
                    client,
                    "/api/v1/execution-jobs",
                    json={
                        "kind": kind,
                        "case_refs": case_refs,
                        "env_ref": args.account_slot,
                        "payload": spec,
                    },
                    headers=headers,
                )
                created.raise_for_status()
                job_ids.append(int(created.json()["data"]["id"]))

            evidence_complete = True
            for job_id in job_ids:
                deadline = time.time() + args.job_timeout
                while time.time() < deadline:
                    job = _get(client, f"/api/v1/execution-jobs/{job_id}", headers=headers)
                    state = (job.json() or {}).get("data") or {}
                    if state.get("status") in {"completed", "failed", "cancelled"}:
                        break
                    time.sleep(5)
                verified = (
                    _get(client, f"/api/v1/execution-jobs/{job_id}/evidence/verify", headers=headers).json()
                    or {}
                ).get("data") or {}
                evidence_complete = evidence_complete and bool(
                    verified.get("verdict") == "verified"
                    and (verified.get("completeness") or {}).get("complete")
                )
            execution_hours = round((datetime.now() - started).total_seconds() / 3600, 3)

            # ③ 复用决策（人工口径，逐版本）→ 读**本版本增量**
            cumulative: dict = {}
            if reuse_mode == "version-task" and task_id is not None:
                stats_after_task = _reuse_stats_full(client, headers)
                suggested_self = max(
                    0,
                    int(stats_after_task.get("suggested") or 0)
                    - int(stats_before.get("suggested") or 0),
                )
                decisions_applied = _apply_decisions(
                    client,
                    headers,
                    task_id,
                    _suggestion_refs(client, headers),
                    _decisions_for(decisions_cfg, version_label),
                )
                stats_after_decisions = _reuse_stats_full(client, headers)
                cumulative = stats_after_decisions
                adopted_self = max(
                    0,
                    int(stats_after_decisions.get("adopted") or 0)
                    - int(stats_after_task.get("adopted") or 0),
                )
                rejected_self = max(
                    0,
                    int(stats_after_decisions.get("rejected") or 0)
                    - int(stats_after_task.get("rejected") or 0),
                )
                reuse_suggested, reuse_adopted = suggested_self, adopted_self
                reuse_source = "platform:version-task-delta"
            else:
                reuse_suggested, reuse_adopted = args.reuse_suggested, args.reuse_adopted
                reuse_source = "operator"
                if not reuse_suggested and not reuse_adopted:
                    cumulative = _reuse_stats_full(client, headers)
                    reuse_suggested, reuse_adopted = _platform_reuse_stats(client, headers)
                    reuse_source = "platform:cumulative"

            versions.append(
                {
                    "version": version_label,
                    "version_task_id": task_id,
                    "job_ids": job_ids,
                    # 人工审核耗时无法自动测量 → 由执行者如实提供
                    "person_hours": args.person_hours_per_version,
                    "execution_hours": execution_hours,
                    "evidence_complete": evidence_complete,
                    # ⑦ 的分子分母用**本版本自产**的数字（version-task 模式）
                    "reuse_suggested": reuse_suggested,
                    "reuse_adopted": reuse_adopted,
                    "reuse_rejected": rejected_self,
                    "reuse_source": reuse_source,
                    "decisions": decisions_applied,
                    "cumulative_reuse": cumulative,
                }
            )
            print(
                f"[version {version_label}] task={task_id} jobs={job_ids} "
                f"evidence_complete={evidence_complete} "
                f"reuse={reuse_adopted}/{reuse_suggested} ({reuse_source})"
            )
            # ④ C269-2：每版落盘，崩溃不再丢全部进度
            _write_report(
                args.out,
                {
                    "status": "running",
                    "partial": True,
                    "reuse_mode": reuse_mode,
                    "versions": versions,
                },
            )
    return versions


def main() -> int:
    parser = argparse.ArgumentParser(description="体育试点连续 3 版本演练")
    parser.add_argument("--project-id", type=int, required=True)
    parser.add_argument("--environment-id", type=int, required=True)
    parser.add_argument("--account-slot", default="", help="账号槽位名（不是凭据）")
    parser.add_argument("--base-url", required=True, help="平台 API 地址")
    parser.add_argument("--target-url", default="", help="被测系统地址（Test5 网关，需 VPN）")
    parser.add_argument("--web-target-url", default="", help="Web 用例基址（默认同 --target-url）")
    parser.add_argument("--user-token", default="", help="用户 JWT（登记/查询任务用；execution:manage）")
    parser.add_argument("--username", default="", help="平台账号（与 --password 一起，用于现登录取 JWT）")
    parser.add_argument("--password", default="", help="平台密码（仅当未提供 --user-token 时使用）")
    parser.add_argument(
        "--node-token",
        default="",
        help="节点令牌（保留兼容；仅节点侧使用，本脚本不再用它发请求）",
    )
    parser.add_argument("--module-prefix", default="体育")
    parser.add_argument("--api-limit", type=int, default=pilot_dataset_service.PILOT_API_TARGET)
    parser.add_argument("--web-limit", type=int, default=pilot_dataset_service.PILOT_WEB_TARGET)
    parser.add_argument("--versions", type=int, default=3)
    parser.add_argument("--version-prefix", default="16.")
    parser.add_argument("--person-hours-per-version", type=float, default=None)
    parser.add_argument("--reuse-suggested", type=int, default=0)
    parser.add_argument("--reuse-adopted", type=int, default=0)
    parser.add_argument(
        "--reuse-mode",
        choices=["version-task", "cumulative"],
        default="version-task",
        help=(
            "复用口径：version-task（默认）= 逐版本建版本任务并按**本版本增量**取数与记决策；"
            "cumulative = 旧行为（读平台累计读数或吃 --reuse-suggested/--reuse-adopted 人工输入）"
        ),
    )
    parser.add_argument(
        "--decisions-json",
        default="",
        help=(
            '逐版本复用决策（人工口径）：{"<版本>": {"adopted": ["条目标题"], "rejected": [...], '
            '"reason": "..."}}；未列出的条目保持 pending（不计入分子）'
        ),
    )
    parser.add_argument("--job-timeout", type=float, default=1800.0)
    parser.add_argument("--target-timeout", type=float, default=6.0)
    parser.add_argument("--out", default="", help="报告输出路径（JSON）")
    args = parser.parse_args()

    checks, dataset = collect_preflight(args)
    blockers = pilot_slo_service.preflight_blockers(checks)
    if blockers:
        print(json.dumps(
            {
                "status": "not_ready",
                "checks": checks,
                "blockers": blockers,
                "dataset": {k: dataset.get(k) for k in ("counts", "targets", "shortfall")},
                "note": "环境未就绪，未执行任何版本（不会用本地替身顶替体育验收）",
            },
            ensure_ascii=False,
            indent=2,
        ))
        return EXIT_NOT_READY

    versions = run_versions(args, dataset)
    slo = pilot_slo_service.compute_slo(versions)
    report = {
        "status": "completed",
        "partial": False,
        "reuse_mode": args.reuse_mode,
        "checks": checks,
        "dataset": dataset,
        "versions": versions,
        "slo": slo,
        "environment_fingerprint_source": "environment_fingerprints",
        "account_slot": args.account_slot,
    }
    if args.out:
        _write_report(args.out, report)
        print(f"报告已写入 {args.out}")
    print(
        json.dumps(
            {"meets_all": slo["meets_all"], "consecutive_passing": slo["consecutive_passing"]},
            ensure_ascii=False,
        )
    )
    return EXIT_OK if slo["meets_all"] else EXIT_SLO_NOT_MET


if __name__ == "__main__":
    raise SystemExit(main())
