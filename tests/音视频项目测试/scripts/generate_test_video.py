r"""
测试视频生成脚本
用途: 使用Python+OpenCV生成高精度时间戳测试视频和帧率跑马灯测试视频
用法: python generate_test_video.py
输出: 项目目录\materials\high_precision_timestamp.mp4
      项目目录\materials\fluency_test_pattern.mp4
"""
import cv2
import numpy as np
import os
from datetime import datetime

# ==================== 可调整参数 ====================
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'materials')

# 时间戳测试视频参数
TIMESTAMP_WIDTH = 1280
TIMESTAMP_HEIGHT = 720
TIMESTAMP_FPS = 30
TIMESTAMP_DURATION = 300  # 秒

# 帧率测试视频参数
FLUENCY_WIDTH = 1280
FLUENCY_HEIGHT = 720
FLUENCY_FPS = 60
FLUENCY_DURATION = 600  # 秒

# 颜色定义 (BGR)
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_GREEN = (0, 255, 0)
COLOR_RED = (255, 100, 100)
COLOR_GRAY = (128, 128, 128)
COLOR_DARK_GRAY = (200, 200, 200)
COLOR_YELLOW = (200, 255, 100)
COLOR_BLUE = (255, 200, 100)
COLOR_LIGHT_BLUE = (200, 255, 100)
# ===================================================


def generate_timestamp_video():
    """生成高精度时间戳测试视频"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 生成时间戳测试视频...")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    total_frames = TIMESTAMP_FPS * TIMESTAMP_DURATION
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video_path = os.path.join(OUTPUT_DIR, 'high_precision_timestamp.mp4')
    out = cv2.VideoWriter(video_path, fourcc, TIMESTAMP_FPS,
                          (TIMESTAMP_WIDTH, TIMESTAMP_HEIGHT))

    if not out.isOpened():
        print(f"错误：无法创建视频文件 {video_path}")
        return None

    for frame_num in range(total_frames):
        # 黑色背景
        frame = np.zeros((TIMESTAMP_HEIGHT, TIMESTAMP_WIDTH, 3), dtype=np.uint8)

        # 当前时间（毫秒）
        current_time_ms = (frame_num / TIMESTAMP_FPS) * 1000

        # 绘制信息文字
        texts = [
            (f"TIMESTAMP: {current_time_ms:.1f}ms", (50, 100), 1.5, COLOR_WHITE),
            (f"FRAME: {frame_num}", (50, 160), 1.0, COLOR_YELLOW),
            (f"TIME: {int(frame_num//TIMESTAMP_FPS//60):02d}:{int((frame_num//TIMESTAMP_FPS)%60):02d}.{int((frame_num % TIMESTAMP_FPS) * (1000/TIMESTAMP_FPS)):03d}",
             (50, 220), 0.8, COLOR_LIGHT_BLUE),
            ("TEST PATTERN - VIDEO DELAY MEASUREMENT", (50, 50), 1.2, COLOR_BLUE),
        ]
        for text, pos, size, color in texts:
            cv2.putText(frame, text, pos, cv2.FONT_HERSHEY_SIMPLEX, size, color, 2)

        # 绘制移动标记（绿色圆球，从左到右循环移动）
        moving_x = int((frame_num * 2) % (TIMESTAMP_WIDTH - 200) + 100)
        cv2.circle(frame, (moving_x, 500), 30, COLOR_GREEN, -1)
        cv2.putText(frame, "MOVING MARKER", (moving_x - 80, 550),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLOR_GREEN, 2)

        # 绘制数字时钟（每100ms更新）
        if frame_num % 3 == 0:  # 30fps下每3帧≈100ms
            clock_digit = int((current_time_ms // 100) % 10)
            cv2.putText(frame, f"CLOCK: {clock_digit}", (TIMESTAMP_WIDTH - 250, 100),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, COLOR_RED, 2)

        # 绘制网格线（辅助视觉检测）
        for x in range(0, TIMESTAMP_WIDTH, 160):
            cv2.line(frame, (x, 0), (x, TIMESTAMP_HEIGHT), (50, 50, 50), 1)
        for y in range(0, TIMESTAMP_HEIGHT, 90):
            cv2.line(frame, (0, y), (TIMESTAMP_WIDTH, y), (50, 50, 50), 1)

        out.write(frame)

        if frame_num % 300 == 0:
            progress = (frame_num / total_frames) * 100
            print(f"  生成进度: {progress:.1f}%")

    out.release()

    file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
    print(f"时间戳测试视频生成完成!")
    print(f"  文件: {video_path}")
    print(f"  大小: {file_size_mb:.1f}MB")
    print(f"  时长: {TIMESTAMP_DURATION}秒, 帧率: {TIMESTAMP_FPS}fps")
    return video_path


def generate_fluency_test_video():
    """生成帧率跑马灯测试视频"""
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 生成帧率跑马灯测试视频...")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 60fps下白条每帧移动4像素
    move_per_frame = 4

    total_frames = FLUENCY_FPS * FLUENCY_DURATION
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video_path = os.path.join(OUTPUT_DIR, 'fluency_test_pattern.mp4')
    out = cv2.VideoWriter(video_path, fourcc, FLUENCY_FPS,
                          (FLUENCY_WIDTH, FLUENCY_HEIGHT))

    if not out.isOpened():
        print(f"错误：无法创建视频文件 {video_path}")
        return None

    for frame_num in range(total_frames):
        # 灰色背景
        frame = np.ones((FLUENCY_HEIGHT, FLUENCY_WIDTH, 3), dtype=np.uint8) * 128

        # 绘制跑马灯白条（从左到右循环移动）
        bar_pos = int((frame_num * move_per_frame) % (FLUENCY_WIDTH + 200) - 100)
        cv2.rectangle(frame, (bar_pos, 300), (bar_pos + 100, 400), COLOR_WHITE, -1)

        # 绘制帧率测试信息
        info_texts = [
            (f"FLUENCY TEST PATTERN - {FLUENCY_FPS}FPS", (50, 100), 0.8),
            (f"Frame: {frame_num}", (50, 140), 0.7),
            (f"Time: {int(frame_num//FLUENCY_FPS//60):02d}:{int((frame_num//FLUENCY_FPS)%60):02d}",
             (50, 180), 0.7),
            ("White bar should move smoothly - any jump = frame drop", (50, 220), 0.6),
        ]
        for text, pos, size in info_texts:
            cv2.putText(frame, text, pos, cv2.FONT_HERSHEY_SIMPLEX, size, COLOR_BLACK, 2)

        # 绘制网格（辅助视觉检测卡顿）
        for x in range(0, FLUENCY_WIDTH, 50):
            cv2.line(frame, (x, 0), (x, FLUENCY_HEIGHT), COLOR_DARK_GRAY, 1)
        for y in range(0, FLUENCY_HEIGHT, 50):
            cv2.line(frame, (0, y), (FLUENCY_WIDTH, y), COLOR_DARK_GRAY, 1)

        out.write(frame)

        if frame_num % 600 == 0:
            progress = (frame_num / total_frames) * 100
            print(f"  生成进度: {progress:.1f}%")

    out.release()

    file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
    print(f"帧率跑马灯测试视频生成完成!")
    print(f"  文件: {video_path}")
    print(f"  大小: {file_size_mb:.1f}MB")
    print(f"  时长: {FLUENCY_DURATION}秒, 帧率: {FLUENCY_FPS}fps")
    return video_path


if __name__ == "__main__":
    print("=" * 55)
    print("       测试视频生成工具")
    print("=" * 55)
    print(f"输出目录: {OUTPUT_DIR}")
    print(f"时间戳视频: {TIMESTAMP_FPS}fps, {TIMESTAMP_DURATION}秒")
    print(f"跑马灯视频: {FLUENCY_FPS}fps, {FLUENCY_DURATION}秒")
    print()

    generate_timestamp_video()
    generate_fluency_test_video()

    print(f"\n所有测试视频已生成到: {OUTPUT_DIR}")
