#!/usr/bin/env python3
"""将 users.email 唯一索引改为仅约束有值邮箱（部分索引）。

现有 docker 初始化脚本创建的 email 唯一索引不是 sparse/partial，
多个不写 email 的手机号用户会因「空邮箱」互相冲突。

运行方式：
    python scripts/migrations/fix_users_email_index.py --dry-run
    python scripts/migrations/fix_users_email_index.py
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Iterable, List, Tuple

from pymongo import ASCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.errors import OperationFailure

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import get_settings  # noqa: E402

logger = logging.getLogger(__name__)

PARTIAL_INDEX_NAME = "uniq_email_partial"
PARTIAL_FILTER = {"email": {"$type": "string"}}


def _index_keys(index_info: dict) -> Tuple:
    return tuple(index_info.get("key", {}).items())


def find_email_unique_indexes(indexes: Iterable[dict]) -> List[dict]:
    """找出作用在 email 上的唯一索引（不含目标部分索引）。"""
    found = []
    for info in indexes:
        keys = _index_keys(info)
        if keys != (("email", 1),) and keys != (("email", ASCENDING),):
            continue
        if info.get("name") == PARTIAL_INDEX_NAME:
            continue
        if info.get("unique"):
            found.append(info)
    return found


def has_partial_email_index(indexes: Iterable[dict]) -> bool:
    for info in indexes:
        if info.get("name") == PARTIAL_INDEX_NAME and info.get("unique"):
            return True
    return False


def plan_email_index_fix(indexes: Iterable[dict]) -> List[str]:
    """返回将要执行的操作说明，不连库。"""
    index_list = list(indexes)
    actions: List[str] = []
    for info in find_email_unique_indexes(index_list):
        actions.append(f"dropIndex {info.get('name')}")
    if not has_partial_email_index(index_list):
        actions.append(
            f"createIndex {PARTIAL_INDEX_NAME} unique partialFilterExpression={PARTIAL_FILTER}"
        )
    if not actions:
        actions.append("noop: 目标部分唯一索引已存在，且无旧的 email 唯一索引")
    return actions


def apply_email_index_fix(collection: Collection, dry_run: bool = True) -> List[str]:
    indexes = list(collection.list_indexes())
    actions = plan_email_index_fix(indexes)
    logger.info("计划操作: %s", actions)
    if dry_run:
        logger.info("dry-run 模式，不执行")
        return actions

    for info in find_email_unique_indexes(collection.list_indexes()):
        name = info.get("name")
        logger.info("删除旧索引: %s", name)
        collection.drop_index(name)

    if not has_partial_email_index(collection.list_indexes()):
        logger.info("创建部分唯一索引: %s", PARTIAL_INDEX_NAME)
        try:
            collection.create_index(
                [("email", ASCENDING)],
                unique=True,
                name=PARTIAL_INDEX_NAME,
                partialFilterExpression=PARTIAL_FILTER,
            )
        except OperationFailure as exc:
            logger.error("创建部分索引失败: %s", exc)
            raise
    return actions


def main() -> int:
    parser = argparse.ArgumentParser(description="Fix users.email unique index to partial")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印将要变更的索引，不实际 drop/create",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    settings = get_settings()
    client = MongoClient(settings.MONGO_URI)
    collection = client[settings.MONGO_DB]["users"]
    try:
        client.admin.command("ping")
        apply_email_index_fix(collection, dry_run=args.dry_run)
        logger.info("完成 (dry_run=%s)", args.dry_run)
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
