"""
延迟数据分析脚本
用途: 分析opencv.py生成的日志文件，计算延迟统计并生成图表
用法: python analysis.py <日志文件路径>
"""
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import sys
import os
from datetime import datetime

# ==================== 可调整参数 ====================
# 测试视频的实际帧率（必须与生成测试视频时的fps一致）
ASSUMED_FPS = 30

# 图表使用的中文字体（Windows下通常是这些之一）
CHINESE_FONTS = ['SimHei', 'Microsoft YaHei', 'KaiTi', 'FangSong', 'Arial']
# ===================================================


def setup_chinese_font():
    """配置中文字体支持"""
    import matplotlib.font_manager as fm
    available_fonts = [f.name for f in fm.fontManager.ttflist]

    for font in CHINESE_FONTS:
        if font in available_fonts:
            plt.rcParams['font.sans-serif'] = [font, 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
            return font
    # 如果没有中文字体，使用英文标签
    return None


def parse_timestamp(ts):
    """解析各种格式的时间戳为毫秒值"""
    try:
        ts_str = str(ts).strip()
        if ':' in ts_str:
            parts = ts_str.split(':')
            if len(parts) == 3:  # HH:MM:SS 或 HH:MM:SS.ms
                h, m, s = int(parts[0]), int(parts[1]), float(parts[2])
                return h * 3600000 + m * 60000 + s * 1000
            elif len(parts) == 2:  # MM:SS
                m, s = int(parts[0]), float(parts[1])
                return m * 60000 + s * 1000
        else:
            # 纯数字，假设单位是秒
            return float(ts_str) * 1000
    except Exception:
        return None


def analyze_delay(log_file):
    """分析延迟日志文件"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始分析日志: {log_file}")

    if not os.path.exists(log_file):
        print(f"错误：文件 {log_file} 不存在")
        return None

    # 读取日志（自动尝试多种编码）
    for encoding in ['utf-8', 'gbk', 'gb2312', 'latin-1']:
        try:
            df = pd.read_csv(log_file, encoding=encoding)
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    else:
        print("错误：无法读取日志文件，请检查编码格式")
        return None

    if df.empty:
        print("错误：日志文件为空")
        return None

    print(f"读取到 {len(df)} 条记录")

    # 转换时间戳
    df['timestamp_ms'] = df['timestamp'].apply(parse_timestamp)
    valid_count_before = len(df)
    df = df.dropna(subset=['timestamp_ms'])
    valid_count_after = len(df)

    if valid_count_after == 0:
        print("错误：没有有效的时间戳数据")
        print("提示：请检查时间戳格式是否被正确解析，或调整parse_timestamp函数")
        return None

    if valid_count_after < valid_count_before:
        print(f"注意：{valid_count_before - valid_count_after} 条记录的时间戳解析失败，已跳过")

    # 计算延迟
    base_time = df['timestamp_ms'].iloc[0]
    df['delay_ms'] = df['timestamp_ms'] - base_time

    # 基于帧率计算预期时间和实际延迟
    df['expected_time'] = df['frame_number'] * (1000 / ASSUMED_FPS)
    df['actual_delay'] = df['delay_ms'] - df['expected_time']

    delays = df['actual_delay'].dropna()

    # 统计信息
    stats = {
        '数据点数': len(delays),
        '平均延迟(ms)': np.mean(delays),
        '中位数延迟(ms)': np.median(delays),
        '最小延迟(ms)': np.min(delays),
        '最大延迟(ms)': np.max(delays),
        '标准差(ms)': np.std(delays),
        '95分位延迟(ms)': np.percentile(delays, 95),
        '99分位延迟(ms)': np.percentile(delays, 99),
    }

    # 输出统计结果
    print("\n" + "=" * 50)
    print("           延迟分析统计结果")
    print("=" * 50)
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")
    print("=" * 50)

    # 生成图表
    chinese_font = setup_chinese_font()
    use_chinese = chinese_font is not None

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # 图1: 延迟随时间变化趋势
    ax1 = axes[0, 0]
    ax1.plot(df['frame_number'], df['actual_delay'], 'b-', alpha=0.7, linewidth=0.8)
    ax1.axhline(y=0, color='r', linestyle='--', alpha=0.5, label='零延迟参考线')
    ax1.set_xlabel('Frame Number' if not use_chinese else '帧号')
    ax1.set_ylabel('Delay (ms)' if not use_chinese else '延迟 (ms)')
    ax1.set_title(f'Video Delay Trend - {os.path.basename(log_file)}')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 图2: 延迟分布直方图
    ax2 = axes[0, 1]
    ax2.hist(delays, bins=50, alpha=0.7, edgecolor='black', color='steelblue')
    ax2.axvline(x=np.mean(delays), color='red', linestyle='--', linewidth=2,
                label=f'Mean: {np.mean(delays):.0f}ms')
    ax2.axvline(x=np.percentile(delays, 95), color='orange', linestyle='--', linewidth=2,
                label=f'P95: {np.percentile(delays, 95):.0f}ms')
    ax2.set_xlabel('Delay (ms)' if not use_chinese else '延迟 (ms)')
    ax2.set_ylabel('Count' if not use_chinese else '频次')
    ax2.set_title('Delay Distribution Histogram' if not use_chinese else '延迟分布直方图')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # 图3: 延迟累计分布 (CDF)
    ax3 = axes[1, 0]
    sorted_delays = np.sort(delays)
    cdf = np.arange(1, len(sorted_delays) + 1) / len(sorted_delays) * 100
    ax3.plot(sorted_delays, cdf, 'g-', linewidth=1.5)
    ax3.axvline(x=np.percentile(delays, 50), color='blue', linestyle='--', alpha=0.7,
                label=f'P50: {np.percentile(delays, 50):.0f}ms')
    ax3.axvline(x=np.percentile(delays, 95), color='orange', linestyle='--', alpha=0.7,
                label=f'P95: {np.percentile(delays, 95):.0f}ms')
    ax3.set_xlabel('Delay (ms)' if not use_chinese else '延迟 (ms)')
    ax3.set_ylabel('CDF (%)' if not use_chinese else '累积占比 (%)')
    ax3.set_title('Delay CDF' if not use_chinese else '延迟累积分布')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # 图4: 延迟区间统计
    ax4 = axes[1, 1]
    bins_labels = ['<0ms', '0-500ms', '500-1000ms', '1000-2000ms', '2000-5000ms', '>5000ms']
    bins_edges = [-np.inf, 0, 500, 1000, 2000, 5000, np.inf]
    bin_counts = []
    for i in range(len(bins_edges) - 1):
        count = np.sum((delays >= bins_edges[i]) & (delays < bins_edges[i+1]))
        bin_counts.append(count)
    colors = ['#2ecc71', '#27ae60', '#f39c12', '#e67e22', '#e74c3c', '#c0392b']
    bars = ax4.bar(bins_labels, bin_counts, color=colors, edgecolor='black', alpha=0.8)
    for bar, count in zip(bars, bin_counts):
        if count > 0:
            ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(bin_counts)*0.01,
                    str(count), ha='center', fontsize=9)
    ax4.set_ylabel('Count' if not use_chinese else '帧数')
    ax4.set_title('Delay Range Distribution' if not use_chinese else '延迟区间分布')
    plt.setp(ax4.get_xticklabels(), rotation=30, ha='right')

    plt.tight_layout()

    # 保存图表
    chart_file = os.path.splitext(log_file)[0] + '_chart.png'
    plt.savefig(chart_file, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n图表已保存: {chart_file}")

    # 保存详细结果到文本文件
    result_file = os.path.splitext(log_file)[0] + '_results.txt'
    with open(result_file, 'w', encoding='utf-8') as f:
        f.write("视频延迟测试结果\n")
        f.write("=" * 50 + "\n")
        f.write(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"源文件: {log_file}\n")
        f.write(f"假设帧率: {ASSUMED_FPS} fps\n\n")
        for key, value in stats.items():
            if isinstance(value, float):
                f.write(f"{key}: {value:.2f}\n")
            else:
                f.write(f"{key}: {value}\n")

    print(f"详细结果已保存: {result_file}")

    return stats


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python analysis.py <日志文件路径>")
        print("示例: python analysis.py recording.log")
        sys.exit(1)

    analyze_delay(sys.argv[1])
