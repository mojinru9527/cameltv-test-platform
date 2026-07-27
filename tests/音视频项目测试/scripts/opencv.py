"""
视频帧时间戳OCR识别脚本
用途: 从录制的直播画面中提取时间戳，生成延迟分析日志
用法: python opencv.py <视频文件路径>
"""
import cv2
import pytesseract
import os
import sys
from datetime import datetime

# ==================== 可调整参数 ====================
# 时间戳在画面中的区域 (y_start, y_end, x_start, x_end)
# 根据实际测试视频的时间戳位置调整
ROI_Y_START = 50
ROI_Y_END = 100
ROI_X_OFFSET_END = 200   # 从右边缘向左偏移
ROI_X_OFFSET_START = 50  # 从右边缘向左偏移

# 处理间隔: 每N帧处理一次（提高效率）
FRAME_INTERVAL = 10

# OCR配置
OCR_CONFIG = '--psm 7 -c tessedit_char_whitelist=0123456789:.'
# --psm 7: 单行文本识别
# --psm 6: 统一文本块
# --psm 8: 单个单词
# --psm 13: 原始文本行
# ===================================================


def process_video(video_path):
    """处理视频文件，识别时间戳并生成日志"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始处理视频: {video_path}")

    if not os.path.exists(video_path):
        print(f"错误：文件 {video_path} 不存在")
        return

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("错误：无法打开视频文件")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_sec = total_frames / fps if fps > 0 else 0
    print(f"视频信息: FPS={fps:.2f}, 总帧数={total_frames}, 时长={duration_sec:.1f}秒")

    # 生成日志文件路径
    log_file = os.path.splitext(video_path)[0] + '.log'

    frame_count = 0
    processed_count = 0
    success_count = 0

    with open(log_file, 'w', encoding='utf-8') as f:
        f.write("frame_number,timestamp,confidence\n")

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # 每FRAME_INTERVAL帧处理一次
            if frame_count % FRAME_INTERVAL == 0:
                processed_count += 1

                # 转换为灰度图
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                # 提取时间戳ROI区域
                height, width = gray.shape
                y_start = ROI_Y_START
                y_end = ROI_Y_END
                x_start = max(0, width - ROI_X_OFFSET_END)
                x_end = max(0, width - ROI_X_OFFSET_START)

                roi = gray[y_start:y_end, x_start:x_end]

                # 图像预处理增强识别率
                # 二值化
                _, roi = cv2.threshold(roi, 127, 255, cv2.THRESH_BINARY)

                try:
                    timestamp = pytesseract.image_to_string(roi, config=OCR_CONFIG)
                    timestamp = timestamp.strip()
                    if timestamp and len(timestamp) > 0:
                        f.write(f"{frame_count},{timestamp},1.0\n")
                        success_count += 1
                        if success_count <= 5 or success_count % 50 == 0:
                            print(f"  帧 {frame_count}: 识别到时间戳 [{timestamp}]")
                except Exception as e:
                    pass  # 单帧失败不影响整体

            frame_count += 1

            # 进度显示
            if frame_count % 500 == 0 and total_frames > 0:
                progress = (frame_count / total_frames) * 100
                print(f"  处理进度: {progress:.1f}% ({frame_count}/{total_frames})")

    cap.release()

    if processed_count == 0:
        print("警告：没有处理任何帧，请检查视频文件是否正常")
    else:
        recognition_rate = (success_count / processed_count) * 100
        print(f"\n处理完成!")
        print(f"  总帧数: {frame_count}")
        print(f"  处理帧数: {processed_count}")
        print(f"  成功识别: {success_count} ({recognition_rate:.1f}%)")
        print(f"  日志文件: {log_file}")

        if recognition_rate < 30:
            print("\n⚠ 识别率较低，建议:")
            print("  1. 调整ROI坐标参数 (ROI_Y_START, ROI_Y_END等)")
            print("  2. 检查时间戳字体是否足够大且清晰")
            print("  3. 尝试修改OCR_CONFIG中的--psm参数值")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python opencv.py <视频文件路径>")
        print("示例: python opencv.py recording.mp4")
        sys.exit(1)

    process_video(sys.argv[1])
