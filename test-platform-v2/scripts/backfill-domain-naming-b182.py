# -*- coding: utf-8 -*-
"""Batch 182（FIX-173-P3-04）域命名归一：test_case.domain 裸域回填脚本。

背景
----
用例「所属域」与追溯「按域覆盖」存在五种命名范式混排（batch-173 审查结论）：
`用户端/xxx`、`运营后台/xxx`、`接口测试/xxx`、`体育-运营后台-功能` 式连字符、
裸域（UGC、广告…）。batch-178 已给前端域下拉做分组+搜索，本脚本把库内
`test_case.domain` 的裸域归一为 `用户端/{裸域名}`，使数据口径与前端
`groupDomainLabel`（frontend/src/utils/domainNaming.ts）完全一致。

规则（与前端 groupDomainLabel 相同）
------------------------------------
1. 平台前缀直接保留：`用户端`、`运营后台`、`接口测试`（含平台名本身如 `接口测试`，
   以及 `用户端/首页`、`运营后台-热门比赛配置` 等带斜杠/连字符的变体）→ 不修改；
2. `体育-运营后台-*`（如 `体育-运营后台-功能`）→ 仅展示归组「运营后台」，库值不修改；
3. 其余裸域（UGC、广告等）→ `用户端/{裸域名}`，如 `UGC` → `用户端/UGC`；
4. 空值/空白 → 不修改。

幂等：已归一的值（如 `用户端/UGC`）再次运行不会二次加前缀。

用法
----
默认只读 dry-run（打印将改动的映射清单与统计，不写库）：
    python scripts/backfill-domain-naming-b182.py [--dry-run]

写入数据库（先跑 dry-run 人工核对映射清单后再执行）：
    python scripts/backfill-domain-naming-b182.py --apply

DATABASE_URL 取值优先级：环境变量 > backend/.env（脚本自动解析）。
仅更新未软删（is_deleted=0）用例的 domain 字段。
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent / "backend"

# ── 平台前缀（与前端 domainNaming.ts 的 PLATFORM_GROUPS 一致）──
PLATFORM_PREFIXES: tuple[str, ...] = ("用户端", "运营后台", "接口测试")

# ── 审查点名的已知裸域样本（batch-173 report-ui-design.md / evidence 27-stats2.json）──
# 规则对库内任意裸域生效，此清单仅用于 dry-run 报告说明覆盖情况。
KNOWN_BARE_DOMAINS: tuple[str, ...] = (
    "UGC",            # 审查点名：裸域
    "广告",           # 审查点名：裸域
    "UGC内容",        # 27-stats2.json 观测值
    "UGC文章管理",
    "UGC统计指标",
    "UGC内容管理",
    "WEB-第三方社媒引导移除",   # 英文前缀变体（审查观测）
    "体育数据-篮球",           # 连字符裸域（审查观测）
    "篮球相关-广告调整",
    "通知-比分变更",
    "APP-版本更新",
    # 13 用户模块 / 15 运营模块清单（docs/体育平台-关联基座.json）中的裸域形态
    "首页", "搜索", "资讯", "赛事详情", "直播间", "回放", "世界杯专题", "登录注册",
    "通用", "个人中心", "赛事预测", "广告系统", "银钻系统", "银钻预测", "付费活动",
    "骆驼币系统",
)

TOP_N = 20  # 映射 Top-N 统计条数


def normalize_domain(domain: str) -> str:
    """裸域 → `用户端/{裸域名}`；已归一/平台前缀/`体育-运营后台-*`/空值不修改（幂等）。

    与前端 `groupDomainLabel(domain).label` 的转换口径一致：
    前端对裸域的展示标签即为 `用户端/{原名}`，本函数把该标签落库。
    """
    d = (domain or "").strip()
    if not d:
        return domain or ""
    for prefix in PLATFORM_PREFIXES:
        if d == prefix or d.startswith(prefix + "/") or d.startswith(prefix + "-"):
            return d
    if d.startswith("体育-运营后台"):
        return d
    return "用户端/" + d


def load_database_url() -> str:
    """DATABASE_URL：环境变量优先，其次 backend/.env；返回并写入环境变量供 app 读取。"""
    raw = os.environ.get("DATABASE_URL", "")
    if not raw:
        env_file = BACKEND_DIR / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    if key.strip() == "DATABASE_URL":
                        raw = value.strip().strip('"').strip("'")
                        break
    if not raw:
        raise SystemExit(
            "未找到 DATABASE_URL：请设置环境变量，"
            "或确认 backend/.env 中存在 DATABASE_URL"
        )
    # 相对 sqlite 路径按 backend 目录解析为绝对路径（任意 cwd 运行不建错目录）
    if raw.startswith("sqlite:///") and not raw[len("sqlite:///"):].startswith(
        ("/", "\\\\")
    ):
        rel = raw[len("sqlite:///"):]
        raw = "sqlite:///" + str((BACKEND_DIR / rel).resolve()).replace("\\", "/")
    os.environ["DATABASE_URL"] = raw
    return raw


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Batch 182 域命名归一：test_case.domain 裸域 → 用户端/{裸域名}"
            "（默认 dry-run 只读）"
        ),
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="写入数据库；不传（或传 --dry-run）时只读预览，不修改任何数据",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只读预览（默认行为，可省略）",
    )
    args = parser.parse_args()

    url = load_database_url()
    print(f"[batch-182] DATABASE_URL = {url}")
    print(f"[batch-182] 模式 = "
          f"{'写入（--apply）' if args.apply else '只读 dry-run（默认）'}")

    # 复用 backend 的 models / 会话（导入前已写入 DATABASE_URL 环境变量）
    sys.path.insert(0, str(BACKEND_DIR))
    from sqlalchemy import func, inspect, update  # noqa: E402
    from sqlalchemy.orm import Session  # noqa: E402

    from app.core.db import SessionLocal  # noqa: E402
    from app.models.test_case import TestCase  # noqa: E402

    if not inspect(SessionLocal().get_bind()).has_table(TestCase.__tablename__):
        raise SystemExit(
            f"数据库 {url} 中不存在表 {TestCase.__tablename__}，"
            "请检查 DATABASE_URL 指向的库"
        )

    session: Session = SessionLocal()
    try:
        # 只读聚合：未软删用例按 domain 分组计数
        total = session.query(TestCase).filter(TestCase.is_deleted.is_(False)).count()
        rows = (
            session.query(TestCase.domain, func.count(TestCase.id))
            .filter(TestCase.is_deleted.is_(False))
            .group_by(TestCase.domain)
            .order_by(func.count(TestCase.id).desc())
            .all()
        )
        distinct = len(rows)
        changed: list[tuple[str, str, int]] = []  # (原值, 目标值, 条数)
        for domain, cnt in rows:
            target = normalize_domain(domain)
            if target != domain:
                changed.append((domain, target, cnt))
        changed_rows = sum(cnt for _, _, cnt in changed)
        known_hit = [d for d, _, _ in changed if d in KNOWN_BARE_DOMAINS]

        # ── 报告 ──
        print("\n===== 统计 =====")
        print(f"用例总数（未软删）: {total}")
        print(f"域去重值数        : {distinct}")
        if total:
            pct = 100.0 * changed_rows / total
            print(f"将改行数          : {changed_rows}（占总数 {pct:.2f}%）")
        else:
            print("将改行数          : 0（库中无未软删用例）")
        print(f"将改域值数        : {len(changed)}")
        print(f"无需改动域值数    : {distinct - len(changed)}")
        print(f"已知裸域样本命中  : {len(known_hit)}（{known_hit}）")

        print(f"\n===== 映射清单（全部 {len(changed)} 项，按条数降序）=====")
        if not changed:
            print("（无，所有域值已归一）")
        for i, (src, dst, cnt) in enumerate(changed, 1):
            print(f"{i:3d}. {src!r} → {dst!r} ({cnt} 条)")

        print(f"\n===== 映射 Top{TOP_N}（按条数降序）=====")
        if not changed:
            print("（无）")
        for i, (src, dst, cnt) in enumerate(changed[:TOP_N], 1):
            print(f"{i:3d}. {src!r} → {dst!r} ({cnt} 条)")
        if len(changed) > TOP_N:
            print(f"… 其余 {len(changed) - TOP_N} 项见上方完整清单")

        if not args.apply:
            print("\n[dry-run] 未写库。核对映射清单后如需落库，请执行：")
            print("python scripts/backfill-domain-naming-b182.py --apply")
            return 0

        # ── 写入：逐映射 UPDATE（幂等：目标 = 原值 的映射已在上方被过滤）──
        if not changed:
            print("\n[apply] 无变更可写，跳过。")
            return 0
        written = 0
        for src, dst, _ in changed:
            res = session.execute(
                update(TestCase)
                .where(TestCase.domain == src, TestCase.is_deleted.is_(False))
                .values(domain=dst)
            )
            written += res.rowcount or 0
        session.commit()
        print(f"\n[apply] 已更新 {written} 行（映射 {len(changed)} 项）。")
        # 复核：原裸域值应已清零
        leftover = session.query(TestCase).filter(
            TestCase.is_deleted.is_(False),
            TestCase.domain.in_([src for src, _, _ in changed]),
        ).count()
        print(f"[apply] 复核：原裸域值剩余 {leftover} 行。")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
