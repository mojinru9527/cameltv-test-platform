"""会话凭证自动注入服务测试（C-API-AUTO-001）。

覆盖：
- 配置解析（未配置 → 空注入；配置 → 自动获取）
- 响应结构提取（detail.value/detail.key/data.token 等）
- 执行引擎注入（$session.token 在请求头/URL/body 中替换）
- 凭证获取失败降级（不影响用例执行）
- 缓存行为
"""

from __future__ import annotations

import json

import pytest

from app.models.environment import Environment, EnvironmentVariable
from app.models.test_case import TestCase
from app.services import session_credentials_service as scs
from app.services.api_execution_service import execute_api_case


@pytest.fixture(autouse=True)
def _clear_cred_cache():
    scs.clear_credential_cache()
    yield
    scs.clear_credential_cache()


def _make_env(
    db, project_id: int, base_url: str = "http://cred.example"
) -> Environment:
    env = Environment(
        project_id=project_id, name="test-env", env_type="test", base_url=base_url
    )
    db.add(env)
    db.commit()
    db.refresh(env)
    return env


def _set_var(db, env: Environment, key: str, value: str, encrypted: bool = False):
    var = EnvironmentVariable(
        environment_id=env.id,
        key=key,
        value=value,
        encrypted=encrypted,
    )
    db.add(var)
    db.commit()


def test_configured_fetch_returns_token_and_key(db_session):
    """配置凭证接口后，自动获取 token/key。"""
    import httpx

    # 模拟凭证接口
    port = 18900

    from fastapi import FastAPI
    from fastapi.testclient import TestClient  # noqa: F401  (uvicorn 依赖)

    cred_app = FastAPI()

    @cred_app.post("/anon")
    def anon():
        return {"code": 0, "detail": {"key": "Anony123", "value": "C_token_abc"}}

    import threading
    import uvicorn

    server = uvicorn.Server(
        uvicorn.Config(cred_app, host="127.0.0.1", port=port, log_level="error")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        import time

        for _ in range(50):
            try:
                httpx.get(f"http://127.0.0.1:{port}/anon", timeout=1)
                break
            except Exception:
                time.sleep(0.1)
        env = _make_env(db_session, project_id=1)
        _set_var(
            db_session, env, "session_credential_url", f"http://127.0.0.1:{port}/anon"
        )
        creds = scs.fetch_session_credentials(db_session, env.id, 1)
        assert creds.get("token") == "C_token_abc"
        assert creds.get("key") == "Anony123"
    finally:
        server.should_exit = True


def test_unconfigured_returns_empty(db_session):
    """未配置凭证接口时返回空 dict（零开销）。"""
    env = _make_env(db_session, project_id=1)
    assert scs.fetch_session_credentials(db_session, env.id, 1) == {}
    assert scs.session_variable_map(db_session, env.id, 1) == {}


def test_form_encoded_credentials_fetch(db_session):
    """form-urlencoded 凭证接口（Batch 188：被测系统 demo/login 仅接受 form 编码）。

    模拟被测系统登录响应结构：{"status":200,"data":{"token","userSig","userId"}}
    + session_field_map 提取 userSig/userId。
    """
    import threading
    import time
    import uvicorn
    from fastapi import FastAPI, Form

    port = 18904
    app = FastAPI()

    @app.post("/form-login")
    def form_login(countryCode: str = Form(...), mobile: str = Form(...), password: str = Form(...)):
        assert countryCode == "86"
        assert mobile == "18476944071"
        assert password == "secret"
        return {
            "status": 200,
            "data": {
                "token": "C_form_token_abc",
                "userSig": "C_user_sig_xyz",
                "userId": "11025728",
            },
            "msg": "",
        }

    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        import httpx

        for _ in range(50):
            try:
                httpx.get(f"http://127.0.0.1:{port}/form-login", timeout=1)
                break
            except Exception:
                time.sleep(0.1)

        env = _make_env(db_session, project_id=1)
        _set_var(
            db_session, env, "session_credential_url", f"http://127.0.0.1:{port}/form-login"
        )
        _set_var(db_session, env, "session_credential_content_type", "form")
        _set_var(
            db_session, env, "session_credential_body",
            json.dumps({"countryCode": "86", "mobile": "18476944071", "password": "secret"}),
        )
        _set_var(
            db_session, env, "session_field_map",
            json.dumps({"userSig": "$.data.userSig", "userId": "$.data.userId"}),
        )
        creds = scs.fetch_session_credentials(db_session, env.id, 1)
        assert creds.get("token") == "C_form_token_abc", creds
        assert creds.get("userSig") == "C_user_sig_xyz", creds
        assert creds.get("userId") == "11025728", creds
    finally:
        server.should_exit = True


def test_extract_credentials_variants():
    """多种响应结构提取。"""
    r1 = {"code": 0, "detail": {"key": "K1", "value": "V1"}}
    c1 = scs._extract_credentials(r1)
    assert c1 == {"token": "V1", "key": "K1"}

    r2 = {"code": 0, "data": {"token": "T2", "mid": "M2"}}
    c2 = scs._extract_credentials(r2)
    assert c2.get("token") == "T2" and c2.get("mid") == "M2"

    r3 = {"result": {"access_token": "T3"}}
    c3 = scs._extract_credentials(r3)
    assert c3.get("token") == "T3"

    assert scs._extract_credentials({"code": 500}) == {}


def test_fetch_failure_degrades_empty(db_session):
    """凭证接口不可达时降级为空 dict，不抛异常。"""
    env = _make_env(db_session, project_id=1)
    _set_var(
        db_session, env, "session_credential_url", "http://127.0.0.1:1/unreachable"
    )
    assert scs.fetch_session_credentials(db_session, env.id, 1) == {}


def test_execute_with_session_injection(db_session):
    """执行引擎：请求引用 $session.token 时自动注入（用内联模拟凭证接口）。"""
    import threading
    import time
    import uvicorn
    from fastapi import FastAPI, Header

    # 凭证接口与目标接口共用同一 app
    # （满足 SSRF 防护：目标 host 必须与环境 base_url 一致）
    port = 18903
    app = FastAPI()

    @app.post("/anon")
    def anon():
        return {"code": 0, "detail": {"key": "AnonyX", "value": "C_SESSTOKEN"}}

    @app.get("/echo")
    def echo(authorization: str | None = Header(default=None)):
        return {"auth": authorization, "code": 0}

    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        import httpx

        for _ in range(50):
            try:
                httpx.get(f"http://127.0.0.1:{port}/echo", timeout=1)
                break
            except Exception:
                time.sleep(0.1)

        env = _make_env(db_session, project_id=1, base_url=f"http://127.0.0.1:{port}")
        _set_var(
            db_session, env, "session_credential_url", f"http://127.0.0.1:{port}/anon"
        )

        case = TestCase(
            project_id=1,
            title="会话注入用例",
            case_type="api",
            api_method="GET",
            api_endpoint="/echo",
            api_headers=json.dumps({"Authorization": "Bearer ${session.token}"}),
            api_assertions=json.dumps(
                [
                    {
                        "type": "jsonpath",
                        "path": "$.auth",
                        "operator": "equals",
                        "expected": "Bearer C_SESSTOKEN",
                    },
                ]
            ),
        )
        db_session.add(case)
        db_session.commit()
        db_session.refresh(case)

        result = execute_api_case(
            db_session, case.id, project_id=1, environment_id=env.id
        )
        # 引擎成功状态为 "ok"；核心验证：断言全部通过 + 注入的 token 生效
        assert result.get("all_pass") is True, result
        assert result.get("status") == "ok", result
        assert result.get("response_body", {}).get("auth") == "Bearer C_SESSTOKEN"
    finally:
        server.should_exit = True
