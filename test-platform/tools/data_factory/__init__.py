"""测试数据工厂：按 YAML 规则生成成套数据并灌库 / 导出。

能力：
- 字段级生成（手机/身份证/邮箱/枚举/数值边界等，基于 Faker）
- 跨字段约束引擎（constraints: 表达式，不满足则重抽）
- 关联数据成套生成（relations: 父带子，外键自动对齐）
- 脏数据模式（emoji/注入串/超长/全角，--mode dirty）
- 场景模板（--template vip_user → templates/vip_user.yaml）
- 输出 db / sql / json

规则示例见 tools/data_factory/examples/user.yaml。
"""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

import yaml

from core import logging as log
from core.models import RunContext

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE / "templates"

DIRTY_VALUES = [
    "😀🎉", "' OR '1'='1", "<script>alert(1)</script>",
    "ａｂｃ１２３", "　", "x" * 300, "", "null", "-1",
]


# --------------------------------------------------------------------------- #
# 字段生成
# --------------------------------------------------------------------------- #
def _gen_field(spec: dict[str, Any], faker) -> Any:
    t = spec.get("type", "str")
    if t == "int":
        return random.randint(spec.get("min", 0), spec.get("max", 1000))
    if t == "float":
        return round(random.uniform(spec.get("min", 0.0), spec.get("max", 1000.0)), 2)
    if t == "bool":
        return faker.boolean()
    if t == "enum":
        return random.choice(spec["values"])
    if t == "name":
        return faker.name()
    if t == "phone":
        return faker.phone_number()
    if t == "id_card":
        return faker.ssn()
    if t == "email":
        return faker.email()
    if t == "uuid":
        return faker.uuid4()
    if t == "datetime":
        return faker.date_time().isoformat(sep=" ", timespec="seconds")
    if t == "date":
        return faker.date()
    # str（可带长度）
    length = spec.get("length")
    if length:
        return faker.pystr(min_chars=length, max_chars=length)
    return faker.word()


def _gen_row(fields: dict[str, Any], faker, mode: str) -> dict[str, Any]:
    row = {name: _gen_field(spec, faker) for name, spec in fields.items()}
    if mode == "dirty":
        # 随机选 1~2 个字段塞脏值
        for name in random.sample(list(row), k=min(2, len(row))):
            row[name] = random.choice(DIRTY_VALUES)
    return row


def _safe_eval(expr: str, variables: dict[str, Any]) -> Any:
    """安全求值约束表达式：只允许字面量、变量名、比较/布尔/算术运算。

    用 AST 白名单替代裸 eval，避免 `().__class__.__bases__...` 一类沙箱绕过——
    平台移植到其他项目后，约束 YAML 可能来自不完全可信的来源。
    """
    import ast
    import operator as op

    _BIN = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv,
            ast.Mod: op.mod, ast.FloorDiv: op.floordiv, ast.Pow: op.pow}
    _CMP = {ast.Eq: op.eq, ast.NotEq: op.ne, ast.Lt: op.lt, ast.LtE: op.le,
            ast.Gt: op.gt, ast.GtE: op.ge}
    _UNARY = {ast.USub: op.neg, ast.UAdd: op.pos, ast.Not: op.not_}

    def _ev(node: ast.AST) -> Any:
        if isinstance(node, ast.Expression):
            return _ev(node.body)
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            if node.id in variables:
                return variables[node.id]
            raise ValueError(f"未知变量: {node.id}")
        if isinstance(node, ast.BinOp) and type(node.op) in _BIN:
            return _BIN[type(node.op)](_ev(node.left), _ev(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
            return _UNARY[type(node.op)](_ev(node.operand))
        if isinstance(node, ast.BoolOp):
            vals = [_ev(v) for v in node.values]
            return all(vals) if isinstance(node.op, ast.And) else any(vals)
        if isinstance(node, ast.Compare):
            left = _ev(node.left)
            for o, comp in zip(node.ops, node.comparators):
                right = _ev(comp)
                if type(o) not in _CMP or not _CMP[type(o)](left, right):
                    return False
                left = right
            return True
        raise ValueError(f"不支持的表达式节点: {type(node).__name__}")

    return _ev(ast.parse(expr, mode="eval"))


def _satisfies(row: dict[str, Any], constraints: list[str]) -> bool:
    for expr in constraints:
        try:
            if not _safe_eval(expr, dict(row)):
                return False
        except Exception:
            return False
    return True


def _gen_rows(rule: dict[str, Any], count: int, faker, mode: str) -> list[dict[str, Any]]:
    fields = rule.get("fields", {})
    constraints = rule.get("constraints", []) or []
    rows = []
    for i in range(count):
        for _ in range(20):  # 约束重抽上限
            row = _gen_row(fields, faker, mode)
            if mode == "dirty" or _satisfies(row, constraints):
                break
        # 主键：未显式生成则补自增 id
        pk = rule.get("parent_key", "id")
        row.setdefault(pk, i + 1)
        rows.append(row)
    return rows


# --------------------------------------------------------------------------- #
# 输出
# --------------------------------------------------------------------------- #
def _sql_inserts(table: str, rows: list[dict[str, Any]]) -> str:
    lines = []
    for r in rows:
        cols = ", ".join(r.keys())
        vals = ", ".join("NULL" if v is None else f"'{str(v).replace(chr(39), chr(39)*2)}'" for v in r.values())
        lines.append(f"INSERT INTO {table} ({cols}) VALUES ({vals});")
    return "\n".join(lines)


def _insert_db(ctx: RunContext, rule: dict, table: str, rows: list[dict]) -> None:
    from sqlalchemy import create_engine, text
    db_name = rule.get("db")
    db = next((d for d in ctx.env_cfg.dbs if d.name == db_name), None) if db_name else (
        ctx.env_cfg.dbs[0] if ctx.env_cfg.dbs else None)
    if not db:
        raise RuntimeError(f"环境 {ctx.site}/{ctx.env} 未配置可用 DB（rule.db={db_name}）")
    engine = create_engine(db.dsn)
    with engine.begin() as conn:
        for r in rows:
            cols = ", ".join(r.keys())
            ph = ", ".join(f":{k}" for k in r.keys())
            conn.execute(text(f"INSERT INTO {table} ({cols}) VALUES ({ph})"), r)
    engine.dispose()


# --------------------------------------------------------------------------- #
# 入口
# --------------------------------------------------------------------------- #
def run_gen(ctx: RunContext, rule: str, count: int = 10, mode: str = "normal",
            template: str = "", output: str = "db") -> None:
    from faker import Faker

    if not template and not rule:
        raise ValueError("datafactory: 必须提供 --rule <规则YAML> 或 --template <模板名> 之一")

    rule_path = TEMPLATES / f"{template}.yaml" if template else Path(rule)
    if not rule_path.exists():
        raise FileNotFoundError(
            f"数据规则文件不存在: {rule_path}"
            + (f"（模板 '{template}' 未找到，检查 {TEMPLATES}）" if template else "")
        )
    spec = yaml.safe_load(rule_path.read_text(encoding="utf-8"))
    faker = Faker(spec.get("locale", "zh_CN"))

    table = spec["table"]
    count = spec.get("count", count)
    log.rule(f"数据工厂 · {table} · {mode} · ×{count}")

    parent_rows = _gen_rows(spec, count, faker, mode)
    bundle: dict[str, list[dict]] = {table: parent_rows}

    # 关联子表
    for rel in spec.get("relations", []) or []:
        child_table = rel["table"]
        fk = rel.get("fk", f"{table.rstrip('s')}_id")
        parent_key = spec.get("parent_key", "id")
        lo, hi = _parse_range(rel.get("per_parent", "1"))
        children: list[dict] = []
        cid = 1
        for p in parent_rows:
            for _ in range(random.randint(lo, hi)):
                child = _gen_row(rel.get("fields", {}), faker, mode)
                child[fk] = p[parent_key]
                child.setdefault("id", cid); cid += 1
                children.append(child)
        bundle[child_table] = children
        log.info(f"关联 {child_table}: {len(children)} 行（fk={fk}）")

    # 输出
    if output == "json":
        out = Path(ctx.platform.recordings_dir).parent / f"datafactory-{table}.json"
        out.write_text(json.dumps(bundle, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        log.ok(f"已导出 JSON：{out}")
    elif output == "sql":
        out = Path(ctx.platform.recordings_dir).parent / f"datafactory-{table}.sql"
        out.write_text("\n".join(_sql_inserts(tbl, rows) for tbl, rows in bundle.items()), encoding="utf-8")
        log.ok(f"已导出 SQL：{out}")
    else:  # db
        for tbl, rows in bundle.items():
            _insert_db(ctx, spec, tbl, rows)
            log.ok(f"已灌库 {tbl}: {len(rows)} 行")


def _parse_range(s: str | int) -> tuple[int, int]:
    if isinstance(s, int):
        return s, s
    if "-" in str(s):
        a, b = str(s).split("-", 1)
        return int(a), int(b)
    return int(s), int(s)
