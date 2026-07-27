"""压测工具骨架（P2 — 暂缓）。

选型建议:
  - k6: 脚本化（JavaScript），CI 集成好，适合 API 压测
  - Locust: Python，分布式，Web UI 实时监控

能力规划:
  - 复用 §4 接口定义与 §4 造数能力
  - 仅打测试环境（不打正式环境）
  - 产出 HTML 报告 + 关键指标（P50/P95/P99/QPS/Error Rate）

当前状态: 骨架占位。
"""
from __future__ import annotations


def run_load_test(env: str, scenario: str = "smoke") -> dict:
    """执行压测（占位）。"""
    return {
        "status": "skipped",
        "message": f"压测暂缓（P2）。scenario={scenario}, env={env}",
    }
