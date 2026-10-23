"""普通用户可访问的脱敏配置（P1.4）。不挂在 config.py 上，避免被路由级 admin 覆盖。"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends

from app.routers.auth_db import get_current_user
from app.services.config_service import config_service

router = APIRouter(prefix="/api/config/public", tags=["public-config"])


def _whitelist_models(llm_configs) -> List[Dict[str, Any]]:
    models: List[Dict[str, Any]] = []
    for llm in llm_configs or []:
        if not getattr(llm, "enabled", True):
            continue
        models.append(
            {
                "name": getattr(llm, "model_name", None),
                "display_name": getattr(llm, "model_display_name", None)
                or getattr(llm, "model_name", None),
                "provider": getattr(llm, "provider", None),
                "capability_level": getattr(llm, "capability_level", 2),
                "roles": list(getattr(llm, "suitable_roles", None) or ["both"]),
            }
        )
    return models


@router.get("/models")
async def public_models(_user: dict = Depends(get_current_user)):
    """只返回模型名称与能力，不含 key / base_url / secret。"""
    default_quick = None
    default_deep = None
    models: List[Dict[str, Any]] = []
    try:
        config = await config_service.get_system_config()
    except Exception:
        config = None
    if config:
        default_quick = getattr(config, "default_llm", None)
        default_deep = getattr(config, "default_llm", None)
        models = _whitelist_models(getattr(config, "llm_configs", None))
        for item in models:
            roles = item.get("roles") or []
            if default_quick is None and (
                "quick_analysis" in roles or "both" in roles
            ):
                default_quick = item.get("name")
            if default_deep is None and (
                "deep_analysis" in roles or "both" in roles
            ):
                default_deep = item.get("name")
        if models and not default_quick:
            default_quick = models[0].get("name")
        if models and not default_deep:
            default_deep = models[0].get("name")
    return {
        "success": True,
        "data": {
            "default_quick_model": default_quick,
            "default_deep_model": default_deep,
            "models": models,
        },
        "message": "ok",
    }
