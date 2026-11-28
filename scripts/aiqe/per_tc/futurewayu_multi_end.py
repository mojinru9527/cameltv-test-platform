"""TC-AIQE-009：未来娃屿多端 AC 对照（桌面 Chrome / Android Appium / 微信小程序）。

V1.6.2 FIX-007 状态语义
-----------------------
- 只有 ``PASS`` 计入通过；``SEMI_AUTOMATIC`` / ``MANUAL`` / ``SCREENSHOT`` 只允许降级为
  ``PARTIAL``（唯一事实源 ``scripts/aiqe/statuses.py``），不再参与成功聚合。
- 任何 mandatory 平台必须同时具备业务页面导航、关键交互、业务状态断言、执行身份、
  执行版本、可复核 artifact，才可能 PASS；只看 HTTP<400 或截图一律不得 PASS。
- 微信小程序在无源码/无自动化 SDK 的现状下只能复制面板截图 → ``PARTIAL``，并写明
  未覆盖范围；只有受控真机 / 外部 Runner 完成业务断言后才可能 PASS。
- 总状态按 mandatory 平台最弱覆盖聚合：任一 mandatory 非 PASS，整体不得 PASS。
- 退出码：0 仅当整体 PASS；FAIL/BLOCKED/NOT_RUN/NOT_PROVEN/PARTIAL 一律 1。

凭据
----
    FUTUREWAYU_TEST_USERNAME / FUTUREWAYU_TEST_PASSWORD
由 CI Secret / Vault 注入，缺失即 BLOCKED，禁止任何默认值回退。日志与证据只记录
Secret 名称，不记录取值。

用法
----
    python scripts/aiqe/per_tc/futurewayu_multi_end.py \\
      --out-dir docs/aiqe/v1.6/evidence/product/TC-AIQE-009
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
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
    PARTIAL,
    PASS,
    aggregate,
    is_pass,
    normalize,
)

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUT = "docs/aiqe/v1.6/evidence/product/TC-AIQE-009"
DEFAULT_BASE_URL = "https://xinyuwadao.com"
DEFAULT_ANDROID_PACKAGE = "uni.app.UNIE3747D0"
DEFAULT_ANDROID_ACTIVITY = "io.dcloud.PandoraEntryActivity"
DEFAULT_DEVICE = "9f0564ba"

#: mandatory 平台契约。任一未 PASS，整体不得 PASS。
MANDATORY_PLATFORMS: tuple[str, ...] = ("desktop", "android", "wechat_miniapp")

PLATFORM_TITLES = {
    "desktop": "桌面 Chrome（运营后台）",
    "android": "Android Appium（未来娃屿 App）",
    "wechat_miniapp": "微信小程序（未来娃屿）",
}

#: 只有这些自动化模式才能产出机器可复核的业务断言。
COMPLETE_AUTOMATION_MODES: frozenset[str] = frozenset(
    {"playwright", "appium", "external_runner", "controlled_device"}
)
#: 这些模式只能证明"看到过界面"，永远不得 PASS。
MANUAL_AUTOMATION_MODES: frozenset[str] = frozenset(
    {"screenshot_copy", "panel_screenshot", "manual", "screenshot"}
)

SECRET_ENV = {
    "username": "FUTUREWAYU_TEST_USERNAME",
    "password": "FUTUREWAYU_TEST_PASSWORD",
}

WECHAT_UNCOVERED = (
    "微信小程序未进入业务页面：只复制了微信面板截图，未执行登录/门店/订单等业务流程",
    "无源码与自动化 SDK，未产生机器可复核的业务状态断言、Trace 或关键交互记录",
    "截图不能证明业务状态，只能作为 PARTIAL 的辅助证据",
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def resolve_credentials(environ: dict | None = None) -> dict:
    """只从环境变量解析测试账号；缺失即返回空值列表，绝不回退默认值。"""
    env = os.environ if environ is None else environ
    username = str(env.get(SECRET_ENV["username"]) or "").strip()
    password = str(env.get(SECRET_ENV["password"]) or "").strip()
    missing = [name for name, value in zip(SECRET_ENV.values(), (username, password)) if not value]
    return {
        "username": username,
        "password": password,
        "available": not missing,
        "missing": missing,
        "secret_names": list(SECRET_ENV.values()),
    }


def _text(value: object) -> str:
    return str(value or "").strip()


def _dict(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _assertions(raw: dict) -> list[dict]:
    items = raw.get("business_assertions")
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []


def _artifacts(raw: dict) -> list[str]:
    items = raw.get("artifacts")
    if not isinstance(items, list):
        return []
    return [str(item) for item in items if _text(item)]


def _identity_record(raw: dict) -> dict:
    identity = _dict(raw.get("identity"))
    return {
        "executed_as": _text(identity.get("executed_as")),
        "role": _text(identity.get("role")),
        "secret_names": [
            str(name) for name in identity.get("secret_names") or [] if _text(name)
        ],
    }


def _version_record(raw: dict) -> dict:
    version = _dict(raw.get("build_version"))
    return {
        "app_version": _text(version.get("app_version") or version.get("version")),
        "commit_sha": _text(version.get("commit_sha")),
        "image_digest": _text(version.get("image_digest")),
        "source": _text(version.get("source")),
    }


def _has_version(version: dict) -> bool:
    return bool(
        version.get("app_version")
        or version.get("commit_sha")
        or version.get("image_digest")
    )


def _navigation(raw: dict) -> dict:
    nav = _dict(raw.get("business_navigation"))
    return {
        "url": _text(nav.get("url")),
        "title": _text(nav.get("title") or nav.get("page_title")),
        "marker": _text(nav.get("page_marker") or nav.get("marker")),
    }


def _interactions(raw: dict) -> list[dict]:
    items = raw.get("key_interactions")
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []


def _result(
    platform: str,
    status: str,
    reasons: list[str],
    *,
    evidence: dict | None = None,
    uncovered: list[str] | None = None,
) -> dict:
    return {
        "platform": platform,
        "title": PLATFORM_TITLES.get(platform, platform),
        "status": normalize(status),
        "reasons": [item for item in reasons if _text(item)],
        "evidence": evidence or {},
        "uncovered": [item for item in (uncovered or []) if _text(item)],
    }


def evaluate_platform(platform: str, raw: object) -> dict:
    """纯函数：把单个平台的原始观测折算为 PASS/PARTIAL/NOT_PROVEN/BLOCKED/NOT_RUN/FAIL。

    只看 HTTP<400、只看截图、只有手工复核都不足以 PASS。
    """
    if not isinstance(raw, dict) or not raw:
        return _result(platform, NOT_RUN, ["缺少平台执行记录"])

    evidence = {
        "automation_mode": _text(raw.get("automation_mode")),
        "navigation": _navigation(raw),
        "identity": _identity_record(raw),
        "build_version": _version_record(raw),
        "assertions": _assertions(raw),
        "interactions": _interactions(raw),
        "artifacts": _artifacts(raw),
    }

    if _text(raw.get("blocked_reason")) or raw.get("blocked") is True:
        return _result(
            platform,
            BLOCKED,
            [_text(raw.get("blocked_reason")) or "平台执行被阻塞（未给出原因）"],
            evidence=evidence,
        )
    if raw.get("not_run") is True or raw.get("executed") is False:
        return _result(platform, NOT_RUN, ["本次没有执行该平台"], evidence=evidence)

    legacy = raw.get("legacy_status")
    if _text(legacy):
        mapped = normalize(legacy)
        evidence["legacy_status"] = _text(legacy)
        evidence["legacy_mapped_to"] = mapped
        if mapped != PASS:
            # 旧状态（SEMI_AUTOMATIC/MANUAL/SCREENSHOT）只允许降级，不允许折算 PASS。
            return _result(
                platform,
                mapped,
                [f"旧状态 {legacy} 只允许映射为 {mapped}，不计入 PASS"],
                evidence=evidence,
                uncovered=["旧状态没有可复核的业务断言"],
            )

    mode = evidence["automation_mode"].lower()
    assertions = evidence["assertions"]
    if (
        not mode
        and _text(raw.get("screenshot"))
        and not evidence["navigation"]["url"]
        and not assertions
    ):
        # 兼容旧报告：只有截图、没有导航/断言，按截图模式处理（最多 PARTIAL）。
        mode = "screenshot_copy"
        evidence["automation_mode"] = mode
    failed = [
        _text(item.get("name")) or f"assertion-{index}"
        for index, item in enumerate(assertions, 1)
        if item.get("passed") is False or normalize(item.get("status")) == FAIL
    ]

    if failed:
        return _result(
            platform,
            FAIL,
            [f"业务断言失败: {', '.join(failed)}"],
            evidence=evidence,
        )

    if mode in MANUAL_AUTOMATION_MODES:
        # 截图/人工复核最多 PARTIAL；即使有人手工补了断言也不得 PASS。
        reasons = [f"自动化模式 {mode} 只能算 PARTIAL，不是机器可复核执行"]
        if assertions:
            reasons.append("人工/截图模式下的断言不计入机器 PASS")
        uncovered = list(WECHAT_UNCOVERED) if platform == "wechat_miniapp" else [
            "人工/截图复核未覆盖真实业务流程与业务状态断言"
        ]
        return _result(platform, PARTIAL, reasons, evidence=evidence, uncovered=uncovered)

    missing: list[str] = []
    navigation = evidence["navigation"]
    if not (navigation["url"] and (navigation["title"] or navigation["marker"])):
        missing.append("缺少业务页面导航记录（URL + 页面标识）")
    if not evidence["interactions"]:
        missing.append("缺少关键交互记录")
    if not assertions:
        if navigation["url"]:
            # 已进入业务页面但没有业务断言 → NOT_PROVEN（不是 PASS，也不再退化成 PARTIAL）。
            return _result(
                platform,
                NOT_PROVEN,
                ["进入业务页面但没有业务状态断言"],
                evidence=evidence,
                uncovered=["业务状态未被断言"],
            )
        return _result(
            platform,
            NOT_PROVEN,
            ["既没有业务页面导航，也没有业务断言"],
            evidence=evidence,
            uncovered=["业务页面导航与业务状态断言均缺失"],
        )
    if not evidence["identity"]["executed_as"]:
        missing.append("缺少执行身份（只允许记录 Secret 名称，不记录取值）")
    if not _has_version(evidence["build_version"]):
        missing.append("缺少执行版本（app_version / commit_sha / image_digest 至少一项）")
    if not evidence["artifacts"]:
        missing.append("缺少可复核 artifact（截图/录屏/Trace）")

    if missing:
        return _result(
            platform,
            NOT_PROVEN,
            missing,
            evidence=evidence,
            uncovered=["证据链不完整，不能作为 PASS"],
        )

    return _result(
        platform,
        PASS,
        ["业务导航/关键交互/业务断言/执行身份/版本/artifact 齐全"],
        evidence=evidence,
    )


def aggregate_multi_end(
    platforms: object,
    mandatory: tuple[str, ...] = MANDATORY_PLATFORMS,
) -> dict:
    """纯函数：按 mandatory 平台最弱覆盖聚合多端总状态。

    任一 mandatory 平台非 PASS（含缺失记录）→ 整体不得 PASS。
    """
    raw_platforms = platforms if isinstance(platforms, dict) else {}
    evaluated: dict[str, dict] = {}
    gaps: list[str] = []
    for name in mandatory:
        raw = raw_platforms.get(name)
        if raw is None:
            evaluated[name] = _result(name, NOT_RUN, ["缺少平台执行记录"])
            gaps.append(f"{name}: 缺少平台执行记录")
        else:
            evaluated[name] = evaluate_platform(name, raw)
        if evaluated[name]["status"] != PASS:
            gaps.append(f"{name}: {evaluated[name]['status']}")
    values = [evaluated[name]["status"] for name in mandatory]
    overall = aggregate(values, empty=NOT_PROVEN)
    uncovered = [
        {
            "platform": name,
            "status": evaluated[name]["status"],
            "scope": evaluated[name]["uncovered"],
        }
        for name in mandatory
        if evaluated[name]["status"] != PASS
    ]
    return {
        "status": overall,
        "mandatory_platforms": list(mandatory),
        "platforms": evaluated,
        "passing_platforms": [name for name in mandatory if is_pass(evaluated[name]["status"])],
        "uncovered_scope": uncovered,
        "evidence_gaps": gaps,
    }


def validate_multi_end_result(
    result: object,
    mandatory: tuple[str, ...] = MANDATORY_PLATFORMS,
) -> dict:
    """纯函数：拒绝把 PARTIAL/截图结果手工改写成整体 PASS 的报告。"""
    payload = result if isinstance(result, dict) else {}
    declared_raw = payload.get("status")
    declared = normalize(declared_raw, empty=NOT_RUN)
    evidence = payload.get("platform_evidence")
    sources = evidence if isinstance(evidence, dict) else payload.get("platforms")
    computed = aggregate_multi_end(sources, mandatory)
    reasons: list[str] = []
    forged = declared == PASS and computed["status"] != PASS
    if forged:
        weakest = ", ".join(computed["evidence_gaps"]) or computed["status"]
        reasons.append(f"报告声明整体 PASS 被拒绝：mandatory 平台未全部 PASS（{weakest}）")
    final = aggregate([declared, computed["status"]], empty=computed["status"])
    if not forged and declared != computed["status"]:
        reasons.append(
            f"报告声明 {declared} 与按原始平台记录聚合的 {computed['status']} 不一致，按较弱者处理"
        )
    return {
        "status": final,
        "declared": _text(declared_raw),
        "computed": computed["status"],
        "forged_pass_rejected": forged,
        "reasons": reasons,
        "platforms": computed["platforms"],
        "uncovered_scope": computed["uncovered_scope"],
        "evidence_gaps": computed["evidence_gaps"],
    }


def exit_code(status: object) -> int:
    """0 仅当整体 PASS；其余状态一律非零。"""
    return 0 if is_pass(status) else 1


def _captcha(captcha_url: str, timeout: float = 10.0) -> str:
    with urllib.request.urlopen(captcha_url, timeout=timeout) as response:  # noqa: S310
        return str(json.loads(response.read().decode())["code"])


def _artifact_ref(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _safe_error(exc: BaseException, secrets: list[str]) -> str:
    """异常信息先脱敏：任何 Secret 取值都替换为 ***，日志只留类型与脱敏文本。"""
    text = f"{type(exc).__name__}: {str(exc)[:300]}"
    for secret in secrets:
        if secret:
            text = text.replace(secret, "***")
    return text


def _run_desktop(args: argparse.Namespace, creds: dict, out: Path) -> dict:
    if not creds["available"]:
        return {
            "blocked_reason": (
                "缺少 Secret: " + ", ".join(creds["missing"]) + "（禁止默认值回退）"
            )
        }
    from playwright.sync_api import sync_playwright

    base = args.base_url.rstrip("/")
    menu_text = args.desktop_menu_text
    shot = out / "desktop-business.png"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        try:
            page.goto(f"{base}/login", wait_until="domcontentloaded", timeout=45000)
            page.locator('input[placeholder="用户名"]').fill(creds["username"])
            page.locator('input[placeholder="密码"]').fill(creds["password"])
            captcha = _captcha(args.captcha_url) if args.captcha_url else ""
            if captcha:
                page.locator('input[placeholder="验证码"]').fill(captcha)
            page.get_by_role("button", name="登录").click(force=True)
            page.wait_for_timeout(3000)
            page.wait_for_url(lambda url: "/login" not in url, timeout=20000)
            business_url = page.url
            business_title = page.title()
            marker = page.get_by_text(menu_text, exact=False).first
            marker_visible = marker.count() > 0 and marker.is_visible()
            page.screenshot(path=str(shot), full_page=False)
            interactions = [
                {"action": "login", "result": "submitted"},
                {"action": "open_business_menu", "target": menu_text, "result": marker_visible},
            ]
            assertions = [
                {
                    "name": "login_redirected_to_business_page",
                    "expected": "url 不含 /login",
                    "actual": business_url,
                    "passed": "/login" not in business_url,
                },
                {
                    "name": "business_menu_visible",
                    "expected": menu_text,
                    "actual": marker_visible,
                    "passed": bool(marker_visible),
                },
            ]
        finally:
            browser.close()
    return {
        "executed": True,
        "automation_mode": "playwright",
        "business_navigation": {
            "url": business_url,
            "title": business_title,
            "page_marker": menu_text,
        },
        "key_interactions": interactions,
        "business_assertions": assertions,
        "identity": {
            "executed_as": f"secret:{SECRET_ENV['username']}",
            "role": args.test_role,
            "secret_names": list(SECRET_ENV.values()),
        },
        "build_version": {
            "app_version": args.expected_build,
            "source": "FUTUREWAYU_BUILD_VERSION / --expected-build",
        },
        "artifacts": [_artifact_ref(shot)],
    }


def _run_android(args: argparse.Namespace, out: Path) -> dict:
    if args.skip_android:
        return {"blocked_reason": "本次未执行 Android（--skip-android）"}
    from appium import webdriver
    from appium.options.android import UiAutomator2Options

    options = UiAutomator2Options().load_capabilities(
        {
            "platformName": "Android",
            "appium:automationName": "UiAutomator2",
            "appium:deviceName": args.device_name,
            "appium:appPackage": DEFAULT_ANDROID_PACKAGE,
            "appium:appActivity": "io.dcloud.PandoraEntry",
            "appium:noReset": True,
            "appium:newCommandTimeout": 120,
        }
    )
    shot = out / "android-business.png"
    driver = webdriver.Remote(args.appium_url, options=options)
    try:
        driver.wait_activity(DEFAULT_ANDROID_ACTIVITY, 20)
        page_source = driver.page_source or ""
        business_text = args.android_business_text
        visible = bool(business_text) and business_text in page_source
        driver.get_screenshot_as_file(str(shot))
        capabilities = dict(driver.capabilities or {})
        device = capabilities.get("deviceModel") or capabilities.get("deviceName") or args.device_name
        platform_version = str(capabilities.get("platformVersion") or "")
        interactions = [
            {"action": "launch_app", "target": DEFAULT_ANDROID_PACKAGE, "result": "launched"},
            {
                "action": "assert_business_text",
                "target": business_text,
                "result": visible,
            },
        ]
        assertions = (
            [
                {
                    "name": "android_business_text_visible",
                    "expected": business_text,
                    "actual": visible,
                    "passed": visible,
                }
            ]
            if business_text
            else []
        )
        return {
            "executed": True,
            "automation_mode": "appium",
            "business_navigation": {
                "url": f"android://{DEFAULT_ANDROID_PACKAGE}/{DEFAULT_ANDROID_ACTIVITY}",
                "title": f"{device} / Android {platform_version}",
                "page_marker": business_text,
            },
            "key_interactions": interactions,
            "business_assertions": assertions,
            "identity": {
                "executed_as": args.android_account_secret,
                "role": "android-app",
                "secret_names": [args.android_account_secret] if args.android_account_secret else [],
            },
            "build_version": {
                "app_version": args.android_build or str(capabilities.get("appVersion") or ""),
                "source": "appium capabilities appVersion / --android-build",
            },
            "artifacts": [_artifact_ref(shot)],
        }
    finally:
        driver.quit()


def _run_wechat(args: argparse.Namespace, out: Path) -> dict:
    source = Path(args.wechat_screenshot)
    if not source.is_absolute():
        source = ROOT / source
    if not source.exists():
        return {"blocked_reason": f"缺少微信小程序面板截图: {_artifact_ref(source)}"}
    target = out / "wechat-miniapp.png"
    shutil.copyfile(source, target)
    return {
        "executed": True,
        "automation_mode": "screenshot_copy",
        "note": "复制微信小程序面板截图；无开发者权限，未做任何机器断言",
        "artifacts": [_artifact_ref(target)],
        "screenshot": _artifact_ref(target),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TC-AIQE-009 多端 AC 对照（诚实状态）")
    parser.add_argument("--out-dir", default=DEFAULT_OUT)
    parser.add_argument("--base-url", default=os.environ.get("FUTUREWAYU_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--appium-url", default=os.environ.get("APPIUM_URL", "http://127.0.0.1:4723"))
    parser.add_argument("--captcha-url", default=os.environ.get("FUTUREWAYU_CAPTCHA_URL", ""))
    parser.add_argument(
        "--wechat-screenshot",
        default=os.environ.get(
            "FUTUREWAYU_WECHAT_SCREENSHOT",
            "docs/aiqe/v1.6/evidence/product/wechat-miniapp-futurewayu.png",
        ),
    )
    parser.add_argument("--desktop-menu-text", default=os.environ.get("FUTUREWAYU_DESKTOP_MENU_TEXT", "工作台"))
    parser.add_argument("--android-business-text", default=os.environ.get("FUTUREWAYU_ANDROID_BUSINESS_TEXT", ""))
    parser.add_argument("--android-account-secret", default=os.environ.get("FUTUREWAYU_ANDROID_ACCOUNT_SECRET", ""))
    parser.add_argument("--android-build", default=os.environ.get("FUTUREWAYU_ANDROID_BUILD", ""))
    parser.add_argument("--device-name", default=os.environ.get("FUTUREWAYU_ANDROID_DEVICE", DEFAULT_DEVICE))
    parser.add_argument("--expected-build", default=os.environ.get("FUTUREWAYU_BUILD_VERSION", ""))
    parser.add_argument("--test-role", default=os.environ.get("FUTUREWAYU_TEST_ROLE", "operator"))
    parser.add_argument(
        "--skip-android",
        action="store_true",
        help="跳过 Android 时该平台记 BLOCKED（不能靠跳过拿到整体 PASS）",
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

    creds = resolve_credentials()
    raw_platforms: dict[str, dict] = {}
    for name, runner in (
        ("desktop", lambda: _run_desktop(args, creds, out)),
        ("android", lambda: _run_android(args, out)),
        ("wechat_miniapp", lambda: _run_wechat(args, out)),
    ):
        try:
            raw_platforms[name] = runner()
        except Exception as exc:  # noqa: BLE001 - 执行失败必须降级为 BLOCKED
            raw_platforms[name] = {
                "blocked_reason": _safe_error(exc, [creds["username"], creds["password"]]),
            }

    result: dict = {
        "schema_version": "2.0",
        "tc_id": "TC-AIQE-009",
        "artifact_kind": "multi-end-result",
        "generated_at": _now(),
        "base_url": args.base_url,
        "credential_secret_names": list(SECRET_ENV.values()),
        "credential_available": creds["available"],
        "platform_evidence": raw_platforms,
        "platforms": raw_platforms,
    }
    aggregated = aggregate_multi_end(raw_platforms)
    result.update(aggregated)
    # 校验必须基于原始平台观测，而不是已折算后的 platforms，防止自证 PASS。
    validation = validate_multi_end_result(
        {"status": aggregated["status"], "platforms": raw_platforms}
    )
    result["status"] = validation["status"]
    result["validation"] = validation
    result["conclusion"] = (
        "所有 mandatory 平台完成真实业务执行与断言"
        if validation["status"] == PASS
        else "未满足多端 PASS 条件：" + "; ".join(validation["evidence_gaps"][:6])
    )
    (out / "multi-end.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "platforms": {
                    key: value["status"] for key, value in result["platforms"].items()
                },
                "uncovered": [item["platform"] for item in result["uncovered_scope"]],
            },
            ensure_ascii=False,
        )
    )
    return exit_code(result["status"])


if __name__ == "__main__":
    raise SystemExit(main())
