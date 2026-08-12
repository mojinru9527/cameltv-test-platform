"""Batch 161（G5）：用例端标识（surface）分类回归——16.0.0 顶层域推断。"""
from __future__ import annotations

from app.services.test_case_taxonomy import canonical_case_location, classify_case_surface


class TestClassifyCaseSurface:
    def test_api_type_always_interface(self) -> None:
        assert classify_case_surface("广告", "api") == "接口测试"

    def test_prefixed_domains_unchanged(self) -> None:
        assert classify_case_surface("用户端/首页", "manual") == "用户端"
        assert classify_case_surface("运营后台/广告管理", "manual") == "运营后台"
        assert classify_case_surface("接口测试/首页", "manual") == "接口测试"

    def test_ad_domain_frontend_modules_user(self) -> None:
        for module in ("开屏广告", "横幅广告", "贴片广告", "中场广告", "居中弹窗广告", "视频浮窗广告", "侧边栏广告", "品牌商广告", "POP Under广告", "页底悬浮广告"):
            assert classify_case_surface("广告", "manual", module) == "用户端", module

    def test_ad_domain_admin_modules_admin(self) -> None:
        for module in ("广告素材管理", "广告位配置", "广告活动基础配置", "展示方式选择", "展示区域限制", "展示权重配置", "启用时间与活动状态", "关联比赛配置", "中场广告展示时长配置"):
            assert classify_case_surface("广告", "manual", module) == "运营后台", module

    def test_top_level_16_domains(self) -> None:
        assert classify_case_surface("广告后台", "manual", "") == "运营后台"
        assert classify_case_surface("UGC", "manual", "UGC创作者管理") == "运营后台"
        assert classify_case_surface("UGC内容管理", "manual", "文章上下架") == "运营后台"
        assert classify_case_surface("UGC文章管理", "manual", "文章审核") == "运营后台"
        assert classify_case_surface("银钻系统", "manual", "每日登录任务") == "用户端"
        assert classify_case_surface("银钻预测", "manual", "实时赔率更新") == "用户端"
        assert classify_case_surface("付费活动", "manual", "付费活动") == "用户端"
        assert classify_case_surface("经济系统", "manual", "骆驼币账户") == "用户端"
        assert classify_case_surface("篮球赛事", "manual", "比赛回放调整") == "用户端"
        assert classify_case_surface("搜索", "manual", "全局搜索") == "用户端"
        assert classify_case_surface("球员", "manual", "球员详情") == "用户端"
        assert classify_case_surface("球队", "manual", "球队详情") == "用户端"
        assert classify_case_surface("联赛详情", "manual", "") == "用户端"
        assert classify_case_surface("赛事详情", "manual", "") == "用户端"
        assert classify_case_surface("资讯", "manual", "") == "用户端"
        assert classify_case_surface("运营后台", "manual", "热门比赛配置") == "运营后台"

    def test_canonical_location_uses_module(self) -> None:
        loc = canonical_case_location("广告", "广告素材管理", "manual")
        assert loc.surface == "运营后台"
        loc2 = canonical_case_location("广告", "开屏广告", "manual")
        assert loc2.surface == "用户端"
