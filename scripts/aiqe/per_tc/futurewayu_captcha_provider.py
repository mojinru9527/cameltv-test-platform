"""未来娃屿登录验证码 Provider（本地回环，供 AIQE Playwright fill_http 使用）。

从生产 Redis 读取最近的图形验证码答案；只监听 127.0.0.1，不对外暴露。

环境变量：
  FUTUREWAYU_REDIS_HOST / PORT / PASSWORD / DB / KEY_PREFIX
"""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import redis

REDIS = redis.Redis(
    host=os.environ.get("FUTUREWAYU_REDIS_HOST", "43.136.119.131"),
    port=int(os.environ.get("FUTUREWAYU_REDIS_PORT", "6377")),
    password=os.environ.get("FUTUREWAYU_REDIS_PASSWORD", ""),
    db=int(os.environ.get("FUTUREWAYU_REDIS_DB", "5")),
    socket_connect_timeout=5,
    socket_timeout=5,
    decode_responses=True,
)
PREFIX = os.environ.get("FUTUREWAYU_CAPTCHA_PREFIX", "global:captcha_codes:")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        return

    def do_GET(self):
        code = ""
        try:
            keys = list(REDIS.scan_iter(match=PREFIX + "*", count=50))
            if keys:
                key = keys[-1]
                code = str(REDIS.get(key) or "").strip().strip('"')
        except Exception as exc:  # noqa: BLE001
            body = json.dumps({"error": type(exc).__name__}).encode()
            self.send_response(503)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if not code:
            body = json.dumps({"error": "captcha_not_found"}).encode()
            self.send_response(404)
        else:
            body = json.dumps({"code": code}).encode()
            self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    port = int(os.environ.get("FUTUREWAYU_CAPTCHA_PORT", "18081"))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"captcha provider on 127.0.0.1:{port}", flush=True)
    server.serve_forever()
