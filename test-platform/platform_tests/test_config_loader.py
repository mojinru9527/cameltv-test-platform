"""配置体系单测：v2（单项目双环境）+ v1（多站点 × 多环境兼容）+ 合并/覆盖/插值。"""
from __future__ import annotations

import os

import pytest

from core import config_loader as cl
from core.models import RunContext


# =========================================================================== #
# v2: 单项目双环境
# =========================================================================== #
class TestV2Config:
    """v2: project + environments/<env> → RunContext"""

    def test_build_context_v2_test(self):
        ctx = cl.build_context_v2("test")
        assert isinstance(ctx, RunContext)
        assert ctx.env == "test"
        assert ctx.project is not None
        assert ctx.project.name == "CamelTv"
        assert ctx.project.version == "14.0"
        assert ctx.env_cfg.proxy_strategy == "direct"
        assert ctx.env_cfg.vpn_required is False

    def test_build_context_v2_has_apis(self):
        ctx = cl.build_context_v2("test")
        assert len(ctx.apis) >= 10
        assert "ugc_list" in ctx.apis
        assert "wallet_balance" in ctx.apis

    def test_build_context_v2_ignore_paths(self):
        ctx = cl.build_context_v2("test")
        assert len(ctx.project.ignore_paths) > 0

    def test_load_project(self):
        p = cl.load_project()
        assert p.name == "CamelTv"
        assert p.version == "14.0"
        assert p.proxy_strategy == {"test": "direct", "prod": "vpn07"}
        assert p.elk.kibana_url == "https://elk.elelive.cn/app/kibana"

    def test_load_environment_test(self):
        env = cl.load_environment("test")
        assert env.name == "test"
        assert env.kind == "test"
        assert env.proxy_strategy == "direct"
        assert env.vpn_required is False

    def test_list_environments_v2(self):
        envs = cl.list_environments_v2()
        assert "test" in envs


class TestV2VPNCheck:
    """vpn07 前置校验"""

    def test_vpn_check_skipped_for_test(self):
        env = cl.load_environment("test")
        cl.vpn07_check(env)  # 不应抛异常

    def test_prod_env_has_vpn_required(self):
        env = cl.load_environment("prod")
        assert env.vpn_required is True
        assert env.proxy_strategy == "vpn07"
        assert env.proxy == ""  # TUN 模式全局路由，不设显式代理避免双路由冲突


# =========================================================================== #
# v1: 多站点多环境（兼容）
# =========================================================================== #
class TestV1BackwardCompat:

    def test_list_sites_includes_camel1_excludes_underscore(self):
        sites = cl.list_sites()
        assert "camel1" in sites
        assert "_base" not in sites
        assert "_template" not in sites

    def test_list_envs_camel1(self):
        envs = cl.list_envs("camel1")
        assert set(["prod", "test1", "test2"]).issubset(set(envs))

    def test_site_inherits_base_apis(self):
        site = cl.load_site("camel1")
        assert "ugc_list" in site.apis
        assert "pay_order" in site.apis
        assert site.apis["ugc_list"].method == "GET"
        assert site.apis["pay_order"].method == "POST"

    def test_base_ignore_merged_into_site(self):
        site = cl.load_site("camel1")
        assert any("traceId" in p for p in site.ignore_paths)
        assert site.tolerance.get("array_unordered") is True

    def test_build_context_merges_layers(self):
        ctx = cl.build_context("camel1", "prod")
        assert ctx.site == "camel1"
        assert ctx.env == "prod"
        assert len(ctx.apis) >= 10

    def test_env_var_interpolation(self, monkeypatch):
        monkeypatch.setenv("CAMEL1_TEST1_AUTH_TOKEN", "tok-123")
        cl._dotenv_loaded = True
        env = cl.load_env_v1("camel1", "test1")
        assert env.auth_token == "tok-123"

    def test_deep_merge_override_and_delete(self):
        base = {"a": {"x": 1, "y": 2}, "b": 3, "c": 4}
        override = {"a": {"y": 20, "z": 30}, "c": None}
        merged = cl._deep_merge(base, override)
        assert merged["a"] == {"x": 1, "y": 20, "z": 30}
        assert merged["b"] == 3
        assert "c" not in merged

    def test_proxy_fallback_to_platform_default(self, monkeypatch):
        monkeypatch.setenv("UPSTREAM_PROXY", "http://127.0.0.1:7890")
        cl._dotenv_loaded = True
        ctx = cl.build_context("camel1", "test2")
        assert ctx.proxy == "http://127.0.0.1:7890"
