"""体育试点 SLO 判定与前置检查（Batch 261 / B4-3/4/5）。

把 09 方案 §2.3 的试点完成定义做成**纯函数**，与 I/O 驱动分离：
  - 单版本"需求 → 方案" ≤ 2 小时、单版本执行（80 条）≤ 3 小时
  - 证据包完整率 **100%**（每条失败用例都有截图或请求回放）
  - 复用建议命中率 **≥50%**
  - **连续 ≥3 个版本**达标

为什么单独成服务：SLO 的算术必须可单测。真正的 3 版本数字要在有环境的机器上跑出来
（本机 Test5 不可达 → C261-1），但"什么算达标"不能等到那时才第一次被验证。
"""
from __future__ import annotations

# §2.3 阈值（改动需同步 09 方案与验收报告）
PERSON_HOURS_PER_VERSION_MAX = 2.0   # 需求 → 方案 ≤2h
EXECUTION_HOURS_PER_VERSION_MAX = 3.0  # 单版本执行 ≤3h
EVIDENCE_COMPLETENESS_MIN = 1.0      # 完整率 100%
REUSE_HIT_RATE_MIN = 0.5             # 复用命中率 ≥50%
CONSECUTIVE_VERSIONS_MIN = 3         # 连续达标版本数


def compute_slo(versions: list[dict]) -> dict:
    """按版本序列判定 SLO。

    每个版本的输入字段（缺省视为"未测"）：
      version / person_hours / execution_hours / evidence_complete(bool) /
      reuse_suggested / reuse_adopted
    """
    per_version: list[dict] = []
    for item in versions:
        person_hours = item.get("person_hours")
        execution_hours = item.get("execution_hours")
        suggested = int(item.get("reuse_suggested") or 0)
        adopted = int(item.get("reuse_adopted") or 0)
        hit_rate = round(adopted / suggested, 4) if suggested else None
        meets = {
            "plan_within_2h": person_hours is not None and person_hours <= PERSON_HOURS_PER_VERSION_MAX,
            "execution_within_3h": execution_hours is not None
            and execution_hours <= EXECUTION_HOURS_PER_VERSION_MAX,
            "evidence_complete": bool(item.get("evidence_complete")),
            # 没有建议时不能算达标（也不能算不达标）——记为 None 并由 overall 判为未达成
            "reuse_hit_rate_50pct": hit_rate is not None and hit_rate >= REUSE_HIT_RATE_MIN,
        }
        per_version.append(
            {
                "version": item.get("version") or "",
                "person_hours": person_hours,
                "execution_hours": execution_hours,
                "reuse_suggested": suggested,
                "reuse_adopted": adopted,
                "reuse_hit_rate": hit_rate,
                "meets": meets,
                "all_met": all(meets.values()),
            }
        )

    consecutive = 0
    for item in per_version:
        if item["all_met"]:
            consecutive += 1
        else:
            consecutive = 0

    total_suggested = sum(item["reuse_suggested"] for item in per_version)
    total_adopted = sum(item["reuse_adopted"] for item in per_version)
    return {
        "versions": per_version,
        "consecutive_passing": consecutive,
        "consecutive_required": CONSECUTIVE_VERSIONS_MIN,
        "overall_reuse_hit_rate": round(total_adopted / total_suggested, 4)
        if total_suggested
        else None,
        "meets_all": consecutive >= CONSECUTIVE_VERSIONS_MIN,
        "thresholds": {
            "person_hours_per_version_max": PERSON_HOURS_PER_VERSION_MAX,
            "execution_hours_per_version_max": EXECUTION_HOURS_PER_VERSION_MAX,
            "evidence_completeness_min": EVIDENCE_COMPLETENESS_MIN,
            "reuse_hit_rate_min": REUSE_HIT_RATE_MIN,
            "consecutive_versions_min": CONSECUTIVE_VERSIONS_MIN,
        },
    }


def preflight_blockers(checks: dict) -> list[str]:
    """把前置检查结果翻译成"还缺什么"的清单（空 = 可以开跑）。

    刻意返回**阻塞原因**而不是布尔：环境不可达时必须能告诉执行者具体缺哪一环，
    而不是一句"跑不了"。驱动脚本据此 fail fast。
    """
    blockers: list[str] = []
    if not checks.get("database_ok"):
        blockers.append("数据库不可用或未迁移（请先 alembic upgrade head 并确认 DATABASE_URL）")
    if not checks.get("dataset_meets_target"):
        blockers.append(
            "试点数据集不足（需接口 50 + Web 30；请先导入体育资产或用 --module-prefix 收窄范围）"
        )
    if not checks.get("fingerprint_present"):
        blockers.append("目标环境缺少环境指纹（先采集指纹，确保基线可复现）")
    if not checks.get("node_online"):
        blockers.append("没有在线执行节点（在测试人员机器上执行 cameltv-node up）")
    if not checks.get("target_reachable"):
        blockers.append(
            "被测系统不可达（Test5 需 VPN；请确认网络后重试——本脚本不会用本地替身顶替）"
        )
    if not checks.get("account_slot_configured"):
        blockers.append("未配置账号槽位（凭据只在节点侧，基线只存槽位名）")
    return blockers
