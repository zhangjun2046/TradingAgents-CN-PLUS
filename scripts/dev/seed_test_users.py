"""
开发环境种子账号脚本（P1.5）

直接在 MongoDB 的 users 集合创建普通用户 test_user_a / test_user_b（用户名 + 密码登录），
用于在手机号注册功能完成前测试「报告按用户隔离」。

- 幂等：账号已存在则跳过（不修改密码）；加 --reset-password 可重置为指定密码；
- 仅限开发环境：配置 DEBUG=false 时拒绝执行，除非显式加 --force；
- 两个账号均为普通用户（is_admin=false），邮箱各自唯一，不会触发邮箱唯一索引冲突。

用法：
    python scripts/dev/seed_test_users.py
    python scripts/dev/seed_test_users.py --password "MyPass123" --reset-password
"""
import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Windows 控制台默认 GBK，避免日志中的中文 / emoji 触发编码报错
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger("seed_test_users")

DEFAULT_PASSWORD = "Test@123456"
SEED_USERNAMES = ["test_user_a", "test_user_b"]


def hash_password(password: str) -> str:
    """复用现有登录使用的密码哈希，保证种子账号可直接用用户名 + 密码登录。"""
    from app.services.user_service import UserService

    return UserService.hash_password(password)


def build_user_doc(username: str, password: str) -> Dict[str, Any]:
    """构造普通用户文档，字段与 UserService.create_user 保持一致。"""
    now = datetime.utcnow()
    return {
        "username": username,
        "email": f"{username}@dev.local",
        "hashed_password": hash_password(password),
        "is_active": True,
        "is_verified": True,
        "is_admin": False,
        "created_at": now,
        "updated_at": now,
        "last_login": None,
        "preferences": {
            "default_market": "A股",
            "default_depth": "3",
            "default_analysts": ["市场分析师", "基本面分析师"],
            "auto_refresh": True,
            "refresh_interval": 30,
            "ui_theme": "light",
            "sidebar_width": 240,
            "language": "zh-CN",
            "notifications_enabled": True,
            "email_notifications": False,
            "desktop_notifications": True,
            "analysis_complete_notification": True,
            "system_maintenance_notification": True,
        },
        "daily_quota": 1000,
        "concurrent_limit": 3,
        "total_analyses": 0,
        "successful_analyses": 0,
        "failed_analyses": 0,
        "favorite_stocks": [],
    }


def seed_users(
    users_collection,
    password: str = DEFAULT_PASSWORD,
    reset_password: bool = False,
    usernames: List[str] = None,
) -> Dict[str, str]:
    """创建种子账号，返回 {username: created|exists|password_reset}。collection 可注入（便于测试）。"""
    result: Dict[str, str] = {}
    for username in usernames or SEED_USERNAMES:
        existing = users_collection.find_one({"username": username})
        if existing is None:
            users_collection.insert_one(build_user_doc(username, password))
            result[username] = "created"
        elif reset_password:
            users_collection.update_one(
                {"username": username},
                {"$set": {
                    "hashed_password": hash_password(password),
                    "updated_at": datetime.utcnow(),
                }},
            )
            result[username] = "password_reset"
        else:
            result[username] = "exists"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="创建开发用种子账号 test_user_a / test_user_b")
    parser.add_argument("--password", default=DEFAULT_PASSWORD, help=f"账号密码，默认 {DEFAULT_PASSWORD}")
    parser.add_argument("--reset-password", action="store_true", help="账号已存在时重置密码")
    parser.add_argument("--force", action="store_true", help="DEBUG=false 时仍强制执行（不建议）")
    args = parser.parse_args()

    from app.core.config import settings

    if not settings.DEBUG and not args.force:
        logger.error("当前 DEBUG=false，种子账号脚本仅限开发环境，已拒绝执行（确需执行请加 --force）")
        return 1

    from pymongo import MongoClient

    client = MongoClient(settings.MONGO_URI)
    try:
        users = client[settings.MONGO_DB].users
        outcome = seed_users(users, args.password, args.reset_password)
    finally:
        client.close()

    for username, status in outcome.items():
        logger.info(f"{username}: {status}")
    logger.info(f"登录方式：用户名 + 密码；新建账号的密码为 {args.password}（已存在且未加 --reset-password 的账号密码不变）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
