"""P1.3：注册、手机号登录、验证码登录、忘记密码。"""

from __future__ import annotations

from unittest.mock import AsyncMock

from bson import ObjectId
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import auth_db as auth_router
from app.services.sms_code_service import _hash_code
from app.services.user_service import user_service, UserService


class FakeUsers:
    def __init__(self):
        self.docs = []

    def _match(self, doc, query):
        return all(doc.get(k) == v for k, v in query.items())

    def find_one(self, query):
        for doc in self.docs:
            if self._match(doc, query):
                return dict(doc)
        return None

    def insert_one(self, doc):
        stored = dict(doc)
        stored.setdefault("_id", ObjectId())
        self.docs.append(stored)

        class _R:
            inserted_id = stored["_id"]

        return _R()

    def update_one(self, query, update):
        for doc in self.docs:
            if self._match(doc, query):
                doc.update(update.get("$set") or {})

                class _U:
                    modified_count = 1

                return _U()

        class _U0:
            modified_count = 0

        return _U0()


class FakeRedis:
    def __init__(self):
        self.kv = {}
        self.hashes = {}

    async def hset(self, key, mapping=None, **kwargs):
        bucket = self.hashes.setdefault(key, {})
        if mapping:
            bucket.update(mapping)
        bucket.update(kwargs)
        return len(bucket)

    async def hgetall(self, key):
        return dict(self.hashes.get(key, {}))

    async def delete(self, *keys):
        n = 0
        for key in keys:
            if key in self.hashes:
                del self.hashes[key]
                n += 1
            if key in self.kv:
                del self.kv[key]
                n += 1
        return n


def _seed_code(redis, scene, phone, code="123456"):
    redis.hashes[f"sms:code:{scene}:{phone}"] = {
        "code_hash": _hash_code(code),
        "attempts": "0",
    }


def _err(resp):
    return resp.json()["detail"]["code"]


def test_register_login_sms_reset_and_admin(monkeypatch):
    users = FakeUsers()
    redis = FakeRedis()
    users.docs.append(
        {
            "_id": ObjectId(),
            "username": "admin",
            "email": "admin@tradingagents.cn",
            "hashed_password": UserService.hash_password("admin123"),
            "is_active": True,
            "is_verified": True,
            "is_admin": True,
            "preferences": {},
        }
    )
    monkeypatch.setattr(user_service, "users_collection", users)
    monkeypatch.setattr("app.services.sms_code_service.get_redis", lambda: redis)
    monkeypatch.setattr("app.routers.auth_db.log_operation", AsyncMock(return_value=None))

    app = FastAPI()
    app.include_router(auth_router.router, prefix="/api/auth")
    client = TestClient(app)

    phone = "13900001111"
    _seed_code(redis, "register", phone)
    short = client.post(
        "/api/auth/register",
        json={"phone": phone, "code": "123456", "password": "123", "agreed": True},
    )
    assert short.status_code == 400 and _err(short) == "PASSWORD_INVALID"
    assert f"sms:code:register:{phone}" in redis.hashes

    no_terms = client.post(
        "/api/auth/register",
        json={"phone": phone, "code": "123456", "password": "Pass1234", "agreed": False},
    )
    assert no_terms.status_code == 400 and _err(no_terms) == "TERMS_NOT_AGREED"
    assert f"sms:code:register:{phone}" in redis.hashes

    created = client.post(
        "/api/auth/register",
        json={"phone": phone, "code": "123456", "password": "Pass1234", "agreed": True},
    )
    assert created.status_code == 200
    data = created.json()["data"]
    assert data["access_token"]
    assert data["user"]["username"] == phone
    assert data["user"]["phone"] == "139****1111"
    assert f"sms:code:register:{phone}" not in redis.hashes

    _seed_code(redis, "register", phone)
    dup = client.post(
        "/api/auth/register",
        json={"phone": phone, "code": "123456", "password": "Pass1234", "agreed": True},
    )
    assert dup.status_code == 409 and _err(dup) == "PHONE_REGISTERED"

    by_phone = client.post("/api/auth/login", json={"username": phone, "password": "Pass1234"})
    assert by_phone.status_code == 200
    assert by_phone.json()["data"]["user"]["phone"] == "139****1111"

    admin = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert admin.status_code == 200
    assert admin.json()["data"]["user"]["username"] == "admin"

    _seed_code(redis, "login", phone)
    sms_login = client.post("/api/auth/login/sms", json={"phone": phone, "code": "123456"})
    assert sms_login.status_code == 200
    token = sms_login.json()["data"]["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["data"]["phone"] == "139****1111"

    _seed_code(redis, "reset", phone)
    bad_reset = client.post(
        "/api/auth/password/reset-by-sms",
        json={"phone": phone, "code": "123456", "new_password": "1"},
    )
    assert bad_reset.status_code == 400 and _err(bad_reset) == "PASSWORD_INVALID"
    assert f"sms:code:reset:{phone}" in redis.hashes

    reset = client.post(
        "/api/auth/password/reset-by-sms",
        json={"phone": phone, "code": "123456", "new_password": "NewPass99"},
    )
    assert reset.status_code == 200
    old = client.post("/api/auth/login", json={"username": phone, "password": "Pass1234"})
    assert old.status_code == 401
    new = client.post("/api/auth/login", json={"username": phone, "password": "NewPass99"})
    assert new.status_code == 200


def test_sms_login_unregistered_looks_like_bad_code(monkeypatch):
    users = FakeUsers()
    redis = FakeRedis()
    monkeypatch.setattr(user_service, "users_collection", users)
    monkeypatch.setattr("app.services.sms_code_service.get_redis", lambda: redis)
    app = FastAPI()
    app.include_router(auth_router.router, prefix="/api/auth")
    client = TestClient(app)
    phone = "13900002222"
    _seed_code(redis, "login", phone)
    resp = client.post("/api/auth/login/sms", json={"phone": phone, "code": "123456"})
    assert resp.status_code == 400
    assert _err(resp) == "SMS_CODE_INVALID"
