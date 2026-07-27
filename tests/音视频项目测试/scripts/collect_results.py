"""
测试结果汇总脚本
用途: 遍历所有测试结果目录，提取延迟统计并汇总为CSV报告
用法: python collect_results.py [结果根目录，默认项目目录/results]
"""
import os
import glob
import csv
import sys
from datetime import datetime


def collect_results(results_dir=None):
    """收集并汇总所有测试结果"""
    if results_dir is None:
        results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'results')

    if not os.path.exists(results_dir):
        print(f"错误：目录 {results_dir} 不存在")
        return

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(results_dir, f"汇总报告_{timestamp}.csv")

    # 收集所有 *_results.txt 文件
    result_files = []
    for root, dirs, files in os.walk(results_dir):
        for f in files:
            if f.endswith('_results.txt'):
                result_files.append(os.path.join(root, f))

    if not result_files:
        print("未找到任何测试结果文件 (*_results.txt)")
        print(f"搜索目录: {results_dir}")
        return

    print(f"找到 {len(result_files)} 个测试结果文件")

    all_results = []

    for rf in sorted(result_files):
        test_dir = os.path.dirname(rf)
        test_name = os.path.basename(test_dir)

        result = {
            '测试名称': test_name,
            '结果文件路径': rf,
            '文件夹路径': test_dir,
        }

        try:
            with open(rf, 'r', encoding='utf-8') as fh:
                content = fh.read()

            for line in content.split('\n'):
                line = line.strip()
                if ':' in line and not line.startswith('='):
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    if key and value:
                        result[key] = value
        except Exception as e:
            result['解析状态'] = f'失败: {e}'

        all_results.append(result)

    if not all_results:
        print("无有效结果可汇总")
        return

    # 收集所有不重复的列名
    all_keys = set()
    for r in all_results:
        all_keys.update(r.keys())

    # 排序：重要字段在前
    priority_keys = ['测试名称', '平均延迟(ms)', '最大延迟(ms)', '95分位延迟(ms)',
                     '标准差(ms)', '中位数延迟(ms)', '数据点数', '质量评级',
                     '流畅帧占比', '卡顿事件数']
    ordered_keys = [k for k in priority_keys if k in all_keys]
    remaining = sorted(all_keys - set(ordered_keys))
    fieldnames = ordered_keys + remaining

    # 写入CSV（UTF-8 BOM确保Excel正确打开中文）
    with open(output_file, 'w', newline='', encoding='utf-8-sig') as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for r in all_results:
            writer.writerow(r)

    print(f"\n汇总报告已保存: {output_file}")
    print(f"共汇总 {len(all_results)} 条测试记录")
    print(f"包含 {len(fieldnames)} 个字段")

    # 简要统计
    delay_keys = ['平均延迟(ms)']
    for dk in delay_keys:
        values = []
        for r in all_results:
            if dk in r:
                try:
                    values.append(float(r[dk]))
                except (ValueError, TypeError):
                    pass
        if values:
            print(f"\n{dk}:")
            print(f"  最小值: {min(values):.1f}")
            print(f"  最大值: {max(values):.1f}")
            print(f"  平均值: {sum(values)/len(values):.1f}")


if __name__ == "__main__":
    results_dir = sys.argv[1] if len(sys.argv) > 1 else None
    collect_results(results_dir)
