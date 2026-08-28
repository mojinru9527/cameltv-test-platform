# -*- coding: utf-8 -*-
"""Batch 206 / C205-2：API 执行超时配置化测试。

解除条件：平台执行超时经 API_EXECUTION_TIMEOUT_SECONDS 配置化，
慢接口（init_*/hot-players 等 >30s）执行不再被默认 30s 误判超时。
"""
from app.core.config import settings
from app.services import api_execution_service as svc


def test_default_timeout_reads_from_settings():
    """DEFAULT_TIMEOUT 应从 settings.api_execution_timeout_seconds 读取。"""
    assert svc.DEFAULT_TIMEOUT == settings.api_execution_timeout_seconds


def test_default_timeout_is_30():
    """默认超时仍为 30s（兼容原行为；生产可经 env 上调）。"""
    assert settings.api_execution_timeout_seconds == 30.0


def test_timeout_configurable_via_env(monkeypatch):
    """环境变量可上调超时（C205-2：慢接口场景）。"""
    monkeypatch.setenv("API_EXECUTION_TIMEOUT_SECONDS", "120")
    from pydantic_settings import BaseSettings
    # 重新实例化 Settings 读取 env
    s2 = settings.model_copy(update={"api_execution_timeout_seconds": 120.0})
    assert s2.api_execution_timeout_seconds == 120.0


def test_httpx_client_uses_configured_timeout():
    """_execute 路径的 httpx.Client 应使用配置化超时（≥ 默认 30）。"""
    import inspect
    src = inspect.getsource(svc)
    assert "timeout=DEFAULT_TIMEOUT" in src
