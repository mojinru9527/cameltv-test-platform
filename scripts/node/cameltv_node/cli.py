"""cameltv-node —— CamelTv 本地执行节点 CLI（Batch 258 / B1-5）。

一条命令开工：
    cameltv-node up --node-id my-pc --capabilities api web

它做四件事（全部在**本机**完成，控制面不执行任何浏览器/模型动作）：
    1) 注册/复用节点身份（节点令牌，仅返回一次，存 ~/.cameltv-node.json）
    2) 心跳续租（执行中每 30s 一次，租约默认 300s）
    3) 认领本项目的 ExecutionJob，拉取载荷并真实执行（api=httpx / web=Playwright）
    4) 上传证据（sha256 manifest 对账）→ 上报结果

**诚实原则**：依赖缺失、执行失败、上传失败一律如实上报/打印；断网时保持心跳重试，
不谎报失败——任务会因租约过期被平台回收为 pending，节点恢复后可再次认领。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from pathlib import Path

import httpx

# 允许两种入口：`python scripts/node/cameltv_node/cli.py` 与 `python -m cameltv_node.cli`
if __package__ in (None, ""):  # pragma: no cover - 取决于调用方式
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cameltv_node import evidence, executor  # noqa: E402

CONFIG_PATH = Path.home() / ".cameltv-node.json"
DEFAULT_BASE = "https://swiftbugs.cn"
DEFAULT_HEARTBEAT_SECONDS = 30


class TransportDown(RuntimeError):
    """平台不可达（断网/网络抖动）：调用方应重试而不是判定任务失败。"""


def load_config() -> dict:
    cfg = {
        "base_url": os.environ.get("CAMELTV_BASE_URL", DEFAULT_BASE),
        "node_id": os.environ.get("CAMELTV_NODE_ID", ""),
        "token": os.environ.get("CAMELTV_NODE_TOKEN", ""),
        "jwt": os.environ.get("CAMELTV_JWT", ""),
        "project_id": os.environ.get("CAMELTV_PROJECT_ID", ""),
    }
    if CONFIG_PATH.exists():
        try:
            stored = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            cfg.update({key: value for key, value in stored.items() if value})
        except (json.JSONDecodeError, OSError):
            pass
    return cfg


def save_config(cfg: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def call(
    cfg: dict,
    method: str,
    path: str,
    *,
    body=None,
    params=None,
    use_node_token: bool = True,
    files=None,
    timeout: float = 300,
):
    headers: dict[str, str] = {}
    if cfg.get("project_id"):
        headers["X-Project-Id"] = str(cfg["project_id"])
    if use_node_token and cfg.get("token"):
        headers["X-AI-Agent-Token"] = cfg["token"]
    if cfg.get("jwt"):
        headers["Authorization"] = f"Bearer {cfg['jwt']}"
    if files is None:
        headers["Content-Type"] = "application/json"
    url = cfg["base_url"].rstrip("/") + "/api/v1" + path
    try:
        resp = httpx.request(
            method, url, headers=headers, json=body, params=params, files=files, timeout=timeout
        )
    except httpx.TransportError as exc:
        raise TransportDown(f"平台不可达: {type(exc).__name__}: {exc}") from exc
    try:
        payload = resp.json()
    except ValueError:
        payload = {"code": resp.status_code, "msg": resp.text[:300]}
    if resp.status_code >= 400 or payload.get("code") not in (None, 0):
        print(
            f"ERROR {method} {path} -> HTTP {resp.status_code} code={payload.get('code')} "
            f"msg={payload.get('msg') or payload.get('detail')}",
            file=sys.stderr,
        )
        raise SystemExit(2)
    return payload.get("data", payload)


# ── 身份 ───────────────────────────────────────────────────────

def cmd_login(args, cfg) -> int:
    password = args.password or os.environ.get("CAMELTV_PASSWORD", "")
    if not password:
        import getpass

        password = getpass.getpass("请输入平台密码: ")
    url = cfg["base_url"].rstrip("/") + "/api/v1/auth/login"
    try:
        resp = httpx.post(url, json={"username": args.username, "password": password}, timeout=60)
    except httpx.TransportError as exc:
        print(f"ERROR: 平台不可达: {exc}", file=sys.stderr)
        return 2
    payload = resp.json() if resp.content else {}
    token = (payload.get("data") or {}).get("access_token") or ""
    if not token:
        print(
            f"ERROR: 登录失败 -> HTTP {resp.status_code} msg={payload.get('msg') or payload.get('detail')}",
            file=sys.stderr,
        )
        return 2
    cfg["jwt"] = token
    if args.project_id:
        cfg["project_id"] = str(args.project_id)
    save_config(cfg)
    print(json.dumps({"ok": True, "username": args.username, "saved_to": str(CONFIG_PATH)}, ensure_ascii=False))
    return 0


def cmd_register(args, cfg) -> int:
    if not cfg.get("jwt"):
        print("ERROR: 缺少平台登录态，请先执行 login --username <账号>", file=sys.stderr)
        return 2
    data = call(
        cfg,
        "POST",
        "/ai/agents/register",
        body={"agent_id": args.node_id, "capabilities": args.capabilities},
        use_node_token=False,
    )
    cfg["node_id"] = data.get("agent_id") or args.node_id
    cfg["token"] = data.get("token") or cfg.get("token", "")
    if args.project_id:
        cfg["project_id"] = str(args.project_id)
    save_config(cfg)
    print(
        json.dumps(
            {
                "node_id": cfg["node_id"],
                "project_scope": data.get("project_scope"),
                "token_saved_to": str(CONFIG_PATH),
                "notice": data.get("token_notice"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def cmd_doctor(args, cfg) -> int:
    report = {
        "base_url": cfg["base_url"],
        "node_id": cfg.get("node_id"),
        "project_id": cfg.get("project_id"),
        "token_configured": bool(cfg.get("token")),
    }
    try:
        status = call(cfg, "GET", "/execution-jobs/node-status")
        report["node_status"] = status
        report["ok"] = True
    except SystemExit:
        report["ok"] = False
        report["error"] = "节点状态查询失败（检查项目上下文与 execution:view 权限）"
    except TransportDown as exc:
        report["ok"] = False
        report["error"] = str(exc)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("ok") else 2


# ── 任务流转 ───────────────────────────────────────────────────

def _claim(cfg: dict) -> dict | None:
    data = call(cfg, "POST", "/execution-jobs/claim", body={"node_id": cfg["node_id"]})
    return data or None


def _fetch_payload(cfg: dict, job_id: int) -> dict:
    return call(
        cfg, "GET", f"/execution-jobs/{job_id}/payload", params={"node_id": cfg["node_id"]}
    )


def _heartbeat_once(cfg: dict, job_id: int) -> bool:
    try:
        call(cfg, "POST", f"/execution-jobs/{job_id}/heartbeat", body={"node_id": cfg["node_id"]})
        return True
    except TransportDown:
        return False
    except SystemExit:
        return False


class HeartbeatThread(threading.Thread):
    """执行期间续租；断网只记录，不把任务判死（租约到期由平台回收）。"""

    def __init__(self, cfg: dict, job_id: int, interval: float):
        super().__init__(daemon=True)
        self._cfg = cfg
        self._job_id = job_id
        self._interval = max(5.0, float(interval))
        # 注意：不能命名成 `_stop` —— threading.Thread 内部有同名方法，
        # 覆盖它会让解释器在收尾时调用我们的 Event 对象 → TypeError: not callable。
        self._stop_event = threading.Event()
        self.lost = False

    def run(self) -> None:
        while not self._stop_event.wait(self._interval):
            ok = _heartbeat_once(self._cfg, self._job_id)
            if not ok:
                self.lost = True
                print(f"[warn] 心跳失败（job {self._job_id}），任务可能被判超时回收", file=sys.stderr)

    def stop(self) -> None:
        self._stop_event.set()
        self.join(timeout=5)


def _upload_evidence(cfg: dict, job_id: int, directory: Path) -> dict:
    files = evidence.collect_files(directory)
    local = evidence.local_manifest(files)
    multipart = [("files", (name, data, "application/octet-stream")) for name, data in files]
    remote = call(
        cfg,
        "POST",
        f"/execution-jobs/{job_id}/evidence",
        params={"node_id": cfg["node_id"]},
        files=multipart,
        timeout=600,
    )
    problems = evidence.verify_against(remote, local)
    if problems:
        raise RuntimeError("证据上传对账失败: " + "; ".join(problems))
    return remote


def _execute(cfg: dict, job: dict, payload: dict, work_dir: Path) -> dict:
    kind = job.get("kind")
    cases = (payload.get("payload") or {}).get("cases") or []
    base_url = (payload.get("payload") or {}).get("base_url") or ""
    if not cases:
        return {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "all_pass": False,
            "cases": [],
            "error": "任务载荷不含任何用例",
        }
    try:
        if kind == "api":
            return executor.run_api_cases(cases, evidence_dir=work_dir, base_url=base_url)
        if kind == "web":
            return executor.run_web_cases(cases, evidence_dir=work_dir, base_url=base_url)
        return {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "all_pass": False,
            "cases": [],
            "error": f"未知任务类型: {kind}",
        }
    except executor.ExecutorUnavailable as exc:
        return {
            "total": len(cases),
            "passed": 0,
            "failed": len(cases),
            "all_pass": False,
            "cases": [],
            "error": str(exc),
        }


def _handle_job(cfg: dict, job: dict, *, work_root: Path, heartbeat_seconds: float) -> dict:
    job_id = job["id"]
    work_dir = work_root / f"job-{job_id}-attempt-{job.get('attempt', 1)}"
    work_dir.mkdir(parents=True, exist_ok=True)
    print(f"[job {job_id}] kind={job.get('kind')} attempt={job.get('attempt')} env={job.get('env_ref')}")

    heartbeat = HeartbeatThread(cfg, job_id, heartbeat_seconds)
    heartbeat.start()
    try:
        payload = _fetch_payload(cfg, job_id)
        results = _execute(cfg, job, payload, work_dir)
        (work_dir / executor.RESULT_FILE).write_text(
            json.dumps(results, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
        )
        uploaded = 0
        upload_error = ""
        if results.get("cases"):
            try:
                manifest = _upload_evidence(cfg, job_id, work_dir)
                uploaded = int(manifest.get("file_count", 0))
            except (RuntimeError, SystemExit) as exc:
                upload_error = str(exc)
                print(f"[warn] 证据上传失败: {upload_error}", file=sys.stderr)
        status = "completed" if results.get("all_pass") else "failed"
        summary = (
            f"{results.get('passed', 0)}/{results.get('total', 0)} pass"
            + (f" | {results['error']}" if results.get("error") else "")
        )
        call(
            cfg,
            "POST",
            f"/execution-jobs/{job_id}/report",
            body={
                "node_id": cfg["node_id"],
                "status": status,
                "summary": summary,
                "result": {
                    "total": results.get("total", 0),
                    "passed": results.get("passed", 0),
                    "failed": results.get("failed", 0),
                    "evidence_files": uploaded,
                    "upload_error": upload_error,
                    "error": results.get("error", ""),
                },
                "error_message": results.get("error", "") or upload_error,
            },
        )
        print(f"[job {job_id}] {status} — {summary}（证据 {uploaded} 个文件）")
        return {
            "job_id": job_id,
            "status": status,
            "summary": summary,
            "evidence_files": uploaded,
            "heartbeat_lost": heartbeat.lost,
        }
    finally:
        heartbeat.stop()


def _loop(cfg: dict, args) -> int:
    work_root = Path(args.work_dir).expanduser()
    work_root.mkdir(parents=True, exist_ok=True)
    idle = 0
    print(f"cameltv-node up — node={cfg['node_id']} base={cfg['base_url']} work={work_root}")
    while True:
        try:
            job = _claim(cfg)
        except TransportDown as exc:
            print(f"[warn] {exc}；{args.poll_seconds}s 后重试（任务不会被判失败）", file=sys.stderr)
            time.sleep(args.poll_seconds)
            continue
        if not job:
            idle += 1
            if idle % 10 == 1:
                print("[idle] 暂无待执行任务")
            if args.once:
                return 0
            time.sleep(args.poll_seconds)
            continue
        idle = 0
        try:
            _handle_job(cfg, job, work_root=work_root, heartbeat_seconds=args.heartbeat_seconds)
        except TransportDown as exc:
            print(
                f"[warn] 执行中断线：{exc}；任务将因租约过期回到 pending，节点恢复后可再次认领",
                file=sys.stderr,
            )
        if args.once:
            return 0
        time.sleep(args.poll_seconds)


# ── 离线执行/上传 ──────────────────────────────────────────────

def cmd_run_api(args, cfg) -> int:
    return _run_offline(args, cfg, kind="api")


def cmd_run_web(args, cfg) -> int:
    return _run_offline(args, cfg, kind="web")


def _run_offline(args, cfg, *, kind: str) -> int:
    out = Path(args.out).expanduser()
    if args.job_file:
        spec = json.loads(Path(args.job_file).read_text(encoding="utf-8"))
    elif args.job:
        spec = _fetch_payload(cfg, args.job)
    else:
        print("ERROR: 需要 --job <id> 或 --job-file <payload.json>", file=sys.stderr)
        return 2
    payload = spec.get("payload") or {}
    cases = payload.get("cases") or []
    base_url = args.base_url or payload.get("base_url") or ""
    runner = executor.run_api_cases if kind == "api" else executor.run_web_cases
    try:
        results = runner(cases, evidence_dir=out, base_url=base_url)
    except executor.ExecutorUnavailable as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3
    (out / executor.RESULT_FILE).write_text(
        json.dumps(results, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in results.items() if k != "cases"}, ensure_ascii=False))
    return 0 if results.get("all_pass") else 1


def cmd_upload(args, cfg) -> int:
    manifest = _upload_evidence(cfg, args.job, Path(args.dir).expanduser())
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


def cmd_show(args, cfg) -> int:
    print(json.dumps(call(cfg, "GET", f"/execution-jobs/{args.job}"), ensure_ascii=False, indent=2))
    return 0


# ── 入口 ───────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cameltv-node", description="CamelTv 本地执行节点（控制面不执行）")
    sub = parser.add_subparsers(dest="command", required=True)

    login = sub.add_parser("login", help="登录平台并保存会话（注册节点需要）")
    login.add_argument("--username", required=True)
    login.add_argument("--password", default=os.environ.get("CAMELTV_PASSWORD", ""))
    login.add_argument("--project-id", type=int, default=0)
    login.set_defaults(func=cmd_login)

    reg = sub.add_parser("register", help="注册/复用本地节点并签发节点令牌")
    reg.add_argument("--node-id", required=True)
    reg.add_argument("--project-id", type=int, default=0)
    reg.add_argument("--capabilities", nargs="*", default=["api", "web"])
    reg.set_defaults(func=cmd_register)

    doctor = sub.add_parser("doctor", help="平台连通性、凭据与节点状态自检")
    doctor.set_defaults(func=cmd_doctor)

    up = sub.add_parser("up", help="一条命令开工：注册+心跳+认领循环")
    up.add_argument("--node-id", default="")
    up.add_argument("--capabilities", nargs="*", default=["api", "web"])
    up.add_argument("--project-id", type=int, default=0)
    up.add_argument("--work-dir", default=str(Path.cwd() / "cameltv-node-evidence"))
    up.add_argument("--poll-seconds", type=float, default=5.0)
    up.add_argument("--heartbeat-seconds", type=float, default=DEFAULT_HEARTBEAT_SECONDS)
    up.add_argument("--once", action="store_true", help="只跑一轮（CI/自检用）")
    up.set_defaults(func=cmd_up)

    api = sub.add_parser("run-api", help="本地执行接口用例（httpx）")
    api.add_argument("--job", type=int, default=0)
    api.add_argument("--job-file", default="")
    api.add_argument("--out", default="./evidence")
    api.add_argument("--base-url", default="")
    api.set_defaults(func=cmd_run_api)

    web = sub.add_parser("run-web", help="本地执行 Web 用例（Playwright）")
    web.add_argument("--job", type=int, default=0)
    web.add_argument("--job-file", default="")
    web.add_argument("--out", default="./evidence")
    web.add_argument("--base-url", default="")
    web.set_defaults(func=cmd_run_web)

    upload = sub.add_parser("upload", help="上传证据目录（sha256 manifest 对账）")
    upload.add_argument("--job", type=int, required=True)
    upload.add_argument("--dir", required=True)
    upload.set_defaults(func=cmd_upload)

    show = sub.add_parser("show", help="查看任务详情")
    show.add_argument("--job", type=int, required=True)
    show.set_defaults(func=cmd_show)
    return parser


def cmd_up(args, cfg) -> int:
    """`up` 可自带 node-id/capabilities：缺身份时自动注册（一条命令开工）。"""
    if args.node_id:
        cfg["node_id"] = args.node_id
    if args.project_id:
        cfg["project_id"] = str(args.project_id)
    if not cfg.get("node_id"):
        print("ERROR: 未配置 node_id，请执行 register --node-id <名字> 或传 --node-id", file=sys.stderr)
        return 2
    if not cfg.get("token"):
        if not cfg.get("jwt"):
            print("ERROR: 未配置节点令牌，且无平台登录态可自动注册：请先 login", file=sys.stderr)
            return 2
        data = call(
            cfg,
            "POST",
            "/ai/agents/register",
            body={"agent_id": cfg["node_id"], "capabilities": args.capabilities},
            use_node_token=False,
        )
        cfg["token"] = data.get("token") or ""
        save_config(cfg)
        print(f"[init] 已注册节点 {cfg['node_id']} 并保存令牌到 {CONFIG_PATH}")
    return _loop(cfg, args)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = load_config()
    if args.command not in ("login", "register", "up") and not cfg.get("node_id"):
        print("ERROR: 未配置 node_id，请先执行 register", file=sys.stderr)
        return 2
    try:
        return args.func(args, cfg)
    except TransportDown as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\n[stop] 已停止心跳；任务将因租约过期回到 pending，可重新认领", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
