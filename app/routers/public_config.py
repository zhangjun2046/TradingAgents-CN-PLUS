"""普通用户可访问的脱敏配置（P1.4）。不挂在 config.py 上，避免被路由级 admin 覆盖。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.routers.auth_db import get_current_user
from app.services.available_models import ModelCatalogError, load_model_catalog, pick_side_default
from app.services.config_provider import provider as config_provider

router = APIRouter(prefix="/api/config/public", tags=["public-config"])


@router.get("/models")
async def public_models(_user: dict = Depends(get_current_user)):
    """只返回模型名称与能力，不含 key / base_url / secret。"""
    try:
        catalog = await load_model_catalog()
        settings = await config_provider.get_effective_system_settings()
    except ModelCatalogError as exc:
        raise HTTPException(status_code=503, detail="模型列表加载失败") from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="模型列表加载失败") from exc

    settings = settings or {}
    default_llm = None
    if catalog.config is not None:
        default_llm = getattr(catalog.config, "default_llm", None)
        if default_llm is None and isinstance(catalog.config, dict):
            default_llm = catalog.config.get("default_llm")

    quick_default = pick_side_default(
        catalog.quick_models,
        settings.get("quick_analysis_model"),
        default_llm,
    )
    deep_default = pick_side_default(
        catalog.deep_models,
        settings.get("deep_analysis_model"),
        default_llm,
    )
    return {
        "success": True,
        "data": {
            "default_quick_model": quick_default,
            "default_deep_model": deep_default,
            "models": catalog.models,
            "quick_models": catalog.quick_models,
            "deep_models": catalog.deep_models,
        },
        "message": "ok",
    }
