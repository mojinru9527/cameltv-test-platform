"""音视频质量检查器骨架（P2 — 阈值待定）。

能力规划:
  - run_av_checklist(env) → 读取检查表，按项执行检测
  - ffprobe 探测: 视频编码/分辨率/帧率/码率
  - 播放采集: playwright 打开播放页 → 录制 → 逐帧分析
  - 弱网模拟: Chrome DevTools Protocol CDP 控制网络条件

当前状态: 骨架占位，待阈值确认后实现。
"""
from __future__ import annotations

from core.models import RunContext


def run_av_checklist(ctx: RunContext) -> dict:
    """按检查表执行音视频质量检测（占位）。"""
    return {
        "status": "skipped",
        "message": "音视频检查器待阈值确认后实现（P2）。检查表见 tests/音视频测试/checklist-功能检查表.md",
        "env": ctx.env,
    }
