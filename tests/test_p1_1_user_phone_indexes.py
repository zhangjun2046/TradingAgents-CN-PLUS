"""P1.1：用户手机号字段、稀疏唯一索引、邮箱部分索引。"""

from __future__ import annotations

import asyncio
import importlib.util
import uuid
from pathlib import Path

import pytest
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, ServerSelectionTimeoutError

from app.core.config import get_settings
from app.models.user import User, UserCreate
from app.services.user_service import UserService

_MIGRATION = Path(__file__).resolve().parents[1] / "scripts" / "migrations" / "fix_users_email_index.py"
_spec = importlib.util.spec_from_file_location("fix_users_email_index", _MIGRATION)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)
PARTIAL_INDEX_NAME = _mod.PARTIAL_INDEX_NAME
has_partial_email_index = _mod.has_partial_email_index
plan_email_index_fix = _mod.plan_email_index_fix


def test_user_model_allows_missing_email_and_phone_fields():
    user = User(username="13800138000", hashed_password="x")
    assert user.email is None
    assert user.phone is None
    assert user.phone_verified_at is None
    assert user.agreed_terms_at is None


def test_user_model_rejects_invalid_email():
    with pytest.raises(Exception):
        User(username="someone", hashed_password="x", email="not-an-email")


def test_plan_email_index_fix_drops_old_unique_and_creates_partial():
    indexes = [
        {"name": "_id_", "key": {"_id": 1}},
        {"name": "email_1", "key": {"email": 1}, "unique": True},
    ]
    actions = plan_email_index_fix(indexes)
    assert "dropIndex email_1" in actions
    assert any(PARTIAL_INDEX_NAME in item for item in actions)


def test_plan_email_index_fix_noop_when_already_migrated():
    indexes = [
        {
            "name": PARTIAL_INDEX_NAME,
            "key": {"email": 1},
            "unique": True,
            "partialFilterExpression": {"email": {"$type": "string"}},
        }
    ]
    actions = plan_email_index_fix(indexes)
    assert actions == ["noop: 目标部分唯一索引已存在，且无旧的 email 唯一索引"]
    assert has_partial_email_index(indexes) is True


def _mongo_or_skip() -> MongoClient:
    settings = get_settings()
    client = MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=3000)
    try:
        client.admin.command("ping")
    except ServerSelectionTimeoutError:
        client.close()
        pytest.skip("MongoDB 不可用")
    return client


def test_two_users_without_email_and_duplicate_phone_rejected():
    client = _mongo_or_skip()
    db = client["tradingagents_p11_test"]
    users = db["users"]
    reports = db["analysis_reports"]
    tasks = db["analysis_tasks"]
    service = UserService()
    leftover_client = service.client
    service.client = client
    service.db = db
    service.users_collection = users
    try:
        users.drop()
        reports.drop()
        tasks.drop()
        service.ensure_indexes()

        suffix = uuid.uuid4().hex[:8]
        first = UserCreate(
            username=f"u1{suffix}",
            password="secret1",
            phone=f"1390000{suffix[:4]}",
        )
        second = UserCreate(
            username=f"u2{suffix}",
            password="secret2",
            phone=f"1380000{suffix[:4]}",
        )
        dup_phone = UserCreate(
            username=f"u3{suffix}",
            password="secret3",
            phone=first.phone,
        )

        a = asyncio.run(service.create_user(first))
        b = asyncio.run(service.create_user(second))
        c = asyncio.run(service.create_user(dup_phone))
        assert a is not None and a.email is None
        assert b is not None and b.email is None
        assert c is None

        with pytest.raises(DuplicateKeyError):
            users.insert_one(
                {
                    "username": f"u4{suffix}",
                    "phone": first.phone,
                    "hashed_password": "x",
                }
            )

        index_names = users.index_information()
        assert "uniq_phone" in index_names
        assert "user_reports" in reports.index_information()
        assert "uniq_task_id" in tasks.index_information()
    finally:
        users.drop()
        reports.drop()
        tasks.drop()
        leftover_client.close()
        client.drop_database("tradingagents_p11_test")
        client.close()
