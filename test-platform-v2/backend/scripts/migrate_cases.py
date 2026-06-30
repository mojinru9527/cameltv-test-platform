"""旧库 901 条用例 → v2 新库迁移脚本。

用法：cd backend && python scripts/migrate_cases.py

功能：
1. 从旧库 test-platform/data/platform.db 读取 901 条 test_cases
2. 按 tags / api_spec_ref 自动拆分为 功能用例 / 接口用例
3. 应用 module → (domain, module) 映射表归入分类
4. 写入 v2 新库 test_case 表
5. 输出统计报告
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime

# ── 路径设置 ──────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OLD_DB = os.path.join(PROJECT_ROOT, "..", "..", "test-platform", "data", "platform.db")
NEW_DB_URL = os.environ.get("DATABASE_URL", "sqlite:///./data/platform.db")

if not os.path.exists(OLD_DB):
    print(f"[ERROR] 旧库不存在: {OLD_DB}")
    print("请确认 test-platform/data/platform.db 文件存在")
    sys.exit(1)

# ── 模块 → (域, 模块) 映射表 ──────────────────────────

# 功能用例映射：old_module → (domain, module)
FUNC_MODULE_MAP: dict[str, tuple[str, str]] = {
    # ═══ 用户端 ═══
    "首页": ("用户端", "首页推荐"),
    "推荐模块": ("用户端", "首页推荐"),
    "其他推荐": ("用户端", "首页推荐"),
    "横幅广告": ("用户端", "首页推荐"),
    "分类TAB": ("用户端", "首页推荐"),
    "Home": ("用户端", "首页推荐"),

    "注册登录": ("用户端", "注册登录"),
    "Auth": ("用户端", "注册登录"),
    "登录": ("用户端", "注册登录"),

    "资讯": ("用户端", "资讯文章"),
    "文章列表": ("用户端", "资讯文章"),
    "文章详情": ("用户端", "资讯文章"),
    "文章内容": ("用户端", "资讯文章"),
    "文章标题": ("用户端", "资讯文章"),

    "直播": ("用户端", "直播赛事"),
    "赛事视频流": ("用户端", "直播赛事"),
    "推流主播": ("用户端", "直播赛事"),

    "赛事详情": ("用户端", "赛事详情"),
    "赛程": ("用户端", "赛事详情"),
    "联赛/球队": ("用户端", "赛事详情"),
    "热门球队": ("用户端", "赛事详情"),
    "热门联赛": ("用户端", "赛事详情"),
    "球员": ("用户端", "赛事详情"),
    "近30场战绩": ("用户端", "赛事详情"),
    "近期战绩": ("用户端", "赛事详情"),
    "关联比赛": ("用户端", "赛事详情"),

    "预测": ("用户端", "预测竞猜"),
    "预测项": ("用户端", "预测竞猜"),
    "预测结果": ("用户端", "预测竞猜"),

    "个人中心": ("用户端", "个人中心"),
    "我已解锁": ("用户端", "个人中心"),
    "记录入口": ("用户端", "个人中心"),
    "作者信息": ("用户端", "个人中心"),
    "作者统计": ("用户端", "个人中心"),

    "首单退币": ("用户端", "支付充值"),
    "充值赠送": ("用户端", "支付充值"),
    "充值赠币": ("用户端", "支付充值"),
    "充值到账": ("用户端", "支付充值"),
    "继续支付": ("用户端", "支付充值"),
    "选择币种": ("用户端", "支付充值"),
    "套餐列表": ("用户端", "支付充值"),
    "创建订单": ("用户端", "支付充值"),
    "支付方式": ("用户端", "支付充值"),
    "支付类型": ("用户端", "支付充值"),

    "骆驼币财务": ("用户端", "钱包财务"),
    "银钻": ("用户端", "钱包财务"),
    "绿钻流水": ("用户端", "钱包财务"),
    "银钻流水": ("用户端", "钱包财务"),
    "数字货币": ("用户端", "钱包财务"),
    "余额": ("用户端", "钱包财务"),
    "流水": ("用户端", "钱包财务"),

    "Follow": ("用户端", "社交关注"),
    "关注": ("用户端", "社交关注"),
    "取关": ("用户端", "社交关注"),

    "聊天室": ("用户端", "聊天室"),
    "聊天室消息": ("用户端", "聊天室"),

    "搜索": ("用户端", "搜索"),
    "热门搜索": ("用户端", "搜索"),

    "商城": ("用户端", "商城"),
    "商品管理": ("用户端", "商城"),

    "勋章": ("用户端", "勋章头像框"),
    "头像框": ("用户端", "勋章头像框"),

    "推送": ("用户端", "推送"),
    "推送消息": ("用户端", "推送"),

    "广告": ("用户端", "广告活动"),
    "Ads": ("用户端", "广告活动"),
    "活动提示": ("用户端", "广告活动"),

    "FAQ": ("用户端", "FAQ帮助"),

    "版本更新": ("用户端", "版本权限"),
    "权限安全": ("用户端", "版本权限"),
    "账户冻结": ("用户端", "版本权限"),
    "异常处理": ("用户端", "版本权限"),

    "解锁文章": ("用户端", "解锁订阅"),
    "解锁按钮": ("用户端", "解锁订阅"),
    "解锁方式": ("用户端", "解锁订阅"),
    "订阅按钮": ("用户端", "解锁订阅"),
    "玩法类型": ("用户端", "解锁订阅"),
    "Streak": ("用户端", "解锁订阅"),
    "有资格+单篇+Loss": ("用户端", "解锁订阅"),
    "有资格+单篇+Win": ("用户端", "解锁订阅"),
    "无资格+单篇+Loss": ("用户端", "解锁订阅"),
    "有资格+订阅+Loss": ("用户端", "解锁订阅"),
    "发布时间": ("用户端", "解锁订阅"),

    "APP端": ("用户端", "APP端基础"),
    "V": ("用户端", "APP端基础"),
    "I": ("用户端", "APP端基础"),
    "PV": ("用户端", "APP端基础"),

    # ═══ 运营后台 ═══
    "资讯管理": ("运营后台", "资讯管理"),
    "用户管理": ("运营后台", "用户管理"),
    "用户反馈": ("运营后台", "用户管理"),
    "预测管理": ("运营后台", "预测管理"),
    "UGC管理": ("运营后台", "UGC管理"),
    "广告管理": ("运营后台", "广告管理"),
    "Banner管理": ("运营后台", "广告管理"),
    "FAQ管理": ("运营后台", "FAQ管理"),
    "翻译管理": ("运营后台", "翻译管理"),
    "屏蔽记录": ("运营后台", "内容审核"),
    "举报记录": ("运营后台", "内容审核"),
    "任务管理": ("运营后台", "任务管理"),
    "任务记录": ("运营后台", "任务管理"),

    # 特殊处理（运营后台的也可能有这些模块名字的接口用例）
    "(详见源文件)": ("运营后台", "其他"),
}

# 接口用例映射
API_MODULE_MAP: dict[str, tuple[str, str]] = {
    "Auth": ("接口测试", "Auth"),
    "Ads": ("接口测试", "Ads"),
    "Client": ("接口测试", "Client"),
    "Sports": ("接口测试", "Sports"),
    "资讯管理": ("接口测试", "资讯管理"),
    "用户管理": ("接口测试", "用户管理"),
    "预测管理": ("接口测试", "预测管理"),
    "直播": ("接口测试", "直播"),
    "赛事详情": ("接口测试", "赛事详情"),
    "文章列表": ("接口测试", "文章列表"),
    "文章详情": ("接口测试", "文章详情"),
    "解锁文章": ("接口测试", "解锁文章"),
    "创建订单": ("接口测试", "创建订单"),
    "套餐列表": ("接口测试", "套餐列表"),
    "骆驼币财务": ("接口测试", "骆驼币财务"),
    "退币": ("接口测试", "退币"),
    "关注": ("接口测试", "关注取关"),
    "取关": ("接口测试", "关注取关"),
    "推荐模块": ("接口测试", "推荐模块"),
    "余额": ("接口测试", "余额流水"),
    "流水": ("接口测试", "余额流水"),
    "资格查询": ("接口测试", "资格查询"),
    "热门球队": ("接口测试", "热门球队"),
    "热门联赛": ("接口测试", "热门联赛"),
}


def parse_api_info(title: str, steps_str: str) -> tuple[str, str]:
    """从用例标题/步骤中提取 HTTP 方法和端点。"""
    method, endpoint = "", ""

    # 标题格式1: "POST /account-service/ee/ads/activity/get"
    m = re.match(r"^(GET|POST|PUT|DELETE|PATCH)\s+(/\S+)", title, re.IGNORECASE)
    if m:
        return m.group(1).upper(), m.group(2)

    # 标题格式2: "[API-TC-XXX-001] GET /api/admin/news/list — ..."
    m = re.match(r"^\[API-TC-[^\]]+\]\s*(GET|POST|PUT|DELETE|PATCH)\s+(/\S+)", title, re.IGNORECASE)
    if m:
        return m.group(1).upper(), m.group(2)

    # Steps 中查找
    try:
        steps = json.loads(steps_str) if isinstance(steps_str, str) else steps_str
        for s in steps:
            desc = s.get("desc", "")
            m2 = re.search(r"(GET|POST|PUT|DELETE|PATCH)\s+(/\S+)", desc, re.IGNORECASE)
            if m2:
                return m2.group(1).upper(), m2.group(2)
    except (json.JSONDecodeError, TypeError):
        pass

    return method, endpoint


def extract_case_id(title: str, api_spec_ref: str) -> str:
    """提取全局唯一用例编号。"""
    # 格式1: [TC-ADMIN-NEWS-001] 资讯列表...
    m = re.match(r"^\[(TC-[\w-]+)\]", title)
    if m:
        return m.group(1)

    # 格式2: [API-TC-ADMIN-NEWS-001] GET /api/...
    m = re.match(r"^\[(API-TC-[\w-]+)\]", title)
    if m:
        return m.group(1)

    # 格式3: 从 api_spec_ref 提取
    # functional:ADMIN-运营后台-全版本:TC-ADMIN-NEWS-001
    if api_spec_ref:
        parts = api_spec_ref.split(":")
        if len(parts) >= 3 and parts[2].startswith("TC-"):
            return parts[2]

    return ""


def is_api_case(row: dict) -> bool:
    """判断是否为接口用例。"""
    if row['type'] == 'api':
        return True
    tags = json.loads(row['tags'] or '[]')
    if 'swagger' in tags or 'auto-generated' in tags:
        return True
    ref = row['api_spec_ref'] or ''
    if ref.startswith('generated:') or ref.startswith('api-spec:'):
        return True
    return False


def classify(row: dict) -> tuple[str, str]:
    """根据 old module + tags + spec_ref 确定 (domain, module)。"""
    old_module = row['module'].strip()
    if not old_module:
        old_module = "其他"

    if is_api_case(row):
        if old_module in API_MODULE_MAP:
            return API_MODULE_MAP[old_module]
        # 兜底：尝试功能映射但在接口测试域
        if old_module in FUNC_MODULE_MAP:
            dom, mod = FUNC_MODULE_MAP[old_module]
            return ("接口测试", mod)
        return ("接口测试", old_module)
    else:
        if old_module in FUNC_MODULE_MAP:
            return FUNC_MODULE_MAP[old_module]
        # 兜底
        return ("其他", old_module)

    # 从 tags 中判断端侧
    tags = json.loads(row['tags'] or '[]')
    if '运营后台' in tags:
        domain_base = '运营后台'
    elif '用户端' in tags:
        domain_base = '用户端'
    else:
        domain_base = '其他'

    if old_module in FUNC_MODULE_MAP:
        return FUNC_MODULE_MAP[old_module]

    return (domain_base, old_module)


def migrate():
    # ── 连接旧库 ──
    old_conn = sqlite3.connect(OLD_DB)
    old_conn.text_factory = lambda x: x.decode('utf-8', errors='replace')
    old_cur = old_conn.cursor()

    old_cur.execute("SELECT * FROM test_cases ORDER BY id")
    cols = [d[0] for d in old_cur.description]
    old_rows = [dict(zip(cols, r)) for r in old_cur.fetchall()]
    old_conn.close()
    print(f"[1/4] 从旧库读取 {len(old_rows)} 条用例")

    # ── 分类 + 映射 ──
    api_cases = []
    func_cases = []
    for r in old_rows:
        if is_api_case(r):
            api_cases.append(r)
        else:
            func_cases.append(r)
    print(f"[2/4] 拆分: 接口用例 {len(api_cases)} / 功能用例 {len(func_cases)}")

    # ── 转换 ──
    new_rows = []
    for r in old_rows:
        domain, module = classify(r)
        case_id = extract_case_id(r['title'], r['api_spec_ref'] or '')
        api_method, api_endpoint = parse_api_info(r['title'], r['steps'])

        # 解析 tags
        tags_raw = r['tags'] or '[]'
        if isinstance(tags_raw, str):
            try:
                tags = json.loads(tags_raw)
            except (json.JSONDecodeError, TypeError):
                tags = [tags_raw] if tags_raw else []
        else:
            tags = tags_raw

        new_rows.append({
            "project_id": 1,  # 默认 cameltv 项目
            "case_id": case_id,
            "title": r['title'] or '',
            "domain": domain,
            "module": module,
            "case_type": r['type'] or 'manual',
            "priority": r['priority'] or 'P2',
            "status": r['status'] or 'active',
            "tags": json.dumps(tags, ensure_ascii=False) if tags else '[]',
            "preconditions": r['preconditions'] or '',
            "steps": r['steps'] if isinstance(r['steps'], str) else json.dumps(r['steps'], ensure_ascii=False),
            "expected_result": r['expected_result'] or '',
            "api_method": api_method,
            "api_endpoint": api_endpoint,
            "api_spec_ref": r['api_spec_ref'] or '',
            "source": "migration",
            "old_id": r['id'],
            "created_at": r['created_at'] or datetime.now().isoformat(),
            "updated_at": r['updated_at'] or datetime.now().isoformat(),
        })

    # ── 写入新库 ──
    # 解析新库路径
    db_file = NEW_DB_URL.replace("sqlite:///", "", 1)
    db_file = os.path.join(PROJECT_ROOT, db_file) if not os.path.isabs(db_file) else db_file
    os.makedirs(os.path.dirname(db_file), exist_ok=True)

    new_conn = sqlite3.connect(db_file)
    new_cur = new_conn.cursor()

    # 确保表存在
    new_cur.execute("""
        CREATE TABLE IF NOT EXISTS test_case (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL DEFAULT 0,
            case_id VARCHAR(100) NOT NULL DEFAULT '',
            title VARCHAR(500) NOT NULL DEFAULT '',
            domain VARCHAR(50) NOT NULL DEFAULT '',
            module VARCHAR(100) NOT NULL DEFAULT '',
            case_type VARCHAR(20) NOT NULL DEFAULT 'manual',
            priority VARCHAR(4) NOT NULL DEFAULT 'P2',
            status VARCHAR(20) NOT NULL DEFAULT 'active',
            tags TEXT NOT NULL DEFAULT '[]',
            preconditions TEXT NOT NULL DEFAULT '',
            steps TEXT NOT NULL DEFAULT '[]',
            expected_result TEXT NOT NULL DEFAULT '',
            api_method VARCHAR(10) NOT NULL DEFAULT '',
            api_endpoint VARCHAR(500) NOT NULL DEFAULT '',
            api_spec_ref VARCHAR(300) NOT NULL DEFAULT '',
            source VARCHAR(30) NOT NULL DEFAULT 'migration',
            old_id INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 清空旧迁移数据
    new_cur.execute("DELETE FROM test_case WHERE source = 'migration'")

    # 批量插入
    cols_insert = [
        "project_id", "case_id", "title", "domain", "module", "case_type",
        "priority", "status", "tags", "preconditions", "steps", "expected_result",
        "api_method", "api_endpoint", "api_spec_ref", "source", "old_id",
        "created_at", "updated_at",
    ]
    placeholders = ", ".join(["?" for _ in cols_insert])
    insert_sql = f"INSERT INTO test_case ({', '.join(cols_insert)}) VALUES ({placeholders})"

    count = 0
    for r in new_rows:
        try:
            vals = tuple(r.get(c, "") for c in cols_insert)
            new_cur.execute(insert_sql, vals)
            count += 1
        except Exception as e:
            print(f"  [WARN] 插入失败 old_id={r['old_id']}: {e}")

    new_conn.commit()
    print(f"[3/4] 写入新库 {count} 条")

    # ── 统计 ──
    print("\n[4/4] 迁移统计:")
    print(f"  总用例数: {count}")

    # 按域统计
    domain_stats = defaultdict(lambda: {"total": 0, "api": 0, "func": 0})
    for r in new_rows:
        d = r['domain']
        domain_stats[d]["total"] += 1
        if r['case_type'] == 'api':
            domain_stats[d]["api"] += 1
        else:
            domain_stats[d]["func"] += 1

    for domain, stats in sorted(domain_stats.items()):
        print(f"\n  {domain} ({stats['total']}条)")
        # 按模块统计
        mod_stats = defaultdict(int)
        for r in new_rows:
            if r['domain'] == domain:
                mod_stats[r['module']] += 1
        for mod, cnt in sorted(mod_stats.items(), key=lambda x: -x[1]):
            print(f"    {mod}: {cnt}")

    # 验证
    new_cur.execute("SELECT COUNT(*) FROM test_case WHERE source = 'migration'")
    final_count = new_cur.fetchone()[0]
    print(f"\n  [OK] New DB migration records: {final_count}")
    print(f"  [OK] API cases: {len(api_cases)} / Functional cases: {len(func_cases)}")

    new_conn.close()
    print("\nMigration complete!")


if __name__ == "__main__":
    migrate()
