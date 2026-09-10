"""分析完成：自动生成分享短链并回推飞书。失败不阻断主流程。"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from app.services.feishu_notify_service import (
    build_public_share_url,
    send_analysis_failure_text,
    send_analysis_success_card,
)
from app.services.report_share_service import create_or_reuse_share

logger = logging.getLogger("webapi")


async def create_share_for_task(task_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    try:
        return await create_or_reuse_share(task_id, {"id": str(user_id)})
    except Exception as exc:
        logger.warning("分析完成自动生成分享链接失败(忽略): %s", exc)
        return None


async def publish_analysis_success(
    *,
    task_id: str,
    user_id: str,
    result: Dict[str, Any],
    stock_code: str,
) -> Optional[str]:
    """生成分享链并推送飞书。返回 /s/:token，失败返回 None。"""
    share = await create_share_for_task(task_id, user_id)
    share_path = (share or {}).get("path")
    if not share_path:
        return None

    share_url = build_public_share_url(share_path)
    try:
        await send_analysis_success_card(
            stock_code=stock_code or str(result.get("stock_symbol") or ""),
            stock_name=str(result.get("stock_name") or stock_code or ""),
            recommendation=str(result.get("recommendation") or "暂无"),
            risk_level=str(result.get("risk_level") or "中等"),
            confidence_score=result.get("confidence_score", 0),
            summary=str(result.get("summary") or ""),
            share_url=share_url,
        )
    except Exception as exc:
        logger.warning("飞书分析完成回推失败(忽略): %s", exc)
    return share_path


async def publish_analysis_failure(stock_code: str, error_message: str) -> None:
    try:
        await send_analysis_failure_text(stock_code, error_message)
    except Exception as exc:
        logger.warning("飞书分析失败回推失败(忽略): %s", exc)
