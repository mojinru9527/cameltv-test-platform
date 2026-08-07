"""Batch 122 — 体育用例结构校验（幂等、本地执行）。

校验 `work-logs/evidence/batch-122/cases/**/*.json` 的用例是否符合
`docs/体育平台-用例结构规范.md`：
- 必填字段、域白名单、模块路径（入口/一级/二级）、编号格式
- 深度拦截：单步「查看XX」无断言、空 preconditions/expected、接口 body 为空对象

运行: <python> scripts/sports/validate-case-structure.py [--cases <dir|file>]
退出码: 0=全部通过 / 1=存在硬错误
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ALLOWED_DOMAINS = {
    "体育-用户端-功能",
    "体育-运营后台-功能",
    "体育-接口测试",
}
ENTRANCES = {
    "安卓iOS": "AND",
    "PC-web": "PC",
    "移动端-web": "WEB",
    "运营后台": "ADM",
    "konfi": "KON",
}
INTERFACE_ENTRANCE = {"接口测试": "I"}
ALLOWED_TYPES = {"manual", "api", "ui"}
TRIVIAL_PATTERNS = re.compile(r"^(查看|进入|打开).{0,12}(展示|页面|模块|列表)?$")

REQUIRED_FIELDS = ["case_id", "title", "domain", "module", "case_type", "priority",
                   "preconditions", "steps", "expected_result"]


def iter_case_files(path: Path):
    if path.is_file():
        yield path
        return
    for p in sorted(path.rglob("*.json")):
        yield p


def validate_case(case: dict, path: str) -> list[str]:
    errs: list[str] = []
    for f in REQUIRED_FIELDS:
        if f not in case or case[f] in (None, "", [], {}):
            errs.append(f"缺必填字段: {f}")

    domain = case.get("domain", "")
    if domain not in ALLOWED_DOMAINS:
        errs.append(f"domain 不在白名单: {domain!r}")

    module = case.get("module", "")
    parts = [p for p in module.split("/") if p]
    if not parts or parts[0] not in ENTRANCES:
        errs.append(f"module 入口不合法: {module!r}（需 入口/一级/二级）")
    elif len(parts) < 2:
        errs.append(f"module 层级不足: {module!r}（需 入口/一级/二级）")

    cid = case.get("case_id", "")
    if domain == "体育-接口测试":
        ok = bool(re.match(r"^SP-I-[A-Z0-9-]+-\d{3}$", cid))
    else:
        entrance_code = ENTRANCES.get(parts[0] if parts else "", "")
        ok = bool(entrance_code) and cid.startswith(f"SP-{entrance_code}-")
    if not ok:
        errs.append(f"case_id 格式不符: {cid!r}")

    ct = case.get("case_type", "")
    if ct not in ALLOWED_TYPES:
        errs.append(f"case_type 不合法: {ct!r}")

    pre = str(case.get("preconditions", "") or "").strip()
    if not pre or pre == "—":
        errs.append("preconditions 为空")

    steps = case.get("steps") or []
    if ct == "manual":
        if not isinstance(steps, list) or len(steps) == 0:
            errs.append("manual 用例 steps 为空")
        elif len(steps) == 1:
            desc = str(steps[0].get("desc", "")) if isinstance(steps[0], dict) else ""
            if TRIVIAL_PATTERNS.match(desc.strip()):
                errs.append(f"单步冒烟用例被拦截: {desc!r}")
    exp = str(case.get("expected_result", "") or "").strip()
    if not exp:
        errs.append("expected_result 为空")
    if ct == "api":
        if not case.get("api_endpoint"):
            errs.append("api 用例缺 api_endpoint")
        body = case.get("api_body")
        if body is not None and body != "":
            try:
                b = json.loads(body) if isinstance(body, str) else body
                if b == {}:
                    errs.append("api_body 为空对象（缺少真实请求体）")
            except Exception:
                errs.append("api_body 非合法 JSON")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser()
    default = Path(__file__).resolve().parents[1] / "work-logs" / "evidence" / "batch-122" / "cases"
    ap.add_argument("--cases", default=str(default))
    args = ap.parse_args()

    root = Path(args.cases)
    if not root.exists():
        print(f"[validator] 目录不存在（跳过，非错误）: {root}", flush=True)
        return 0
    total = hard = 0
    for fp in iter_case_files(root):
        total += 1
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[validator] {fp} 解析失败: {e}", flush=True)
            hard += 1
            continue
        items = data if isinstance(data, list) else [data]
        for case in items:
            if not isinstance(case, dict):
                hard += 1
                print(f"[validator] {fp} 非对象用例", flush=True)
                continue
            errs = validate_case(case, str(fp))
            if errs:
                hard += 1
                print(f"[validator] FAIL {case.get('case_id', '?')} ({fp})", flush=True)
                for e in errs:
                    print(f"    - {e}", flush=True)
    print(f"[validator] files={total} hard_errors={hard}", flush=True)
    return 1 if hard else 0


if __name__ == "__main__":
    raise SystemExit(main())

