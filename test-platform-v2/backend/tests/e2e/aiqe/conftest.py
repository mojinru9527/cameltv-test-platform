"""V16-017 平台链路 E2E 结果采集 hook（仅注册 sessionfinish，逻辑见 platform_results.py）。"""
from platform_results import pytest_sessionfinish

__all__ = ["pytest_sessionfinish"]
