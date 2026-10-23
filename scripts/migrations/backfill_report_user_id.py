"""
历史报告 user_id 回填（P1.5，tech_solution 7.4）

规则：
- 候选报告：analysis_reports 中 user_id 不存在或为 null 的记录；
- 通过 task_id 关联 analysis_tasks（找不到时按 result.analysis_id 反查）；
- 取 task.user_id（兼容旧字段 user），统一以字符串写入；
- 找不到归属的：user_id=null 且 owner_unknown=true（仅管理员可见）；
- 已存在但类型为 ObjectId 的 user_id 规整为字符串；
- 幂等：重复执行不会改变已回填的数据；owner_unknown 的记录每次会重新尝试关联。

用法：
    python scripts/migrations/backfill_report_user_id.py --dry-run
    python scripts/migrations/backfill_report_user_id.py
"""
import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger("backfill_report_user_id")

# 需要处理的报告：user_id 缺失 / 为 null，或仍是非字符串（如 ObjectId）
_MISSING_USER_ID = {"$or": [{"user_id": {"$exists": False}}, {"user_id": None}]}


def _owner_of(task_doc: Optional[Dict[str, Any]]) -> Optional[str]:
    """从任务记录取归属用户（字符串），取不到返回 None。"""
    if not task_doc:
        return None
    owner = task_doc.get("user_id", task_doc.get("user"))
    if owner is None or not str(owner).strip():
        return None
    return str(owner)


async def _find_task(db, report: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """按 task_id 关联任务；找不到再按 result.analysis_id 反查。"""
    task_id = report.get("task_id")
    if task_id:
        task = await db.analysis_tasks.find_one({"task_id": task_id})
        if task:
            return task
    analysis_id = report.get("analysis_id")
    if analysis_id:
        return await db.analysis_tasks.find_one({"result.analysis_id": analysis_id})
    return None


async def run_backfill(db, dry_run: bool = False) -> Dict[str, int]:
    """执行回填，返回统计。db 可注入（便于测试）。

    统计字段：
    - total：待处理的报告总数（user_id 缺失 / null）
    - filled：成功回填 user_id 的数量
    - unknown：无法回填（标记 owner_unknown）的数量
    - normalized：user_id 非字符串被规整为字符串的数量
    """
    stats = {"total": 0, "filled": 0, "unknown": 0, "normalized": 0}

    # 1. 缺失 / null 的报告
    candidates = []
    async for report in db.analysis_reports.find(_MISSING_USER_ID):
        candidates.append(report)

    stats["total"] = len(candidates)
    for report in candidates:
        owner = _owner_of(await _find_task(db, report))
        if owner is not None:
            stats["filled"] += 1
            update = {"$set": {"user_id": owner}, "$unset": {"owner_unknown": ""}}
        else:
            stats["unknown"] += 1
            update = {"$set": {"user_id": None, "owner_unknown": True}}
        if not dry_run:
            await db.analysis_reports.update_one({"_id": report["_id"]}, update)

    # 2. 已有 user_id 但不是字符串（ObjectId 等）的报告，规整为字符串
    async for report in db.analysis_reports.find({"user_id": {"$exists": True, "$ne": None}}):
        value = report.get("user_id")
        if isinstance(value, str):
            continue
        stats["normalized"] += 1
        if not dry_run:
            await db.analysis_reports.update_one(
                {"_id": report["_id"]}, {"$set": {"user_id": str(value)}}
            )

    return stats


def _print_stats(stats: Dict[str, int], dry_run: bool) -> None:
    mode = "DRY-RUN（未写库）" if dry_run else "正式执行"
    logger.info("=" * 60)
    logger.info(f"回填结果 - {mode}")
    logger.info(f"  总数（待处理）: {stats['total']}")
    logger.info(f"  回填成功:       {stats['filled']}")
    logger.info(f"  无法回填:       {stats['unknown']}（仅管理员可见）")
    logger.info(f"  类型规整:       {stats['normalized']}")
    logger.info("=" * 60)


async def main(dry_run: bool) -> Dict[str, int]:
    from motor.motor_asyncio import AsyncIOMotorClient
    from app.core.config import get_settings

    settings = get_settings()
    client = AsyncIOMotorClient(settings.MONGO_URI)
    try:
        db = client[settings.MONGO_DB]
        logger.info(f"目标数据库: {settings.MONGO_DB}，dry_run={dry_run}")
        stats = await run_backfill(db, dry_run=dry_run)
        _print_stats(stats, dry_run)
        return stats
    finally:
        client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="回填 analysis_reports.user_id")
    parser.add_argument("--dry-run", action="store_true", help="只统计，不写库")
    args = parser.parse_args()
    asyncio.run(main(args.dry_run))
