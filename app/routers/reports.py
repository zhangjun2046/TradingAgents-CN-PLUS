"""
分析报告管理API路由
"""
import os
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from .auth_db import get_current_user
from ..core.database import get_mongo_db
from ..utils.timezone import to_config_tz
from ..services.report_share_service import (
    DEFAULT_EXPIRES_DAYS,
    MAX_EXPIRES_DAYS,
    PUBLIC_NOT_FOUND,
    ReportNotFoundError,
    build_owner_filter,
    check_download_rate_limit,
    create_or_reuse_share,
    find_serialized_report,
    get_active_share,
    get_public_report_by_token,
    mask_token,
    record_share_download,
    revoke_shares,
)
import logging

logger = logging.getLogger("webapi")

# 股票名称缓存
_stock_name_cache = {}

def get_stock_name(stock_code: str) -> str:
    """
    获取股票名称
    优先级：缓存 -> MongoDB（按数据源优先级） -> 默认返回股票代码
    """
    global _stock_name_cache

    # 检查缓存
    if stock_code in _stock_name_cache:
        return _stock_name_cache[stock_code]

    try:
        # 从 MongoDB 获取股票名称
        from ..core.database import get_mongo_db_sync
        from ..core.unified_config import UnifiedConfigManager

        db = get_mongo_db_sync()
        code6 = str(stock_code).zfill(6)

        # 🔥 按数据源优先级查询
        config = UnifiedConfigManager()
        data_source_configs = config.get_data_source_configs()

        # 提取启用的数据源，按优先级排序
        enabled_sources = [
            ds.type.lower() for ds in data_source_configs
            if ds.enabled and ds.type.lower() in ['tushare', 'akshare', 'baostock']
        ]

        if not enabled_sources:
            enabled_sources = ['tushare', 'akshare', 'baostock']

        # 按数据源优先级查询
        stock_info = None
        for data_source in enabled_sources:
            stock_info = db.stock_basic_info.find_one(
                {"$or": [{"symbol": code6}, {"code": code6}], "source": data_source}
            )
            if stock_info:
                logger.debug(f"✅ 使用数据源 {data_source} 获取股票名称 {code6}")
                break

        # 如果所有数据源都没有，尝试不带 source 条件查询（兼容旧数据）
        if not stock_info:
            stock_info = db.stock_basic_info.find_one(
                {"$or": [{"symbol": code6}, {"code": code6}]}
            )
            if stock_info:
                logger.warning(f"⚠️ 使用旧数据（无 source 字段）获取股票名称 {code6}")

        if stock_info and stock_info.get("name"):
            stock_name = stock_info["name"]
            _stock_name_cache[stock_code] = stock_name
            return stock_name

        # 如果没有找到，返回股票代码
        _stock_name_cache[stock_code] = stock_code
        return stock_code

    except Exception as e:
        logger.warning(f"⚠️ 获取股票名称失败 {stock_code}: {e}")
        return stock_code


# 统一构建报告查询：支持 _id(ObjectId) / analysis_id / task_id 三种
def _build_report_query(report_id: str) -> Dict[str, Any]:
    ors = [
        {"analysis_id": report_id},
        {"task_id": report_id},
    ]
    try:
        from bson import ObjectId
        ors.append({"_id": ObjectId(report_id)})
    except Exception:
        pass
    return {"$or": ors}

async def ensure_report_access(report_id: str, user: Dict[str, Any]) -> Dict[str, Any]:
    """校验当前用户可访问该报告并返回报告文档。

    管理员可访问全部；普通用户仅限 user_id 等于自己的报告。
    不存在或不属于自己统一返回 404，避免暴露数据是否存在。
    """
    db = get_mongo_db()
    query = {**_build_report_query(report_id), **build_owner_filter(user)}
    report = await db.analysis_reports.find_one(query)
    if not report:
        logger.info(f"report_access_denied report={report_id} user={user.get('id')}")
        raise HTTPException(status_code=404, detail="报告不存在")
    return report


router = APIRouter(prefix="/api/reports", tags=["reports"])

class ReportFilter(BaseModel):
    """报告筛选参数"""
    search_keyword: Optional[str] = None
    market_filter: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    stock_code: Optional[str] = None
    report_type: Optional[str] = None

class ReportListResponse(BaseModel):
    """报告列表响应"""
    reports: List[Dict[str, Any]]
    total: int
    page: int
    page_size: int


class CreateShareRequest(BaseModel):
    """创建报告分享链接"""
    expires_days: int = Field(DEFAULT_EXPIRES_DAYS, ge=1, le=MAX_EXPIRES_DAYS)
    regenerate: bool = False

@router.get("/list", response_model=Dict[str, Any])
async def get_reports_list(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search_keyword: Optional[str] = Query(None, description="搜索关键词"),
    market_filter: Optional[str] = Query(None, description="市场筛选（A股/港股/美股）"),
    start_date: Optional[str] = Query(None, description="开始日期"),
    end_date: Optional[str] = Query(None, description="结束日期"),
    stock_code: Optional[str] = Query(None, description="股票代码"),
    user: dict = Depends(get_current_user)
):
    """获取分析报告列表"""
    try:
        logger.info(f"🔍 获取报告列表: 用户={user['id']}, 页码={page}, 每页={page_size}, 市场={market_filter}")

        db = get_mongo_db()

        # 构建查询条件（普通用户仅能看到自己的报告，管理员不限）
        query = dict(build_owner_filter(user))

        # 搜索关键词
        if search_keyword:
            query["$or"] = [
                {"stock_symbol": {"$regex": search_keyword, "$options": "i"}},
                {"analysis_id": {"$regex": search_keyword, "$options": "i"}},
                {"summary": {"$regex": search_keyword, "$options": "i"}}
            ]

        # 市场筛选
        if market_filter:
            query["market_type"] = market_filter

        # 股票代码筛选
        if stock_code:
            query["stock_symbol"] = stock_code

        # 日期范围筛选
        if start_date or end_date:
            date_query = {}
            if start_date:
                date_query["$gte"] = start_date
            if end_date:
                date_query["$lte"] = end_date
            query["analysis_date"] = date_query

        logger.info(f"📊 查询条件: {query}")

        # 计算总数
        total = await db.analysis_reports.count_documents(query)

        # 分页查询
        skip = (page - 1) * page_size
        cursor = db.analysis_reports.find(query).sort("created_at", -1).skip(skip).limit(page_size)

        reports = []
        async for doc in cursor:
            # 转换为前端需要的格式
            stock_code = doc.get("stock_symbol", "")
            # 🔥 优先使用MongoDB中保存的股票名称，如果没有则查询
            stock_name = doc.get("stock_name")
            if not stock_name:
                stock_name = get_stock_name(stock_code)

            # 🔥 获取市场类型，如果没有则根据股票代码推断
            market_type = doc.get("market_type")
            if not market_type:
                from tradingagents.utils.stock_utils import StockUtils
                market_info = StockUtils.get_market_info(stock_code)
                market_type_map = {
                    "china_a": "A股",
                    "hong_kong": "港股",
                    "us": "美股",
                    "unknown": "A股"
                }
                market_type = market_type_map.get(market_info.get("market", "unknown"), "A股")

            # 获取创建时间（数据库中是 UTC 时间，需要转换为 UTC+8）
            created_at = doc.get("created_at", datetime.utcnow())
            created_at_tz = to_config_tz(created_at)  # 转换为 UTC+8 并添加时区信息

            report = {
                "id": str(doc["_id"]),
                "analysis_id": doc.get("analysis_id", ""),
                "title": f"{stock_name}({stock_code}) 分析报告",
                "stock_code": stock_code,
                "stock_name": stock_name,
                "market_type": market_type,  # 🔥 添加市场类型字段
                "model_info": doc.get("model_info", "Unknown"),  # 🔥 添加模型信息字段
                "type": "single",  # 目前主要是单股分析
                "format": "markdown",  # 主要格式
                "status": doc.get("status", "completed"),
                "created_at": created_at_tz.isoformat() if created_at_tz else str(created_at),
                "analysis_date": doc.get("analysis_date", ""),
                "analysts": doc.get("analysts", []),
                "research_depth": doc.get("research_depth", 1),
                "summary": doc.get("summary", ""),
                "file_size": len(str(doc.get("reports", {}))),  # 估算大小
                "source": doc.get("source", "unknown"),
                "task_id": doc.get("task_id", "")
            }
            reports.append(report)

        logger.info(f"✅ 查询完成: 总数={total}, 返回={len(reports)}")

        return {
            "success": True,
            "data": {
                "reports": reports,
                "total": total,
                "page": page,
                "page_size": page_size
            },
            "message": "报告列表获取成功"
        }

    except Exception as e:
        logger.error(f"❌ 获取报告列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/share/{token}")
async def get_shared_report(token: str):
    """凭分享 token 读取公开报告（无需登录）"""
    try:
        report, _meta = await get_public_report_by_token(token)
        return {
            "success": True,
            "data": report,
            "message": "报告获取成功"
        }
    except ReportNotFoundError:
        raise HTTPException(status_code=404, detail=PUBLIC_NOT_FOUND)
    except Exception as e:
        logger.error(f"❌ 获取公开分享报告失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


_SHARE_EXPORT_FORMATS = {
    "markdown": ("md", "text/markdown; charset=utf-8"),
    "pdf": ("pdf", "application/pdf"),
    "docx": ("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
}


def _build_share_download_headers(report: Dict[str, Any], ext: str) -> Dict[str, str]:
    """构造 Content-Disposition：{股票代码}_{日期}_HunterAgent.{ext}，filename* 使用 UTF-8 编码。"""
    from urllib.parse import quote
    import re

    def _safe(text: str) -> str:
        return re.sub(r'[\\/:*?"<>|\s]+', "-", str(text or "")).strip("-")

    symbol = _safe(report.get("stock_symbol")) or "report"
    date_text = _safe(report.get("analysis_date")) or _safe(str(report.get("created_at", ""))[:10]) \
        or datetime.now().strftime("%Y-%m-%d")
    filename = f"{symbol}_{date_text}_HunterAgent.{ext}"
    ascii_name = filename.encode("ascii", "ignore").decode() or f"report.{ext}"
    return {
        "Content-Disposition": f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{quote(filename)}'
    }


@router.get("/share/{token}/download")
async def download_shared_report(
    token: str,
    format: str = Query("markdown", description="导出格式: markdown, pdf, docx"),
):
    """凭分享 token 免登录导出报告（内容与公开页一致，不含内部字段）"""
    from starlette.concurrency import run_in_threadpool
    from app.utils.report_exporter import report_exporter

    fmt = (format or "").lower()
    if fmt not in _SHARE_EXPORT_FORMATS:
        raise HTTPException(status_code=400, detail=f"不支持的下载格式: {format}")

    # 先限流再查库，避免被刷时仍打到数据库
    if not await check_download_rate_limit(token):
        logger.info("share_download_rate_limited token=%s format=%s", mask_token(token), fmt)
        raise HTTPException(status_code=429, detail="下载过于频繁，请稍后再试")

    try:
        report, _meta = await get_public_report_by_token(token)
    except ReportNotFoundError:
        raise HTTPException(status_code=404, detail=PUBLIC_NOT_FOUND)
    except Exception as e:
        logger.error(f"❌ 分享导出读取报告失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    if fmt == "pdf" and not report_exporter.pdf_available:
        raise HTTPException(status_code=400, detail="PDF 导出功能不可用。")
    if fmt == "docx" and not report_exporter.docx_available:
        raise HTTPException(status_code=400, detail="Word 导出功能不可用。")

    try:
        if fmt == "markdown":
            content = (await run_in_threadpool(report_exporter.generate_markdown_report, report)).encode("utf-8")
        elif fmt == "pdf":
            content = await run_in_threadpool(report_exporter.generate_pdf_report, report)
        else:
            content = await run_in_threadpool(report_exporter.generate_docx_report, report)
    except Exception as e:
        logger.error(f"❌ 分享导出生成失败 format={fmt}: {e}")
        raise HTTPException(status_code=500, detail=f"文档生成失败: {str(e)}")

    await record_share_download(token.strip())
    logger.info("share_download token=%s format=%s", mask_token(token), fmt)
    ext, media_type = _SHARE_EXPORT_FORMATS[fmt]
    return Response(content=content, media_type=media_type, headers=_build_share_download_headers(report, ext))


@router.post("/{report_id}/share")
async def create_report_share(
    report_id: str,
    payload: Optional[CreateShareRequest] = None,
    user: dict = Depends(get_current_user)
):
    """创建或复用报告分享链接"""
    body = payload or CreateShareRequest()
    try:
        data = await create_or_reuse_share(
            report_id,
            user,
            expires_days=body.expires_days,
            regenerate=body.regenerate,
        )  # create_or_reuse_share 内部按 user 做归属校验
        return {
            "success": True,
            "data": data,
            "message": "分享链接已生成" if body.regenerate else "分享链接已就绪"
        }
    except ReportNotFoundError:
        raise HTTPException(status_code=404, detail="报告不存在")
    except Exception as e:
        logger.error(f"❌ 创建报告分享失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{report_id}/share")
async def get_report_share(
    report_id: str,
    user: dict = Depends(get_current_user)
):
    """查询当前有效的分享链接"""
    try:
        report = await find_serialized_report(report_id, user=user)
        if not report:
            raise HTTPException(status_code=404, detail="报告不存在")
        data = await get_active_share(report_id, user=user)
        return {
            "success": True,
            "data": data,
            "message": "已有有效分享链接" if data else "暂无有效分享链接"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 查询报告分享失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{report_id}/share")
async def delete_report_share(
    report_id: str,
    user: dict = Depends(get_current_user)
):
    """撤销该报告全部有效分享链接"""
    try:
        report = await find_serialized_report(report_id, user=user)
        if not report:
            raise HTTPException(status_code=404, detail="报告不存在")
        count = await revoke_shares(report_id, user=user)
        return {
            "success": True,
            "data": {"revoked": count},
            "message": "分享链接已撤销"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 撤销报告分享失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{report_id}/detail")
async def get_report_detail(
    report_id: str,
    user: dict = Depends(get_current_user)
):
    """获取报告详情"""
    try:
        logger.info(f"🔍 获取报告详情: {report_id}")
        report = await find_serialized_report(report_id, user=user)
        if not report:
            raise HTTPException(status_code=404, detail="报告不存在")

        return {
            "success": True,
            "data": report,
            "message": "报告详情获取成功"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取报告详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{report_id}/content/{module}")
async def get_report_module_content(
    report_id: str,
    module: str,
    user: dict = Depends(get_current_user)
):
    """获取报告特定模块的内容"""
    try:
        logger.info(f"🔍 获取报告模块内容: {report_id}/{module}")

        # 查询报告（支持多种ID）并校验归属
        doc = await ensure_report_access(report_id, user)

        reports = doc.get("reports", {})

        if module not in reports:
            raise HTTPException(status_code=404, detail=f"模块 {module} 不存在")

        content = reports[module]

        return {
            "success": True,
            "data": {
                "module": module,
                "content": content,
                "content_type": "markdown" if isinstance(content, str) else "json"
            },
            "message": "模块内容获取成功"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取报告模块内容失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{report_id}")
async def delete_report(
    report_id: str,
    user: dict = Depends(get_current_user)
):
    """删除报告"""
    try:
        logger.info(f"🗑️ 删除报告: {report_id}")

        db = get_mongo_db()

        # 先校验归属，再按文档主键删除（避免条件歧义误删他人报告）
        doc = await ensure_report_access(report_id, user)
        result = await db.analysis_reports.delete_one({"_id": doc["_id"]})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="报告不存在")

        logger.info(f"✅ 报告删除成功: {report_id}")

        return {
            "success": True,
            "message": "报告删除成功"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 删除报告失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{report_id}/download")
async def download_report(
    report_id: str,
    format: str = Query("markdown", description="下载格式: markdown, json, pdf, docx"),
    user: dict = Depends(get_current_user)
):
    """下载报告

    支持的格式:
    - markdown: Markdown 格式（默认）
    - json: JSON 格式（包含完整数据）
    - docx: Word 文档格式（pandoc 或 python-docx）
    - pdf: PDF 格式（WeasyPrint、pdfkit 或 fpdf2）
    """
    try:
        logger.info(f"📥 下载报告: {report_id}, 格式: {format}")

        # 查询报告（支持多种ID）并校验归属
        doc = await ensure_report_access(report_id, user)

        stock_symbol = doc.get("stock_symbol", "unknown")
        analysis_date = doc.get("analysis_date", datetime.now().strftime("%Y-%m-%d"))

        if format == "json":
            # JSON格式下载
            content = json.dumps(doc, ensure_ascii=False, indent=2, default=str)
            filename = f"{stock_symbol}_{analysis_date}_report.json"
            media_type = "application/json"

            # 返回文件流
            def generate():
                yield content.encode('utf-8')

            return StreamingResponse(
                generate(),
                media_type=media_type,
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )

        elif format == "markdown":
            from app.utils.report_exporter import report_exporter

            content = report_exporter.generate_markdown_report(doc)
            filename = f"{stock_symbol}_{analysis_date}_report.md"
            media_type = "text/markdown"

            def generate():
                yield content.encode('utf-8')

            return StreamingResponse(
                generate(),
                media_type=media_type,
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )

        elif format == "docx":
            from app.utils.report_exporter import report_exporter

            if not report_exporter.docx_available:
                raise HTTPException(
                    status_code=400,
                    detail="Word 导出功能不可用。请安装 python-docx，或安装 pandoc + pypandoc。"
                )

            try:
                docx_content = report_exporter.generate_docx_report(doc)
                filename = f"{stock_symbol}_{analysis_date}_report.docx"

                def generate():
                    yield docx_content

                return StreamingResponse(
                    generate(),
                    media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={"Content-Disposition": f"attachment; filename={filename}"}
                )
            except Exception as e:
                logger.error(f"❌ Word 文档生成失败: {e}")
                raise HTTPException(status_code=500, detail=f"Word 文档生成失败: {str(e)}")

        elif format == "pdf":
            from app.utils.report_exporter import report_exporter

            if not report_exporter.pdf_available:
                raise HTTPException(
                    status_code=400,
                    detail="PDF 导出功能不可用。请安装 fpdf2（pip install fpdf2），或安装 WeasyPrint / pdfkit 与 wkhtmltopdf。"
                )

            try:
                pdf_content = report_exporter.generate_pdf_report(doc)
                filename = f"{stock_symbol}_{analysis_date}_report.pdf"

                def generate():
                    yield pdf_content

                return StreamingResponse(
                    generate(),
                    media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename={filename}"}
                )
            except Exception as e:
                logger.error(f"❌ PDF 文档生成失败: {e}")
                raise HTTPException(status_code=500, detail=f"PDF 文档生成失败: {str(e)}")

        else:
            raise HTTPException(status_code=400, detail=f"不支持的下载格式: {format}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 下载报告失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
