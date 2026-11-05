#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 / 校验测试资产底图 live CI 所需的 env.json。

两种模式：
1. 静态凭据（最简单）：直接给出 admin_token / client_token，脚本只做校验与落盘。
   适合令牌有效期内的临时运行。
2. 自动刷新（推荐）：给管理员账号口令 + Redis 地址，脚本自己走「验证码 → 登录」拿 admin token，
   并从 Redis 取 C 端 token后写 env.json。适合 self-hosted runner 定时/手动运行。

用法：
    # 校验既有文件
    python scripts/test-asset-map/refresh_env.py --check runtime/env.json

    # 从环境变量组装（CI 推荐）
    ASSET_MAP_BASE_URL=... ADMIN_USER=... ADMIN_PASSWORD=...
    ASSET_MAP_CLIENT_PHONE=... REDIS_HOST=... REDIS_PORT=... REDIS_PASSWORD=... REDIS_DB=5 \
      python scripts/test-asset-map/refresh_env.py --out runtime/env.json

    # 直接用现成 token
    python scripts/test-asset-map/refresh_env.py --out runtime/env.json \
      --admin-token <jwt> --client-token <token> --base-url https://example.com/prod-api

退出码：0 成功；2 校验失败；3 依赖缺失/取 token 失败。
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import time
from pathlib import Path

REQUIRED = ("base_url", "admin_token", "client_token")
OPTIONAL_DEFAULTS = {"clientid": "", "timeout": 60}


# ----------------------------------------------------------------- 校验
def validate_env(env: dict) -> list[str]:
    """返回问题列表；空列表表示通过。纯函数，便于单测。"""
    errs: list[str] = []
    if not isinstance(env, dict):
        return ["env 必须是 JSON 对象"]
    for k in REQUIRED:
        v = env.get(k)
        if not isinstance(v, str) or not v.strip():
            errs.append(f"缺少或为空: {k}")
    base = (env.get("base_url") or "").strip()
    if base:
        if not base.startswith(("http://", "https://")):
            errs.append("base_url 必须以 http(s):// 开头")
        if base.endswith("/"):
            errs.append("base_url 不应以 / 结尾（脚本会自行拼接路径）")
        if base.startswith("http://") and "localhost" not in base and "127.0.0.1" not in base:
            errs.append("base_url 使用明文 http（非本地地址），请改用 https")
    admin = (env.get("admin_token") or "").strip()
    if admin and admin.count(".") != 2 and len(admin) < 20:
        errs.append("admin_token 不像 JWT 也不像长随机串，请确认是否粘贴完整")
    client = (env.get("client_token") or "").strip()
    if client and len(client) < 8:
        errs.append("client_token 过短，疑似粘贴不完整")
    if env.get("clientid") is not None and not isinstance(env["clientid"], str):
        errs.append("clientid 必须是字符串")
    return errs


def write_env(env: dict, out: Path, chmod: bool = True) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(env, ensure_ascii=False, indent=1), encoding="utf-8")
    if chmod and os.name != "nt":
        try:
            os.chmod(out, 0o600)
        except OSError:
            pass


# ----------------------------------------------------------------- Redis
def redis_get(key: str, host: str, port: int, password: str, db: int, timeout: float = 10.0):
    """最小 RESP 客户端（避免引入 redis 依赖）。返回 str/None。"""
    s = socket.create_connection((host, port), timeout=timeout)
    f = s.makefile("rb")

    def send(*args):
        out = [("*%d\r\n" % len(args)).encode()]
        for a in args:
            b = a if isinstance(a, bytes) else str(a).encode()
            out += [("$%d\r\n" % len(b)).encode(), b, b"\r\n"]
        s.sendall(b"".join(out))

    def reply():
        line = f.readline().rstrip(b"\r\n")
        t, rest = line[:1], line[1:]
        if t == b"$":
            n = int(rest)
            if n == -1:
                return None
            data = f.read(n)
            f.read(2)
            return data
        if t == b"*":
            n = int(rest)
            return None if n == -1 else [reply() for _ in range(n)]
        if t == b"-":
            raise RuntimeError("redis error: " + rest.decode("utf-8", "replace"))
        return rest

    try:
        if password:
            send("AUTH", password)
            reply()
        send("SELECT", db)
        reply()
        send("GET", key)
        return reply()
    finally:
        s.close()


def fetch_client_token(phone: str, host: str, port: int, password: str, db: int) -> str:
    """按手机号在 Redis 里找到 openid，再取该 openid 的 token。"""
    keys = redis_get("KEYS", host, port, password, db) or []
    for k in keys:
        kb = k.decode() if isinstance(k, bytes) else str(k)
        if not kb.startswith("USER_TOKEN_KEY:"):
            continue
        raw = redis_get(kb, host, port, password, db)
        if not raw:
            continue
        try:
            meta = json.loads(raw)
            if isinstance(meta, str):
                meta = json.loads(meta)
        except Exception:
            continue
        if str(meta.get("phoneNumber")) != str(phone):
            continue
        openid = meta.get("openid")
        if not openid:
            continue
        tok = redis_get("USER_OPENID_TOKEN_KEY:" + openid, host, port, password, db)
        if tok:
            return (tok.decode() if isinstance(tok, bytes) else str(tok)).strip('"')
    return ""


# ----------------------------------------------------------------- 登录
def login_admin(base_url: str, username: str, password: str, clientid: str,
                redis_host: str, redis_port: int, redis_pwd: str, redis_db: int) -> str:
    """走「取验证码 → Redis 读答案 → 登录」拿 admin token。"""
    import requests
    import urllib3
    urllib3.disable_warnings()

    sess = requests.Session()
    r = sess.get(base_url.rstrip("/") + "/auth/code", timeout=30, verify=False)
    j = r.json()
    data = j.get("data") or {}
    uuid = data.get("uuid") if isinstance(data, dict) else None
    if not uuid:
        raise RuntimeError(f"取验证码失败: {json.dumps(j, ensure_ascii=False)[:200]}")
    ans = redis_get("global:captcha_codes:" + uuid, redis_host, redis_port, redis_pwd, redis_db)
    if isinstance(ans, bytes):
        ans = ans.decode()
    if not ans:
        raise RuntimeError("Redis 中未找到验证码答案（检查 REDIS_DB / 前缀 global:captcha_codes）")
    payload = {"username": username, "password": password, "code": str(ans).strip('"'),
               "uuid": uuid, "clientId": clientid, "grantType": "password"}
    r = sess.post(base_url.rstrip("/") + "/auth/login", json=payload, timeout=30, verify=False)
    j = r.json()
    tok = j.get("data") if isinstance(j.get("data"), str) else None
    if not tok:
        raise RuntimeError(f"登录失败: code={j.get('code')} msg={j.get('msg')}")
    return tok


# ----------------------------------------------------------------- CLI
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="runtime/env.json")
    ap.add_argument("--check", metavar="FILE", default="")
    ap.add_argument("--base-url", default=os.getenv("ASSET_MAP_BASE_URL", ""))
    ap.add_argument("--admin-token", default=os.getenv("ADMIN_TOKEN", ""))
    ap.add_argument("--client-token", default=os.getenv("CLIENT_TOKEN", ""))
    ap.add_argument("--clientid", default=os.getenv("ASSET_MAP_CLIENTID", ""))
    ap.add_argument("--admin-user", default=os.getenv("ADMIN_USER", ""))
    ap.add_argument("--admin-password", default=os.getenv("ADMIN_PASSWORD", ""))
    ap.add_argument("--client-phone", default=os.getenv("ASSET_MAP_CLIENT_PHONE", ""))
    ap.add_argument("--redis-host", default=os.getenv("REDIS_HOST", ""))
    ap.add_argument("--redis-port", type=int, default=int(os.getenv("REDIS_PORT", "6379")))
    ap.add_argument("--redis-password", default=os.getenv("REDIS_PASSWORD", ""))
    ap.add_argument("--redis-db", type=int, default=int(os.getenv("REDIS_DB", "5")))
    args = ap.parse_args()

    if args.check:
        p = Path(args.check)
        if not p.exists():
            print(f"FAIL: 文件不存在 {p}")
            return 2
        env = json.loads(p.read_text(encoding="utf-8"))
        errs = validate_env(env)
        if errs:
            print("FAIL:\n  - " + "\n  - ".join(errs))
            return 2
        print(f"OK: {p} 校验通过（base_url={env['base_url']}，admin_token={len(env['admin_token'])} 字符）")
        return 0

    env = {"base_url": args.base_url.rstrip("/"), "admin_token": args.admin_token,
           "client_token": args.client_token, "clientid": args.clientid}
    if not env["admin_token"]:
        if not (args.admin_user and args.admin_password and args.redis_host):
            print("需要 ADMIN_TOKEN，或提供 ADMIN_USER/ADMIN_PASSWORD/REDIS_HOST 走自动登录", file=sys.stderr)
            return 3
        try:
            t0 = time.time()
            env["admin_token"] = login_admin(env["base_url"], args.admin_user, args.admin_password,
                                             env["clientid"], args.redis_host, args.redis_port,
                                             args.redis_password, args.redis_db)
            print(f"admin token 获取成功（{int(time.time()-t0)}s）")
        except Exception as e:
            print(f"admin token 获取失败: {e}", file=sys.stderr)
            return 3
    if not env["client_token"]:
        if not (args.client_phone and args.redis_host):
            print("需要 CLIENT_TOKEN，或提供 ASSET_MAP_CLIENT_PHONE/REDIS_HOST 从 Redis 读取", file=sys.stderr)
            return 3
        try:
            env["client_token"] = fetch_client_token(args.client_phone, args.redis_host,
                                                     args.redis_port, args.redis_password, args.redis_db)
        except Exception as e:
            print(f"client token 获取失败: {e}", file=sys.stderr)
            return 3
        if not env["client_token"]:
            print("Redis 中未找到该手机号的 C 端 token（检查测试号是否登录过）", file=sys.stderr)
            return 3

    errs = validate_env(env)
    if errs:
        print("FAIL:\n  - " + "\n  - ".join(errs), file=sys.stderr)
        return 2
    write_env(env, Path(args.out))
    print(f"OK: 已写入 {args.out}（base_url={env['base_url']}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
