"""WWY-V5-006「记住账号」单用例点击复核（不是 TC-AIQE-008 产品级 PASS）。

V1.6.2 FIX-008 事实边界
-----------------------
- 本脚本只复测 ``WWY-V5-006``（``TC-ADM-01-D`` 记住账号），**不**代表
  ``TC-AIQE-008`` 产品级通过，也**不**能覆盖/关闭 ``WWY-V5-001``（仍为 FAIL/OPEN）。
- 它直接驱动 Playwright 检查 localStorage，不经过正式 Defect Regression API，
  因此没有 fixed commit SHA、Mandatory Scope Snapshot、Mandatory Case Results 与
  Comparison Snapshot。缺少这些证据时状态只能是 ``NOT_PROVEN``；即使 UI 观察通过，
  也不会输出 PASS（PASS 只来自 ``defect_regression_runner.py`` 的正式回归链路）。
- UI 观察失败 → ``FAIL``；缺 Secret/环境 → ``BLOCKED``；未执行 → ``NOT_RUN``。

凭据
----
    FUTUREWAYU_TEST_USERNAME / FUTUREWAYU_TEST_PASSWORD
由 CI Secret / Vault 注入；缺失即 BLOCKED，禁止任何默认值回退。输出只记录 Secret 名称。

用法
----
    python scripts/aiqe/per_tc/futurewayu_remember_account.py \\
      --out-dir docs/aiqe/v1.6/evidence/product/TC-AIQE-008
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
AIQE_DIR = SCRIPT_DIR.parent
if str(AIQE_DIR) not in sys.path:
    sys.path.insert(0, str(AIQE_DIR))

from statuses import (  # noqa: E402
    BLOCKED,
    FAIL,
    NOT_PROVEN,
    NOT_RUN,
    PASS,
    is_pass,
    normalize,
)

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUT = "docs/aiqe/v1.6/evidence/product/TC-AIQE-008"
DEFAULT_BASE_URL = "https://xinyuwadao.com"

DEFECT_ID = "WWY-V5-006"
CASE_ID = "TC-ADM-01-D"
TC_ID = "TC-AIQE-008"
#: 本脚本永远不改写这条缺陷的状态（必须保持 FAIL/OPEN，直到它自身通过正式回归）。
UNTOUCHED_DEFECTS = ("WWY-V5-001",)

SECRET_ENV = {
    "username": "FUTUREWAYU_TEST_USERNAME",
    "password": "FUTUREWAYU_TEST_PASSWORD",
}

#: 正式回归链路必须具备的证据；直接 Playwright 复核无法提供。
REQUIRED_REGRESSION_FIELDS = (
    "regression_run_id",
    "fixed_commit_sha",
    "scope_snapshot_id",
    "comparison_snapshot_id",
    "mandatory_case_results",
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def resolve_credentials(environ: dict | None = None) -> dict:
    """只从环境变量解析测试账号；缺失即返回空值列表，绝不回退默认值。"""
    env = os.environ if environ is None else environ
    username = str(env.get(SECRET_ENV["username"]) or "").strip()
    password = str(env.get(SECRET_ENV["password"]) or "").strip()
    missing = [
        name for name, value in zip(SECRET_ENV.values(), (username, password)) if not value
    ]
    return {
        "username": username,
        "password": password,
        "available": not missing,
        "missing": missing,
        "secret_names": list(SECRET_ENV.values()),
    }


def _text(value: object) -> str:
    return str(value or "").strip()


def evaluate_single_case(observation: object, regression: object = None) -> dict:
    """纯函数：把单用例 UI 观察 + 正式回归证据折算为状态（永不伪造 PASS）。"""
    raw = observation if isinstance(observation, dict) else {}
    evidence = regression if isinstance(regression, dict) else {}
    missing_regression = [
        field for field in REQUIRED_REGRESSION_FIELDS if not evidence.get(field)
    ]

    if _text(raw.get("blocked_reason")):
        return {
            "status": BLOCKED,
            "reasons": [_text(raw.get("blocked_reason"))],
            "missing_regression_evidence": missing_regression,
        }
    if raw.get("not_run") is True or raw.get("executed") is False:
        return {
            "status": NOT_RUN,
            "reasons": ["本次没有执行单用例复核"],
            "missing_regression_evidence": missing_regression,
        }
    checks = raw.get("checks") if isinstance(raw.get("checks"), dict) else {}
    failed = [name for name, value in checks.items() if value is False]
    if failed:
        return {
            "status": FAIL,
            "reasons": [f"UI 观察失败: {', '.join(failed)}"],
            "missing_regression_evidence": missing_regression,
        }
    if not checks:
        return {
            "status": NOT_PROVEN,
            "reasons": ["没有可复核的 UI 业务断言"],
            "missing_regression_evidence": missing_regression,
        }
    if missing_regression:
        return {
            "status": NOT_PROVEN,
            "reasons": [
                "单用例点击复核不经过正式 Defect Regression API，缺少 "
                + ", ".join(missing_regression)
                + "；不能作为 TC-AIQE-008 产品级 PASS，也不能关闭 WWY-V5-001"
            ],
            "missing_regression_evidence": missing_regression,
        }
    return {
        "status": PASS,
        "reasons": ["正式回归链路证据齐全且单用例断言通过"],
        "missing_regression_evidence": [],
    }


def _captcha(captcha_url: str, timeout: float = 10.0) -> str:
    with urllib.request.urlopen(captcha_url, timeout=timeout) as response:  # noqa: S310
        return str(json.loads(response.read().decode())["code"])


def _observe(args: argparse.Namespace, creds: dict, out: Path) -> dict:
    if not creds["available"]:
        return {
            "blocked_reason": "缺少 Secret: "
            + ", ".join(creds["missing"])
            + "（禁止默认值回退）"
        }
    from playwright.sync_api import sync_playwright

    base = args.base_url.rstrip("/")
    shot = out / "remember-account.png"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(f"{base}/login", wait_until="domcontentloaded", timeout=45000)
            page.locator('input[placeholder="用户名"]').fill(creds["username"])
            page.locator('input[placeholder="密码"]').fill(creds["password"])
            captcha = _captcha(args.captcha_url) if args.captcha_url else ""
            if captcha:
                page.locator('input[placeholder="验证码"]').fill(captcha)
            page.get_by_text("记住账号").click()
            page.get_by_role("button", name="登录").click(force=True)
            page.wait_for_timeout(3000)
            page.goto(f"{base}/login", wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(1000)
            filled = page.locator('input[placeholder="用户名"]').input_value()
            remember = page.evaluate("localStorage.getItem('rememberMe')")
            stored_user = page.evaluate("localStorage.getItem('username')")
            # 截图中不保留账号明文：对输入框做文本遮蔽后再截屏。
            page.add_style_tag(
                content="input[type=password], input[placeholder='用户名'] "
                "{ -webkit-text-security: disc !important; }"
            )
            page.screenshot(path=str(shot), full_page=False)
            checks = {
                "username_refilled": filled == creds["username"],
                "remember_me_true": str(remember).lower() == "true",
                "stored_username_matches": stored_user == creds["username"],
            }
        finally:
            browser.close()
    return {
        "executed": True,
        "checks": checks,
        "screenshot": _artifact_ref(shot),
        "identity": {"executed_as": f"secret:{SECRET_ENV['username']}"},
    }


def _artifact_ref(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _safe_error(exc: BaseException, secrets: list[str]) -> str:
    """异常信息先脱敏：任何 Secret 取值都替换为 ***。"""
    text = f"{type(exc).__name__}: {str(exc)[:300]}"
    for secret in secrets:
        if secret:
            text = text.replace(secret, "***")
    return text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="WWY-V5-006 单用例点击复核（NOT TC-008 产品 PASS）")
    parser.add_argument("--out-dir", default=DEFAULT_OUT)
    parser.add_argument(
        "--base-url", default=os.environ.get("FUTUREWAYU_BASE_URL", DEFAULT_BASE_URL)
    )
    parser.add_argument("--captcha-url", default=os.environ.get("FUTUREWAYU_CAPTCHA_URL", ""))
    parser.add_argument(
        "--regression-evidence",
        default="",
        help="正式回归链路证据 JSON（缺省=没有，状态必为 NOT_PROVEN）",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):  # pragma: no cover
            pass
    args = build_parser().parse_args(argv)
    out = Path(args.out_dir)
    if not out.is_absolute():
        out = ROOT / out
    out.mkdir(parents=True, exist_ok=True)

    regression: dict = {}
    if args.regression_evidence:
        path = Path(args.regression_evidence)
        if not path.is_absolute():
            path = ROOT / path
        if path.exists():
            regression = json.loads(path.read_text(encoding="utf-8"))
        else:
            print(f"::warning::[aiqe] 回归证据不存在: {args.regression_evidence}")

    creds = resolve_credentials()
    try:
        observation = _observe(args, creds, out)
    except Exception as exc:  # noqa: BLE001 - 执行失败必须降级为 BLOCKED
        observation = {
            "blocked_reason": _safe_error(exc, [creds["username"], creds["password"]])
        }

    evaluation = evaluate_single_case(observation, regression)
    result = {
        "schema_version": "2.0",
        "artifact_kind": "single-case-click-regression",
        "generated_at": _now(),
        "tc_id": TC_ID,
        "case_scope": "single-case",
        "defect_id": DEFECT_ID,
        "case_id": CASE_ID,
        "status": normalize(evaluation["status"]),
        "product_tc_status": NOT_PROVEN,
        "product_tc_pass_claimed": False,
        "defect_state_unchanged": list(UNTOUCHED_DEFECTS),
        "ui_observation": observation,
        "formal_regression": {
            "evidence_present": bool(regression),
            "missing": evaluation["missing_regression_evidence"],
        },
        "credential_secret_names": list(SECRET_ENV.values()),
        "credential_available": creds["available"],
        "reasons": evaluation["reasons"],
        "conclusion": (
            "WWY-V5-006 单用例复核通过（仅此一条用例），但缺少正式 Defect Regression API "
            "Run / 固定 SHA / Comparison Snapshot，不能作为 TC-AIQE-008 产品级 PASS，"
            "也不能覆盖或关闭 WWY-V5-001。"
            if evaluation["status"] == NOT_PROVEN
            else evaluation["reasons"][-1] if evaluation["reasons"] else ""
        ),
    }
    (out / "remember-account.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {
                "defect_id": result["defect_id"],
                "case_id": result["case_id"],
                "status": result["status"],
                "product_tc_status": result["product_tc_status"],
                "checks": observation.get("checks", {}),
                "blocked_reason": observation.get("blocked_reason", ""),
            },
            ensure_ascii=False,
        )
    )
    return 0 if is_pass(result["status"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
