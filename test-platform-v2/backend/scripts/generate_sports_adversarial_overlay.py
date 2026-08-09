# -*- coding: utf-8 -*-
"""Generate deterministic recovery and repeat/concurrency cases for Batch 130."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
INVENTORY = (
    REPO_ROOT
    / "test-platform-v2/work-logs/evidence/batch-125/sports-feature-inventory.json"
)
OUT = (
    REPO_ROOT
    / "test-platform-v2/work-logs/evidence/batch-130-case-module-quality/adversarial-case-overlay.json"
)

# Each entry names a real user/administrator action and its observable business
# invariant.  The generated cases share a reviewable structure without reducing
# every module to generic "open page / page opens" assertions.
MODULE_PROFILES: dict[str, tuple[str, str, str]] = {
    "运营后台/UGC": ("审核并上架文章", "文章状态、审核记录和上架记录各只有一份", "UGC 内容服务"),
    "运营后台/内容管理": ("保存内容配置", "配置版本只递增一次且前台读取同一版本", "内容配置服务"),
    "运营后台/商城": ("创建并上架商品", "商品、库存和上架记录保持一致且各只有一份", "商品/库存服务"),
    "运营后台/广告管理": ("保存广告投放", "广告时段不重叠且投放记录只有一份", "广告投放服务"),
    "运营后台/推流主播": ("绑定主播推流配置", "主播与推流地址保持唯一绑定", "推流配置服务"),
    "运营后台/更新日志": ("发布更新日志", "同一版本日志只发布一次", "更新日志服务"),
    "运营后台/活动管理": ("创建并发布活动", "活动状态与参与规则为同一有效版本", "活动服务"),
    "运营后台/消息管理": ("创建并发送站内消息", "目标用户只收到一条消息且发送统计准确", "消息发送服务"),
    "运营后台/球队及联赛": ("保存球队与联赛关联", "球队、联赛及赛季关联无孤立或重复记录", "赛事资料服务"),
    "运营后台/用户管理": ("调整用户状态或权限", "用户最终状态唯一且审计记录完整", "用户权限服务"),
    "运营后台/系统管理": ("保存系统参数", "参数版本唯一且所有读取节点最终一致", "系统配置服务"),
    "运营后台/装扮管理": ("创建并上架装扮", "装扮、售价和上架状态一致且只有一份", "装扮服务"),
    "运营后台/财务管理": ("审核一笔财务单据", "单据状态、余额和账本流水原子一致", "账本服务"),
    "运营后台/赛事视频流": ("保存赛事视频流", "赛事只绑定一条生效视频流且播放源一致", "视频流服务"),
    "运营后台/赛事预测": ("发布预测并执行结算", "预测状态、用户收益和奖励流水原子一致", "预测结算服务"),
    "运营后台/银钻任务": ("发布银钻任务", "任务版本与奖励规则唯一且一致", "任务奖励服务"),
    "运营后台/风控管理": ("启用风控规则", "规则状态唯一且命中审计可追溯", "风控规则服务"),
    "用户端/FAQ帮助": ("搜索并打开 FAQ", "结果不重复且故障恢复后内容版本一致", "FAQ 搜索服务"),
    "用户端/UGC": ("发布一条 UGC 内容", "内容、媒体附件和发布记录各只有一份", "UGC 发布服务"),
    "用户端/个人中心": ("保存个人资料", "资料版本只更新一次且重新登录后仍一致", "用户资料服务"),
    "用户端/付费活动": ("购买并参与付费活动", "扣款、参与资格和订单原子一致", "活动订单服务"),
    "用户端/启动登录": ("登录并建立会话", "只生成一个有效会话且失败不会残留半登录态", "认证服务"),
    "用户端/商城": ("提交商品兑换订单", "库存、余额和订单原子一致且订单唯一", "商城订单服务"),
    "用户端/回放": ("打开并续播赛事回放", "播放进度不倒退且播放会话不重复", "回放服务"),
    "用户端/搜索": ("提交跨模块搜索", "结果去重、顺序稳定且旧请求不覆盖新请求", "聚合搜索服务"),
    "用户端/球员": ("关注球员并查看详情", "关注关系唯一且详情数据版本一致", "球员资料服务"),
    "用户端/球队": ("关注球队并查看详情", "关注关系唯一且球队数据版本一致", "球队资料服务"),
    "用户端/直播": ("进入直播并恢复播放", "只有一个有效播放会话且恢复点正确", "直播播放服务"),
    "用户端/聊天弹幕": ("发送一条聊天弹幕", "消息仅展示和落库一次且顺序可追溯", "聊天消息服务"),
    "用户端/联赛": ("关注联赛并切换赛季", "关注关系唯一且赛季数据不串联", "联赛资料服务"),
    "用户端/装扮": ("购买并启用装扮", "扣款、持有记录和启用状态原子一致", "装扮订单服务"),
    "用户端/资讯": ("刷新并打开资讯", "列表不重复且旧响应不覆盖最新内容", "资讯聚合服务"),
    "用户端/赛事详情": ("刷新赛事详情并切换数据页签", "比分、事件和统计属于同一赛事版本", "赛事详情服务"),
    "用户端/通用": ("执行全局分享或跳转", "目标路由唯一且失败不产生错误业务状态", "通用路由服务"),
    "用户端/钱包财务": ("提交充值或提现", "余额、订单和账本流水原子一致且订单唯一", "支付账本服务"),
    "用户端/银钻任务": ("领取银钻任务奖励", "奖励只到账一次且任务状态同步完成", "任务奖励服务"),
    "用户端/预测Pick": ("提交一笔赛事预测", "投入、预测记录和可用余额原子一致且记录唯一", "预测服务"),
    "用户端/首页": ("刷新首页聚合内容", "卡片不重复且各区块保持同一数据版本", "首页聚合服务"),
}


def load_inventory_modules() -> list[str]:
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    return [
        f"{surface}/{module['name']}"
        for surface, export in inventory["exports"].items()
        for module in export["modules"]
    ]


def _case_id(module: str, category: str) -> str:
    digest = hashlib.sha256(f"{module}|{category}".encode("utf-8")).hexdigest()[:12].upper()
    return f"SP-B130-{digest}"


def _recovery_case(module: str, action: str, invariant: str, dependency: str) -> dict:
    surface, domain = module.split("/", 1)
    return {
        "case_id": _case_id(module, "recovery"),
        "title": f"{domain}-{dependency}超时后可恢复且不产生脏数据",
        "domain": module,
        "module": "异常恢复",
        "case_type": "manual",
        "priority": "P1",
        "case_design_method": "故障注入+场景法",
        "positive_negative": "negative",
        "adversarial_category": "recovery",
        "test_data_note": f"准备可执行“{action}”的数据，并可将{dependency}切换为超时/HTTP 5xx 后恢复",
        "preconditions": f"{surface}账号已具备目标权限；已记录操作前业务快照；{dependency}可注入一次超时或 HTTP 5xx",
        "steps": [
            {"step": 1, "desc": f"记录操作前数据，注入{dependency}超时或 HTTP 5xx", "expected": f"故障仅作用于本次请求；操作前基线可用于核对“{invariant}”"},
            {"step": 2, "desc": f"执行“{action}”并等待错误反馈", "expected": "10 秒内结束等待，展示可理解且可重试的错误；页面仍可操作；不写入半成品、重复记录或错误状态"},
            {"step": 3, "desc": f"解除故障后只重试一次“{action}”，再从页面与数据库/审计记录复核", "expected": f"重试成功；{invariant}；不存在首次失败遗留的脏数据"},
        ],
        "expected_result": f"首次异常被明确拦截且业务快照不变；故障解除后可重试成功；{invariant}。",
        "tags": ["功能用例", "对抗性", "异常", "恢复性", "故障注入"],
        "source_doc": "Batch 130 全模块对抗性审查",
    }


def _repeat_case(module: str, action: str, invariant: str, dependency: str) -> dict:
    surface, domain = module.split("/", 1)
    return {
        "case_id": _case_id(module, "repeat_concurrency"),
        "title": f"{domain}-{action}重复点击与并发提交保持幂等",
        "domain": module,
        "module": "重复与并发",
        "case_type": "manual",
        "priority": "P1",
        "case_design_method": "并发场景法+错误推测",
        "positive_negative": "negative",
        "adversarial_category": "repeat_concurrency",
        "test_data_note": "同一账号、同一业务对象；双击间隔小于 100ms，并准备两个并发客户端使用同一幂等业务参数",
        "preconditions": f"{surface}账号已具备目标权限；已记录操作前业务快照；{dependency}正常可用",
        "steps": [
            {"step": 1, "desc": f"在同一页面对“{action}”按钮连续双击，间隔小于 100ms", "expected": "首次提交后按钮立即禁用或后续请求复用同一幂等键；无重复成功提示"},
            {"step": 2, "desc": "再由两个客户端在同一时刻提交完全相同的业务请求", "expected": "最多一个请求执行业务变更；另一请求返回同一结果或明确的重复操作提示，不出现 500"},
            {"step": 3, "desc": "刷新页面，并核对数据库业务记录、关联记录、余额/库存及审计日志", "expected": f"{invariant}；没有双扣、重复发放、重复展示或孤立关联数据"},
        ],
        "expected_result": f"双击与并发提交最终只生效一次；{invariant}；页面与持久化结果均仅一次。",
        "tags": ["功能用例", "对抗性", "异常", "幂等", "并发"],
        "source_doc": "Batch 130 全模块对抗性审查",
    }


def build_overlay(modules: list[str]) -> dict[str, list[dict]]:
    missing = sorted(set(modules) - MODULE_PROFILES.keys())
    extra = sorted(MODULE_PROFILES.keys() - set(modules))
    if missing or extra:
        raise ValueError(f"模块画像与清单不一致: missing={missing}, extra={extra}")
    return {
        module: [
            _recovery_case(module, *MODULE_PROFILES[module]),
            _repeat_case(module, *MODULE_PROFILES[module]),
        ]
        for module in modules
    }


def main() -> int:
    modules = load_inventory_modules()
    overlay = build_overlay(modules)
    payload = {
        "summary": {
            "module_count": len(modules),
            "case_count": sum(len(cases) for cases in overlay.values()),
            "categories": ["recovery", "repeat_concurrency"],
        },
        "modules": [
            {"module": module, "cases": cases}
            for module, cases in overlay.items()
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"生成 {payload['summary']['case_count']} 条对抗性用例 -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
