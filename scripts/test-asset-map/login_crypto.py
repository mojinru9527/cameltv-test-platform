#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""加密登录支持（RuoYi-Plus 风格：RSA 保护 AES 密钥 + AES-ECB 加密请求体）。

背景
----
该项目后台 `/auth/login` 的请求体不是明文 JSON，而是：
1. 前端随机生成 32 位字母数字串作为 AES 密钥；
2. 用内置 RSA 公钥加密 `base64(aesKey)`，放入请求头 `encrypt-key`；
3. 用该 AES 密钥（AES-256-ECB / PKCS7）加密 `JSON.stringify(payload)`，作为请求体；
4. 附带头 `isencrypt: true`。
明文 JSON 直接提交会被服务端拒绝（实测返回 403「没有访问权限」）。

RSA 公钥来自构建期 `VITE_APP_RSA_PUBLIC_KEY`，会被内联进线上 bundle；
本模块从 index.html → 主 bundle 自动提取（也支持用环境变量覆盖）。

对外只暴露 `encrypted_login()`，供 `refresh_env.py` 的「方式 B」使用。
"""
from __future__ import annotations

import base64
import json
import random
import re
import string

ALPHABET = string.ascii_letters + string.digits  # 与前端 generateRandomString 一致


# --------------------------------------------------------------------- 编解码
def b64e(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def gen_aes_key() -> bytes:
    """32 位字母数字串（AES-256 密钥）。"""
    return "".join(random.choice(ALPHABET) for _ in range(32)).encode("utf-8")


def aes_encrypt(plaintext: str, key: bytes) -> str:
    """AES-256-ECB + PKCS7，返回 base64。"""
    from cryptography.hazmat.primitives import padding as sym_padding
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    padder = sym_padding.PKCS7(128).padder()
    data = padder.update(plaintext.encode("utf-8")) + padder.finalize()
    enc = Cipher(algorithms.AES(key), modes.ECB()).encryptor()
    return b64e(enc.update(data) + enc.finalize())


def rsa_encrypt(plaintext: bytes, public_key) -> str:
    """RSA PKCS1v15 加密，返回 base64（与 JSEncrypt.encrypt 输出一致）。"""
    from cryptography.hazmat.primitives.asymmetric import padding

    return b64e(public_key.encrypt(plaintext, padding.PKCS1v15()))


# --------------------------------------------------------------------- 公钥发现
def parse_public_key(text: str):
    """接受 PEM 或裸 base64，返回 RSA 公钥对象。"""
    from cryptography.hazmat.primitives import serialization

    t = text.strip()
    if "BEGIN" not in t:
        body = re.sub(r"\s+", "", t)
        t = ("-----BEGIN PUBLIC KEY-----\n"
             + "\n".join(body[i:i + 64] for i in range(0, len(body), 64))
             + "\n-----END PUBLIC KEY-----\n")
    return serialization.load_pem_public_key(t.encode("utf-8"))


PK_B64_RE = re.compile(r'["\'](MFww[A-Za-z0-9+/=]{80,300})["\']')


def discover_public_key(base_url: str, *, timeout: int = 60, explicit: str = "") -> tuple[object, str]:
    """返回 (公钥对象, 来源说明)。优先显式传入，其次抓页面 bundle。"""
    if explicit:
        return parse_public_key(explicit), "env/explicit"

    import requests
    import urllib3
    urllib3.disable_warnings()

    origin = re.sub(r"/[^/]+/?$", "", base_url.rstrip("/")) if "/prod-api" in base_url else base_url.rstrip("/")
    html = requests.get(origin + "/", timeout=timeout, verify=False).text
    bundles = re.findall(r'assets/(index-[0-9a-zA-Z]+\.js)', html)
    for b in bundles[:3]:
        js = requests.get(f"{origin}/assets/{b}", timeout=timeout, verify=False).text
        m = PK_B64_RE.search(js)
        if m:
            return parse_public_key(m.group(1)), f"bundle:{b}"
        m2 = re.search(r"-----BEGIN PUBLIC KEY-----.{0,900}?-----END PUBLIC KEY-----", js, re.S)
        if m2:
            return parse_public_key(m2.group(0)), f"bundle:{b}:pem"
    raise RuntimeError("未能在前端 bundle 中找到 RSA 公钥；请通过 ASSET_MAP_RSA_PUBLIC_KEY 显式提供")


# --------------------------------------------------------------------- 登录
def encrypted_login(base_url: str, username: str, password: str, clientid: str,
                    captcha: str, uuid: str, public_key_text: str = "", *,
                    timeout: int = 30) -> str:
    """执行加密登录并返回 admin token。"""
    import requests
    import urllib3
    urllib3.disable_warnings()

    pub, source = discover_public_key(base_url, explicit=public_key_text)
    aes_key = gen_aes_key()
    payload = {
        "username": username,
        "password": password,
        "code": str(captcha),
        "uuid": uuid,
        "clientId": clientid,
        "grantType": "password",
    }
    body = aes_encrypt(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), aes_key)
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "Accept": "application/json, text/plain, */*",
        "clientid": clientid,
        "isencrypt": "true",
        "encrypt-key": rsa_encrypt(b64e(aes_key).encode("ascii"), pub),
    }
    r = requests.post(base_url.rstrip("/") + "/auth/login", data=json.dumps(body),
                      headers=headers, timeout=timeout, verify=False)
    try:
        j = r.json()
    except Exception:
        raise RuntimeError(f"登录响应非 JSON（HTTP {r.status_code}）: {r.text[:160]}")
    data = j.get("data")
    token = data if isinstance(data, str) else (data or {}).get("access_token") if isinstance(data, dict) else None
    if not token:
        raise RuntimeError(f"登录失败（公钥来源 {source}）: code={j.get('code')} msg={j.get('msg')}")
    return token
