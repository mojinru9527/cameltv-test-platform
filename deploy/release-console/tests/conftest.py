"""让测试可以直接 import 控制面模块（与既有测试的 sys.path 兜底一致）。"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
