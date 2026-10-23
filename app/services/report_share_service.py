"""分析报告分享链接：创建、复用、撤销与公开读取。"""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from bson import ObjectId

from app.core.database import get_mongo_db
from app.utils.timezone import to_config_tz

logger = logging.getLogger("webapi")

DEFAULT_EXPIRES_DAYS = 7
MAX_EXPIRES_DAYS = 365
SHARE_COLLECTION = "report_shares"
PUBLIC_NOT_FOUND = "报告不存在或链接已失效"


class ReportNotFoundError(Exception):
    """目标分析报告不存在。"""


def _to_iso(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        try:
            localized = to_config_tz(value)
            if localized is not None and hasattr(localized, "isoformat"):
                return localized.isoformat()
        except Exception:
            pass
        return value.isoformat()
    return str(value)


def _has_module_content(content: Any) -> bool:
    if content is None:
        return False
    if isinstance(content, str):
        return bool(content.strip())
    if isinstance(content, dict):
        return bool(content)
    if isinstance(content, list):
        return bool(content)
    return True


def order_report_modules(reports: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """按 MODULE_ORDER 排列模块，跳过空内容。"""
    from app.utils.report_exporter import MODULE_ORDER

    source = reports or {}
    ordered: Dict[str, Any] = {}
    used = set()
    for key in MODULE_ORDER:
        content = source.get(key)
        if _has_module_content(content):
            ordered[key] = content
            used.add(key)
    for key, content in source.items():
        if key in used:
            continue
        if _has_module_content(content):
            ordered[key] = content
    return ordered


def _collect_lookup_ids(report: Dict[str, Any], report_id: str) -> List[str]:
    ids = [report_id]
    for key in ("id", "analysis_id", "task_id"):
        value = report.get(key)
        if value:
            ids.append(str(value))
    unique: List[str] = []
    seen = set()
    for item in ids:
        if item and item not in seen:
            unique.append(item)
            seen.add(item)
    return unique


def serialize_report_from_analysis_doc(doc: Dict[str, Any], report_id: str) -> Dict[str, Any]:
    from app.routers.reports import get_stock_name

    stock_symbol = doc.get("stock_symbol", "")
    stock_name = doc.get("stock_name") or get_stock_name(stock_symbol)
    created_at = doc.get("created_at", datetime.utcnow())
    updated_at = doc.get("updated_at", created_at)
    return {
        "id": str(doc.get("_id", report_id)),
        "analysis_id": doc.get("analysis_id", ""),
        "stock_symbol": stock_symbol,
        "stock_name": stock_name,
        "model_info": doc.get("model_info", "Unknown"),
        "analysis_date": doc.get("analysis_date", ""),
        "status": doc.get("status", "completed"),
        "created_at": _to_iso(created_at),
        "updated_at": _to_iso(updated_at),
        "analysts": doc.get("analysts", []),
        "research_depth": doc.get("research_depth", 1),
        "summary": doc.get("summary", ""),
        "reports": doc.get("reports", {}) or {},
        "source": doc.get("source", "unknown"),
        "task_id": doc.get("task_id", ""),
        "recommendation": doc.get("recommendation", ""),
        "confidence_score": doc.get("confidence_score", 0.0),
        "risk_level": doc.get("risk_level", "中等"),
        "key_points": doc.get("key_points", []),
        "execution_time": doc.get("execution_time", 0),
        "tokens_used": doc.get("tokens_used", 0),
    }


def serialize_report_from_task_doc(tasks_doc: Dict[str, Any], report_id: str) -> Dict[str, Any]:
    from app.routers.reports import get_stock_name

    result = tasks_doc.get("result") or {}
    created_at = tasks_doc.get("created_at")
    updated_at = tasks_doc.get("completed_at") or created_at
    stock_symbol = result.get("stock_symbol", result.get("stock_code", tasks_doc.get("stock_code", "")))
    stock_name = result.get("stock_name") or get_stock_name(stock_symbol)
    task_id = tasks_doc.get("task_id", report_id)
    return {
        "id": task_id,
        "analysis_id": result.get("analysis_id", ""),
        "stock_symbol": stock_symbol,
        "stock_name": stock_name,
        "model_info": result.get("model_info", "Unknown"),
        "analysis_date": result.get("analysis_date", ""),
        "status": result.get("status", "completed"),
        "created_at": _to_iso(created_at),
        "updated_at": _to_iso(updated_at),
        "analysts": result.get("analysts", []),
        "research_depth": result.get("research_depth", 1),
        "summary": result.get("summary", ""),
        "reports": result.get("reports", {}) or {},
        "source": "analysis_tasks",
        "task_id": task_id,
        "recommendation": result.get("recommendation", ""),
        "confidence_score": result.get("confidence_score", 0.0),
        "risk_level": result.get("risk_level", "中等"),
        "key_points": result.get("key_points", []),
        "execution_time": result.get("execution_time", 0),
        "tokens_used": result.get("tokens_used", 0),
    }


def serialize_public_report(report: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "stock_symbol": report.get("stock_symbol", ""),
        "stock_name": report.get("stock_name", ""),
        "analysis_date": report.get("analysis_date", ""),
        "created_at": report.get("created_at", ""),
        "recommendation": report.get("recommendation", ""),
        "risk_level": report.get("risk_level", "中等"),
        "confidence_score": report.get("confidence_score", 0.0),
        "summary": report.get("summary", ""),
        "key_points": report.get("key_points") or [],
        "reports": order_report_modules(report.get("reports") or {}),
    }


def _build_report_query(report_id: str) -> Dict[str, Any]:
    ors: List[Dict[str, Any]] = [
        {"analysis_id": report_id},
        {"task_id": report_id},
    ]
    try:
        ors.append({"_id": ObjectId(report_id)})
    except Exception:
        pass
    return {"$or": ors}


async def find_serialized_report(report_id: str, db=None) -> Optional[Dict[str, Any]]:
    db = db if db is not None else get_mongo_db()
    query = _build_report_query(report_id)
    doc = await db.analysis_reports.find_one(query)
    if doc:
        return serialize_report_from_analysis_doc(doc, report_id)

    tasks_doc = await db.analysis_tasks.find_one(
        {"$or": [{"task_id": report_id}, {"result.analysis_id": report_id}]},
        {"result": 1, "task_id": 1, "stock_code": 1, "created_at": 1, "completed_at": 1},
    )
    if not tasks_doc or not tasks_doc.get("result"):
        return None
    return serialize_report_from_task_doc(tasks_doc, report_id)


async def _ensure_share_indexes(db) -> None:
    try:
        await db[SHARE_COLLECTION].create_index("token", unique=True, name="uniq_share_token")
        await db[SHARE_COLLECTION].create_index("lookup_ids", name="idx_share_lookup_ids")
        await db[SHARE_COLLECTION].create_index("expires_at", name="idx_share_expires_at")
    except Exception as exc:
        logger.debug("report_shares 索引创建跳过: %s", exc)


def _is_share_active(share: Dict[str, Any], now: Optional[datetime] = None) -> bool:
    if not share:
        return False
    if share.get("revoked_at") is not None:
        return False
    expires_at = share.get("expires_at")
    if expires_at is None:
        return False
    now = now or datetime.utcnow()
    return expires_at > now


def _share_public_meta(share: Dict[str, Any]) -> Dict[str, Any]:
    token = share.get("token", "")
    return {
        "token": token,
        "path": f"/s/{token}",
        "expires_at": _to_iso(share.get("expires_at")),
        "created_at": _to_iso(share.get("created_at")),
        "view_count": share.get("view_count", 0),
    }


async def get_active_share(report_id: str, db=None) -> Optional[Dict[str, Any]]:
    db = db if db is not None else get_mongo_db()
    report = await find_serialized_report(report_id, db=db)
    if not report:
        return None
    lookup_ids = _collect_lookup_ids(report, report_id)
    now = datetime.utcnow()
    share = await db[SHARE_COLLECTION].find_one(
        {
            "lookup_ids": {"$in": lookup_ids},
            "revoked_at": None,
            "expires_at": {"$gt": now},
        }
    )
    if not share or not _is_share_active(share, now):
        return None
    return _share_public_meta(share)


async def revoke_shares(report_id: str, db=None) -> int:
    db = db if db is not None else get_mongo_db()
    report = await find_serialized_report(report_id, db=db)
    if not report:
        return 0
    lookup_ids = _collect_lookup_ids(report, report_id)
    result = await db[SHARE_COLLECTION].update_many(
        {
            "lookup_ids": {"$in": lookup_ids},
            "revoked_at": None,
        },
        {"$set": {"revoked_at": datetime.utcnow()}},
    )
    return int(getattr(result, "modified_count", 0) or 0)


async def create_or_reuse_share(
    report_id: str,
    user: Dict[str, Any],
    expires_days: int = DEFAULT_EXPIRES_DAYS,
    regenerate: bool = False,
    db=None,
) -> Dict[str, Any]:
    db = db if db is not None else get_mongo_db()
    await _ensure_share_indexes(db)

    days = DEFAULT_EXPIRES_DAYS if expires_days is None else int(expires_days)
    if days < 1:
        days = 1
    if days > MAX_EXPIRES_DAYS:
        days = MAX_EXPIRES_DAYS

    report = await find_serialized_report(report_id, db=db)
    if not report:
        raise ReportNotFoundError("报告不存在")

    if regenerate:
        await revoke_shares(report_id, db=db)
    else:
        existing = await get_active_share(report_id, db=db)
        if existing:
            return existing

    now = datetime.utcnow()
    token = secrets.token_urlsafe(32)
    lookup_ids = _collect_lookup_ids(report, report_id)
    share_doc = {
        "token": token,
        "report_query_id": str(report.get("id") or report_id),
        "lookup_ids": lookup_ids,
        "analysis_id": report.get("analysis_id", ""),
        "task_id": report.get("task_id", ""),
        "created_by": str(user.get("id") or user.get("username") or ""),
        "created_at": now,
        "expires_at": now + timedelta(days=days),
        "revoked_at": None,
        "view_count": 0,
    }
    await db[SHARE_COLLECTION].insert_one(share_doc)
    logger.info("创建报告分享链接: report=%s user=%s days=%s", report_id, share_doc["created_by"], days)
    return _share_public_meta(share_doc)


async def get_public_report_by_token(token: str, db=None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    if not token or not token.strip():
        raise ReportNotFoundError(PUBLIC_NOT_FOUND)

    db = db if db is not None else get_mongo_db()
    share = await db[SHARE_COLLECTION].find_one({"token": token.strip()})
    now = datetime.utcnow()
    if not share or not _is_share_active(share, now):
        raise ReportNotFoundError(PUBLIC_NOT_FOUND)

    report_id = share.get("report_query_id") or ""
    report = await find_serialized_report(report_id, db=db) if report_id else None
    if not report:
        for candidate in share.get("lookup_ids") or []:
            report = await find_serialized_report(str(candidate), db=db)
            if report:
                break
    if not report:
        raise ReportNotFoundError(PUBLIC_NOT_FOUND)

    try:
        await db[SHARE_COLLECTION].update_one(
            {"token": share["token"]},
            {"$inc": {"view_count": 1}},
        )
    except Exception as exc:
        logger.debug("分享阅读计数更新失败: %s", exc)

    public_report = serialize_public_report(report)
    public_report["expires_at"] = _to_iso(share.get("expires_at"))
    return public_report, _share_public_meta(share)
