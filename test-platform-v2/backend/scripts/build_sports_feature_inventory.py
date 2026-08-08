# -*- coding: utf-8 -*-
"""体育平台功能梳理（Batch 125 / Slice 1）。

从蓝湖导出（用户端 + 运营后台）的 hierarchy.json + HTML 页面提取全量功能点清单：
  模块结构（来自 hierarchy.json） × 每页功能点（从 HTML 可见文本启发式分类）。

输出：test-platform-v2/work-logs/evidence/batch-125/sports-feature-inventory.json

功能点分类口径：
  action  —— 可执行操作（导出/新增/编辑/删除/查看/搜索/参与/下注/购买/审核 等）
  state   —— 状态枚举（预测中/待开奖/已开奖/已关闭/进行中/已结束/上架/下架 等）
  field   —— 输入/展示字段（含「请输入/请选择/：」等）
  list    —— 列表/表格列名（表头候选）
  filter  —— 筛选条件（含「状态：全部/按…筛选」等）
  entry   —— 页面入口/导航（Tab/跳转入口）
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
EXPORT_BASE = Path(r"F:\CamelTv\test-platform-v2\backend\data\lanhu-exports")
EXPORTS = [
    ("运营后台", EXPORT_BASE / "运营后台原型"),
    ("用户端", EXPORT_BASE / "用户端原型"),
]
OUT = REPO_ROOT / "test-platform-v2" / "work-logs" / "evidence" / "batch-125" / "sports-feature-inventory.json"

# 导航/通用词（跨页面重复，不作为功能点）
NOISE = {
    "重置", "搜索", "条/页", "跳至", "页", "上一页", "下一页", "操作", "导出",
    "体育直播", "Camel", "首页", "返回", "登录/注册", "全部", "登录", "注册",
    # 运营后台导航
    "内容管理", "用户管理", "财务管理", "装扮管理", "商城", "消息管理", "广告管理",
    "球队及联赛", "赛事预测", "银钻任务", "赛事视频流", "推流主播", "更新日志", "系统管理",
    "风控管理", "UGC", "活动管理", "数据统计", "奖励发放记录", "用户参与记录", "退回记录",
    "预测赛事列表", "风控设置", "任务完成记录", "邀请好友记录", "任务内容", "热门联赛",
    "热门球队", "屏蔽赛事视频", "充值记录", "骆驼币流水", "绿钻流水", "提现管理",
    "银钻流水", "充值产品管理", "用户列表", "屏蔽记录", "举报记录", "意见反馈",
    "用户账户", "资讯列表", "资讯分类", "热门搜索管理", "faq管理", "文章列表",
    "订阅记录", "文章购买记录", "创作者列表", "文章分类管理", "聊天室消息", "推送消息",
    "聊天文案白名单", "头像图片监控", "版本更新", "广告活动管理", "广告素材管理",
    "广告位管理", "广告国家管理", "广告商管理", "商品管理", "购买记录", "头像框", "勋章",
    "套餐管理", "数字货币", "活动内容(法币)", "活动内容(数字货币)", "充值赠币活动",
}

ACTION_WORDS = [
    "新增", "编辑", "删除", "查看", "导出", "导入", "搜索", "重置", "确认", "提交", "保存", "取消",
    "参与", "下注", "预测", "购买", "充值", "提现", "兑换", "关注", "取关", "点赞", "分享", "评论",
    "举报", "屏蔽", "审核", "上架", "下架", "启用", "禁用", "通过", "拒绝", "打款", "退款", "发放",
    "创建", "修改", "设置", "绑定", "解绑", "切换", "邀请", "领取", "签到", "任务", "开播", "送礼",
]

STATE_WORDS = [
    "预测中", "待开奖", "已开奖", "已关闭", "已退款", "已取消", "未开始", "进行中", "已结束",
    "未结算", "已结算", "未发放", "已发放", "待审核", "已通过", "已拒绝", "上架", "下架", "启用", "禁用",
    "待支付", "已支付", "已打款", "未打款", "成功", "失败", "正常", "异常", "封禁", "正常",
]

FIELD_MARKERS = ["请输入", "请选择", "选择", "：", ":", "账号", "手机号", "邮箱", "密码", "名称", "编号", "金额", "时间"]


def extract_lines(html_path: Path) -> list[str]:
    raw = html_path.read_text(encoding="utf-8", errors="ignore")
    raw = re.sub(r"<script.*?</script>", "", raw, flags=re.S)
    raw = re.sub(r"<style.*?</style>", "", raw, flags=re.S)
    raw = re.sub(r"<[^>]+>", "\n", raw)
    text = html.unescape(raw)
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def classify_line(line: str) -> str | None:
    if line in NOISE or len(line) < 2:
        return None
    if any(w in line for w in STATE_WORDS) and len(line) <= 20:
        return "state"
    if any(w in line for w in ACTION_WORDS) and len(line) > 4:
        return "action"
    if any(m in line for m in FIELD_MARKERS):
        return "field"
    if len(line) <= 10 and not line.isdigit():
        return "list"
    return "text"


def build_inventory() -> dict:
    result: dict = {"version": "1.0", "generated_at": "", "exports": {}}
    for label, export_dir in EXPORTS:
        hier = export_dir / "hierarchy.json"
        if not hier.exists():
            print(f"[skip] 缺 {hier}", file=sys.stderr)
            continue
        nodes = json.loads(hier.read_text(encoding="utf-8"))
        # 模块归组
        modules: dict[str, dict] = {}
        pages_total = 0
        fps_total = 0
        for n in nodes:
            if n.get("type") != "page":
                continue
            path = n.get("path", "")
            segs = [s for s in path.split("/") if s]
            module_key = "/".join(segs[:2]) if len(segs) >= 2 else label
            mod = modules.setdefault(module_key, {"name": segs[1] if len(segs) >= 2 else label, "path": module_key, "pages": []})
            pid = n.get("lanhu_page_id", "")
            html_path = export_dir / pid if pid else None
            lines = extract_lines(html_path) if html_path and html_path.exists() else []
            # 去重保序 + 分类
            seen = set()
            fps: list[dict] = []
            for ln in lines:
                if ln in seen:
                    continue
                seen.add(ln)
                cls = classify_line(ln)
                if cls and cls != "text":
                    fps.append({"type": cls, "text": ln})
            mod["pages"].append(
                {
                    "name": n.get("path", "").split("/")[-1],
                    "path": path,
                    "lanhu_page_id": pid,
                    "screenshots": n.get("screenshots") or [],
                    "text_len": sum(len(l) for l in lines),
                    "function_points": fps,
                }
            )
            pages_total += 1
            fps_total += len(fps)
        result["exports"][label] = {
            "modules": sorted(modules.values(), key=lambda m: m["path"]),
            "module_count": len(modules),
            "page_count": pages_total,
            "function_point_count": fps_total,
        }
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    inv = build_inventory()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(inv, ensure_ascii=False, indent=1), encoding="utf-8")
    for label, exp in inv["exports"].items():
        print(f"{label}: {exp['module_count']} 模块 / {exp['page_count']} 页 / {exp['function_point_count']} 功能点")
    print(f"输出 -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
