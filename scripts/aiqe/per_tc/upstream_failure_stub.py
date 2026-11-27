"""TC-AIQE-006：本地模拟上游 504/超时（仅开发/验收使用，不连接生产上游）。"""
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        return

    def do_GET(self):
        if self.path.startswith("/health"):
            body = json.dumps({"status": "ok"}).encode()
            self.send_response(200)
        elif self.path.startswith("/upstream-fail"):
            body = json.dumps({"code": 504, "msg": "upstream timeout (simulated)"}).encode()
            self.send_response(504)
        elif self.path.startswith("/upstream-timeout"):
            # 返回 200 但延迟 15s，用于超时场景
            import time

            time.sleep(15)
            body = json.dumps({"code": 200, "msg": "late"}).encode()
            self.send_response(200)
        else:
            body = json.dumps({"code": 404}).encode()
            self.send_response(404)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5210)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"upstream stub on 127.0.0.1:{args.port}", flush=True)
    server.serve_forever()
