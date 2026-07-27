"""GET /api/config  — 项目配置与环境列表。"""
from fastapi import APIRouter

from core import config_loader as cl

router = APIRouter(tags=["config"])


@router.get("/config")
def get_config():
    project = cl.load_project()
    return {
        "project": project.name,
        "version": project.version,
        "description": project.description,
        "environments": cl.list_environments_v2(),
        "proxy_strategy": project.proxy_strategy,
        "elk": {
            "kibana_url": project.elk.kibana_url,
        },
    }


@router.get("/config/{env}")
def get_config_env(env: str):
    ctx = cl.build_context_v2(env)
    return {
        "project": ctx.project.name if ctx.project else "",
        "env": ctx.env,
        "base_url": ctx.base_url,
        "proxy": ctx.proxy or "(none)",
        "proxy_strategy": ctx.env_cfg.proxy_strategy,
        "vpn_required": ctx.env_cfg.vpn_required,
        "api_count": len(ctx.apis),
        "deps": {
            "dbs": [d.name for d in ctx.env_cfg.dbs],
            "redis": [r.name for r in ctx.env_cfg.redis],
            "mqs": [m.name for m in ctx.env_cfg.mqs],
            "https": [h.name for h in ctx.env_cfg.https],
        },
    }
