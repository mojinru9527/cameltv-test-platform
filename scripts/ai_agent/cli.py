"""CamelTv 本地 AI Agent CLI（Batch 248）。

平台不做任何 LLM 推理：本 CLI 在**本地**（例如 ChatGPT 桌面客户端的会话里）
认领平台的 AiJob，把任务输入交给本地模型产出结果，再把结果回传平台。

用法（A 模式：手动/客户端驱动，模型可随时切换）：
    python scripts/ai_agent/cli.py login --username <平台账号>     # 平台 JWT（注册/查询/导入用）
    python scripts/ai_agent/cli.py register --agent-id my-local-agent
    python scripts/ai_agent/cli.py doctor
    python scripts/ai_agent/cli.py next --out job.json      # 认领任务并打印输入
    python scripts/ai_agent/cli.py report --job 12 --file result.json --model chatgpt-5
    python scripts/ai_agent/cli.py import --job 12

配置（环境变量或 ~/.cameltv-ai-agent.json）：
    CAMELTV_BASE_URL     平台地址，默认 https://swiftbugs.cn
    CAMELTV_AGENT_TOKEN  register 返回的 agent token（仅返回一次）
    CAMELTV_AGENT_ID     agent 名称
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import httpx

CONFIG_PATH = Path.home() / ".cameltv-ai-agent.json"
DEFAULT_BASE = "https://swiftbugs.cn"


def load_config() -> dict:
    cfg = {"base_url": os.environ.get("CAMELTV_BASE_URL", DEFAULT_BASE),
           "agent_id": os.environ.get("CAMELTV_AGENT_ID", ""),
           "token": os.environ.get("CAMELTV_AGENT_TOKEN", ""),
           "jwt": os.environ.get("CAMELTV_JWT", ""),
           "project_id": os.environ.get("CAMELTV_PROJECT_ID", "")}
    if CONFIG_PATH.exists():
        try:
            cfg.update({k: v for k, v in json.loads(CONFIG_PATH.read_text(encoding="utf-8")).items() if v})
        except (json.JSONDecodeError, OSError):
            pass
    return cfg


def save_config(cfg: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def call(cfg: dict, method: str, path: str, *, body=None, token: str | None = None, use_agent_token=True):
    headers = {"Content-Type": "application/json"}
    if cfg.get("project_id"):
        headers["X-Project-Id"] = str(cfg["project_id"])
    if use_agent_token and token:
        headers["X-AI-Agent-Token"] = token
    if cfg.get("jwt"):
        headers["Authorization"] = f"Bearer {cfg['jwt']}"
    url = cfg["base_url"].rstrip("/") + "/api/v1" + path
    resp = httpx.request(method, url, headers=headers, json=body, timeout=300)
    try:
        payload = resp.json()
    except ValueError:
        payload = {"code": resp.status_code, "msg": resp.text[:300]}
    if resp.status_code >= 400 or payload.get("code") not in (None, 0):
        print(f"ERROR {method} {path} -> HTTP {resp.status_code} code={payload.get('code')} "
              f"msg={payload.get('msg') or payload.get('detail')}", file=sys.stderr)
        raise SystemExit(2)
    return payload.get("data", payload)


def cmd_login(args, cfg) -> int:
    """登录平台并保存会话 JWT（register / health / import 需要平台登录态）。"""
    password = args.password or os.environ.get("CAMELTV_PASSWORD", "")
    if not password:
        import getpass

        password = getpass.getpass("请输入平台密码: ")
    url = cfg["base_url"].rstrip("/") + "/api/v1/auth/login"
    resp = httpx.post(url, json={"username": args.username, "password": password}, timeout=60)
    try:
        payload = resp.json()
    except ValueError:
        print(f"ERROR: 登录响应无法解析 (HTTP {resp.status_code})", file=sys.stderr)
        return 2
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
    print(json.dumps({"ok": True, "username": args.username, "project_id": cfg.get("project_id"),
                      "saved_to": str(CONFIG_PATH)}, ensure_ascii=False))
    return 0


def cmd_register(args, cfg) -> int:
    if not cfg.get("jwt"):
        print("ERROR: 缺少平台登录态，请先执行 login --username <账号>", file=sys.stderr)
        return 2
    body = {"agent_id": args.agent_id, "capabilities": args.capabilities}
    data = call(cfg, "POST", "/ai/agents/register", body=body, use_agent_token=False)
    cfg["agent_id"] = data["agent_id"]
    cfg["token"] = data.get("token") or cfg.get("token", "")
    if args.project_id:
        cfg["project_id"] = str(args.project_id)
    save_config(cfg)
    print(json.dumps({"agent_id": cfg["agent_id"], "project_scope": data.get("project_scope"),
                      "token_saved_to": str(CONFIG_PATH),
                      "notice": data.get("token_notice")}, ensure_ascii=False, indent=2))
    return 0


def cmd_doctor(args, cfg) -> int:
    report = {"base_url": cfg["base_url"], "agent_id": cfg.get("agent_id"), "project_id": cfg.get("project_id"),
              "token_configured": bool(cfg.get("token")), "jwt_configured": bool(cfg.get("jwt"))}
    if not cfg.get("jwt"):
        report["ok"] = False
        report["error"] = "缺少平台登录态：请先执行 login --username <账号>"
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 2
    try:
        health = call(cfg, "GET", "/ai/agents/health")
        report["agent_health"] = health
        report["ok"] = True
    except SystemExit as exc:
        report["ok"] = False
        report["error"] = f"exit {exc.code}"
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("ok") else 2


def cmd_next(args, cfg) -> int:
    body = {"agent_id": cfg["agent_id"], "capabilities": args.capabilities}
    data = call(cfg, "POST", "/ai/jobs/claim", body=body, token=cfg.get("token"))
    job = data.get("job")
    if not job:
        print(json.dumps({"claimed": False, "message": "当前没有待处理的 AI 任务"}, ensure_ascii=False))
        return 0
    if args.out:
        Path(args.out).write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"claimed": True, "job_id": job["id"], "saved_to": args.out}, ensure_ascii=False))
    else:
        print(json.dumps(job, ensure_ascii=False, indent=2))
    return 0


def cmd_show(args, cfg) -> int:
    print(json.dumps(call(cfg, "GET", f"/ai/jobs/{args.job}"), ensure_ascii=False, indent=2))
    return 0


def cmd_report(args, cfg) -> int:
    result = json.loads(Path(args.file).read_text(encoding="utf-8")) if args.file else {}
    body = {
        "agent_id": cfg["agent_id"],
        "status": args.status,
        "summary": args.summary or "",
        "result": result,
        "evidence_refs": args.evidence or [],
        "model_name": args.model or "",
        "error_message": args.error or "",
    }
    data = call(cfg, "POST", f"/ai/jobs/{args.job}/report", body=body, token=cfg.get("token"))
    print(json.dumps({"job_id": data.get("id"), "status": data.get("status"), "model_name": data.get("model_name")},
                     ensure_ascii=False))
    return 0


def cmd_import(args, cfg) -> int:
    body = {"indices": args.indices} if args.indices else {}
    data = call(cfg, "POST", f"/ai/jobs/{args.job}/import", body=body)
    print(json.dumps(data, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="camel-ai-agent", description="CamelTv 本地 AI Agent（平台零推理）")
    sub = parser.add_subparsers(dest="command", required=True)

    login = sub.add_parser("login", help="登录平台并保存会话（注册/查询/导入需要）")
    login.add_argument("--username", required=True)
    login.add_argument("--password", default=os.environ.get("CAMELTV_PASSWORD", ""))
    login.add_argument("--project-id", type=int, default=0)
    login.set_defaults(func=cmd_login)

    reg = sub.add_parser("register", help="注册本地 Agent 并签发 token")
    reg.add_argument("--agent-id", required=True)
    reg.add_argument("--project-id", type=int, default=0)
    reg.add_argument("--capabilities", nargs="*", default=["extract", "generate"])
    reg.set_defaults(func=cmd_register)

    doc = sub.add_parser("doctor", help="平台连通性与自身配置自检")
    doc.set_defaults(func=cmd_doctor)

    nxt = sub.add_parser("next", help="认领一个待处理 AI 任务")
    nxt.add_argument("--out", default="")
    nxt.add_argument("--capabilities", nargs="*", default=["extract", "generate"])
    nxt.set_defaults(func=cmd_next)

    show = sub.add_parser("show", help="查看任务详情与结果")
    show.add_argument("--job", type=int, required=True)
    show.set_defaults(func=cmd_show)

    rep = sub.add_parser("report", help="回传任务结果")
    rep.add_argument("--job", type=int, required=True)
    rep.add_argument("--file", default="")
    rep.add_argument("--status", default="completed", choices=["completed", "failed", "cancelled"])
    rep.add_argument("--summary", default="")
    rep.add_argument("--model", default="")
    rep.add_argument("--error", default="")
    rep.add_argument("--evidence", nargs="*", default=[])
    rep.set_defaults(func=cmd_report)

    imp = sub.add_parser("import", help="把已完成任务的结果导入用例库")
    imp.add_argument("--job", type=int, required=True)
    imp.add_argument("--indices", nargs="*", type=int, default=[])
    imp.set_defaults(func=cmd_import)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = load_config()
    if args.command not in ("register", "login") and not cfg.get("agent_id"):
        print("ERROR: 未配置 agent_id，请先执行 register", file=sys.stderr)
        return 2
    return args.func(args, cfg)


if __name__ == "__main__":
    raise SystemExit(main())
