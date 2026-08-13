"""Batch 170 — 刷新体育生产站点 Playwright storageState。

凭据只从环境变量读取（不入库/不入仓）：
  SPORTS_PROD_MOBILE      手机号，如 18476944071
  SPORTS_PROD_PASSWORD    密码
  SPORTS_PROD_COUNTRY     国家码，默认 86
  SPORTS_PROD_STATE_PATH  输出路径，默认 config/runtime/sports-prod-storage-state.json

登录接口（用户确认，无需短信验证码）：
  POST https://api.cameltv.live/account-service/ee/client/demo/login
  表单：countryCode=86&mobile=...&password=...

输出 Playwright storageState JSON：为 .camel1.tv 写入 auth cookie
（{"userId","userSig","token"}），可直接填入平台 UI 环境的
UI_STORAGE_STATE_JSON 变量。
"""
from __future__ import annotations

import json
import os
import sys

import httpx

BASE_URL = "https://api.cameltv.live"
LOGIN_URL = f"{BASE_URL}/account-service/ee/client/demo/login"


def main() -> int:
    mobile = (os.environ.get("SPORTS_PROD_MOBILE") or "").strip()
    password = (os.environ.get("SPORTS_PROD_PASSWORD") or "").strip()
    if not mobile or not password:
        print("缺少 SPORTS_PROD_MOBILE / SPORTS_PROD_PASSWORD 环境变量", file=sys.stderr)
        return 2
    country = (os.environ.get("SPORTS_PROD_COUNTRY") or "86").strip()

    resp = httpx.post(
        LOGIN_URL,
        data={"countryCode": country, "mobile": mobile, "password": password},
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"登录失败 HTTP {resp.status_code}: {resp.text[:300]}", file=sys.stderr)
        return 1
    payload = resp.json()
    data = payload.get("data") or {}
    if payload.get("status") not in (200, None) or not data.get("token"):
        print(f"登录业务失败: {json.dumps(payload, ensure_ascii=False)[:300]}", file=sys.stderr)
        return 1

    auth_cookie = json.dumps({
        "userId": str(data.get("userId") or ""),
        "userSig": str(data.get("userSig") or ""),
        "token": str(data.get("token") or ""),
    }, ensure_ascii=False)

    storage_state = {
        "cookies": [
            {
                "name": "auth",
                "value": auth_cookie,
                "domain": ".camel1.tv",
                "path": "/",
                "expires": -1,
                "httpOnly": False,
                "secure": True,
                "sameSite": "Lax",
            },
        ],
        "origins": [],
    }

    out_path = os.environ.get(
        "SPORTS_PROD_STATE_PATH",
        "config/runtime/sports-prod-storage-state.json",
    )
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(storage_state, fh, ensure_ascii=False, indent=2)
    print(f"storageState 已写入 {out_path}（nickname={data.get('nickname')}, userId={data.get('userId')}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
