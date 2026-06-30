"""
帧率流畅度分析脚本
用途: 逐帧分析录制视频中跑马灯白条的移动轨迹，检测丢帧和卡顿
用法: python frame_analysis.py <录制视频路径>
"""
import cv2
import numpy as np
import sys
import os
from datetime import datetime

# ==================== 可调整参数 ====================
# 跑马灯白条检测区域 (y_start, y_end)，应覆盖白条移动的高度范围
BAR_ROI_Y_START = 300
BAR_ROI_Y_END = 400

# 60fps下白条每帧预期移动的像素数（根据实际测试视频调整）
EXPECTED_MOVE_PER_FRAME = 4

# 静止判定阈值: 白条位置变化 < 此值 视为静止(卡顿)
STILL_THRESHOLD = 1

# 跳跃判定阈值: 白条位置变化 > 此倍数 视为跳跃(丢帧)
JUMP_THRESHOLD_MULTIPLIER = 2.5

# 进度显示间隔
PROGRESS_INTERVAL = 2000
# ===================================================


def analyze_fluency(video_path):
    """分析视频流畅度"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始分析流畅度: {video_path}")

    if not os.path.exists(video_path):
        print(f"错误：文件 {video_path} 不存在")
        return

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("错误：无法打开视频文件")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    print(f"视频信息: {width}x{height}, FPS={fps:.2f}, 总帧数={total_frames}")

    prev_bar_pos = None
    frame_num = 0
    jumps = []      # (帧号, 像素差) - 跳跃帧
    stills = []     # 帧号 - 静止帧
    positions = []  # (帧号, 位置) - 位置记录

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # 提取白条检测区域
        y_start = min(BAR_ROI_Y_START, height - 10)
        y_end = min(BAR_ROI_Y_END, height)
        roi = frame[y_start:y_end, :]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

        # 找到最亮的列 = 白条位置
        col_sums = np.sum(gray, axis=0)
        bar_pos = np.argmax(col_sums)

        # 排除全黑行的情况
        if np.max(col_sums) < 1000:
            bar_pos = prev_bar_pos if prev_bar_pos is not None else 0

        if prev_bar_pos is not None and prev_bar_pos > 0:
            diff = bar_pos - prev_bar_pos

            if abs(diff) < STILL_THRESHOLD:
                stills.append(frame_num)
            elif abs(diff) > EXPECTED_MOVE_PER_FRAME * JUMP_THRESHOLD_MULTIPLIER:
                jumps.append((frame_num, diff))

        prev_bar_pos = bar_pos
        positions.append((frame_num, bar_pos))
        frame_num += 1

        if frame_num % PROGRESS_INTERVAL == 0:
            progress = (frame_num / total_frames) * 100 if total_frames > 0 else 0
            print(f"  分析进度: {progress:.1f}% ({frame_num}帧)")

    cap.release()
    total_analyzed = frame_num

    # 计算统计
    num_stills = len(stills)
    num_jumps = len(jumps)
    num_smooth = total_analyzed - num_stills - num_jumps

    still_rate = num_stills / total_analyzed * 100 if total_analyzed > 0 else 0
    jump_rate = num_jumps / total_analyzed * 100 if total_analyzed > 0 else 0
    smooth_rate = num_smooth / total_analyzed * 100 if total_analyzed > 0 else 0

    # 计算连续卡顿段（连续静止帧组成一个卡顿事件）
    still_events = []
    if stills:
        event_start = stills[0]
        event_length = 1
        for i in range(1, len(stills)):
            if stills[i] == stills[i-1] + 1:
                event_length += 1
            else:
                still_events.append((event_start, event_length))
                event_start = stills[i]
                event_length = 1
        still_events.append((event_start, event_length))

    # 输出结果
    print("\n" + "=" * 55)
    print("             流畅度分析结果")
    print("=" * 55)
    print(f"  总帧数:        {total_analyzed}")
    print(f"  流畅帧:        {num_smooth}  ({smooth_rate:.2f}%)")
    print(f"  静止帧(卡顿):  {num_stills}  ({still_rate:.2f}%)")
    print(f"  跳跃帧(丢帧):  {num_jumps}  ({jump_rate:.2f}%)")
    print(f"  卡顿事件数:    {len(still_events)}")
    if still_events:
        durations = [e[1] for e in still_events]
        print(f"  最大卡顿时长:  {max(durations)}帧 ({max(durations)/fps*1000:.0f}ms)" if fps > 0 else f"  最大卡顿时长:  {max(durations)}帧")
        print(f"  平均卡顿时长:  {np.mean(durations):.1f}帧")
    print("=" * 55)

    # 质量评级
    if smooth_rate >= 99.5:
        quality = "优秀 - 几乎无感知卡顿"
    elif smooth_rate >= 98:
        quality = "良好 - 偶尔轻微卡顿"
    elif smooth_rate >= 95:
        quality = "合格 - 有可感知卡顿但不严重影响观看"
    else:
        quality = "不合格 - 卡顿频繁，影响观看体验"

    print(f"\n  质量评级: {quality}")

    # 保存详细结果
    result_file = os.path.splitext(video_path)[0] + '_fluency.txt'
    with open(result_file, 'w', encoding='utf-8') as f:
        f.write("帧率流畅度分析结果\n")
        f.write("=" * 55 + "\n")
        f.write(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"源文件: {video_path}\n")
        f.write(f"视频FPS: {fps:.2f}\n")
        f.write(f"总帧数: {total_analyzed}\n\n")
        f.write(f"流畅帧占比: {smooth_rate:.2f}%\n")
        f.write(f"静止帧(卡顿)占比: {still_rate:.2f}%\n")
        f.write(f"跳跃帧(丢帧)占比: {jump_rate:.2f}%\n")
        f.write(f"卡顿事件数: {len(still_events)}\n")
        f.write(f"质量评级: {quality}\n\n")
        if still_events:
            f.write("卡顿详情 (帧号, 持续帧数):\n")
            for evt in still_events[:50]:
                f.write(f"  帧{evt[0]}: {evt[1]}帧\n")
        if jumps:
            f.write("\n丢帧详情 (帧号, 偏移量):\n")
            for jmp in jumps[:50]:
                f.write(f"  帧{jmp[0]}: {jmp[1]:.0f}像素\n")

    print(f"\n详细结果已保存: {result_file}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python frame_analysis.py <录制视频路径>")
        print("示例: python frame_analysis.py recording.mp4")
        sys.exit(1)

    analyze_fluency(sys.argv[1])
