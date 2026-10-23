"""鉴权依赖。P1.4 起管理接口统一用 require_admin。"""

from __future__ import annotations

from fastapi import Depends, HTTPException

from app.routers.auth_db import get_current_user

try:
    from tradingagents.utils.logging_manager import get_logger
except ImportError:
    import logging

    def get_logger(name: str) -> logging.Logger:
        return logging.getLogger(name)

logger = get_logger("auth_deps")


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """仅允许管理员。普通用户返回 403 FORBIDDEN。"""
    if not user.get("is_admin"):
        logger.info("admin_required_denied user=%s", user.get("username"))
        raise HTTPException(status_code=403, detail="FORBIDDEN")
    return user
