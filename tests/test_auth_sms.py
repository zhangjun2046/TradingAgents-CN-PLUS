"""P1.2：图形验证码、短信发送与冷却三元组。"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import settings
from app.routers import auth_db as auth_router
from app.services.sms import reset_sms_provider
from app.services.sms_code_service import verify_sms_code, SmsFlowError


class FakePipeline:
    def __init__(self, redis: "FakeRedis"):
        self.redis = redis
        self._ops = []

    def incr(self, key):
        self._ops.append(("incr", key))
        return self

    def expire(self, key, ttl):
        self._ops.append(("expire", key, ttl))
        return self

    async def execute(self):
        results = []
        for op in self._ops:
            if op[0] == "incr":
                results.append(await self.redis.incr(op[1]))
            else:
                results.append(True)
        return results


class FakeRedis:
    def __init__(self):
        self.kv = {}
        self.hashes = {}

    async def ping(self):
        return True

    async def get(self, key):
        return self.kv.get(key)

    async def set(self, key, value, nx=False, ex=None):
        if nx and key in self.kv:
            return False
        self.kv[key] = value
        return True

    async def setex(self, key, ttl, value):
        self.kv[key] = value
        return True

    async def delete(self, *keys):
        n = 0
        for key in keys:
            if key in self.kv:
                del self.kv[key]
                n += 1
            if key in self.hashes:
                del self.hashes[key]
                n += 1
        return n

    async def incr(self, key):
        self.kv[key] = str(int(self.kv.get(key) or 0) + 1)
        return int(self.kv[key])

    async def expire(self, key, ttl):
        return True

    async def hset(self, key, mapping=None, **kwargs):
        bucket = self.hashes.setdefault(key, {})
        if mapping:
            bucket.update(mapping)
        bucket.update(kwargs)
        return len(bucket)

    async def hgetall(self, key):
        return dict(self.hashes.get(key, {}))

    def pipeline(self):
        return FakePipeline(self)


class DummyCaptcha:
    def __init__(self, *args, **kwargs):
        pass

    def text(self):
        return "Ab12"

    def to_base64(self, prefix="x"):
        return "cG5n"


@pytest.fixture()
def env(monkeypatch):
    redis = FakeRedis()
    monkeypatch.setattr("app.core.redis_client.get_redis", lambda: redis)
    monkeypatch.setattr("app.services.captcha_service.get_redis", lambda: redis)
    monkeypatch.setattr("app.services.sms_code_service.get_redis", lambda: redis)
    monkeypatch.setattr("app.services.captcha_service.SpecCaptcha", DummyCaptcha)
    monkeypatch.setattr(
        "app.services.sms_code_service.user_service.get_user_by_phone",
        AsyncMock(return_value=None),
    )
    reset_sms_provider()
    app = FastAPI()
    app.include_router(auth_router.router, prefix="/api/auth")
    with TestClient(app) as client:
        yield client, redis
    reset_sms_provider()


def _err(resp):
    return resp.json()["detail"]["code"]


def _issue(client):
    resp = client.get("/api/auth/captcha")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["captcha_id"]
    assert data["image_base64"]
    return data["captcha_id"]


def _send(client, captcha_id, **overrides):
    body = {
        "phone": "13800138000",
        "scene": "register",
        "platform": "h5",
        "captcha_id": captcha_id,
        "captcha_code": "Ab12",
    }
    body.update(overrides)
    return client.post("/api/auth/sms/send", json=body)


def test_captcha_then_send_ok(env):
    client, redis = env
    captcha_id = _issue(client)
    resp = _send(client, captcha_id)
    assert resp.status_code == 200
    assert resp.json()["data"]["expires_in"] == settings.SMS_CODE_TTL_SECONDS
    assert resp.json()["data"]["resend_after"] == 60
    stored = redis.hashes.get("sms:code:register:13800138000")
    assert stored and stored.get("code_hash")


def test_missing_captcha_does_not_send(env):
    client, redis = env
    resp = _send(client, "", captcha_code="")
    assert resp.status_code == 400
    assert _err(resp) == "CAPTCHA_INVALID"
    assert "sms:code:register:13800138000" not in redis.hashes


def test_wrong_captcha_does_not_send(env):
    client, redis = env
    captcha_id = _issue(client)
    resp = _send(client, captcha_id, captcha_code="xxxx")
    assert resp.status_code == 400
    assert _err(resp) == "CAPTCHA_INVALID"
    assert "sms:code:register:13800138000" not in redis.hashes


def test_expired_captcha_does_not_send(env):
    client, redis = env
    resp = _send(client, "missing-id")
    assert resp.status_code == 400
    assert _err(resp) == "CAPTCHA_EXPIRED"


def test_captcha_consumed_after_success(env):
    client, _redis = env
    captcha_id = _issue(client)
    assert _send(client, captcha_id).status_code == 200
    resp = _send(client, captcha_id)
    assert resp.status_code == 400
    assert _err(resp) == "CAPTCHA_EXPIRED"


def test_platform_invalid(env):
    client, _redis = env
    captcha_id = _issue(client)
    resp = _send(client, captcha_id, platform="app")
    assert resp.status_code == 400
    assert _err(resp) == "PLATFORM_INVALID"


def test_cooldown_triplet_and_other_dimension_ok(env, monkeypatch):
    client, _redis = env
    assert _send(client, _issue(client)).status_code == 200
    again = _send(client, _issue(client))
    assert again.status_code == 429
    assert _err(again) == "SMS_TOO_FREQUENT"
    other_platform = _send(client, _issue(client), platform="pc")
    assert other_platform.status_code == 200

    monkeypatch.setattr(
        "app.services.sms_code_service.user_service.get_user_by_phone",
        AsyncMock(return_value=object()),
    )
    other_scene = _send(client, _issue(client), scene="login")
    assert other_scene.status_code == 200


def test_daily_limit(env, monkeypatch):
    client, _redis = env
    monkeypatch.setattr(settings, "SMS_DAILY_LIMIT_PER_PHONE", 1)
    assert _send(client, _issue(client)).status_code == 200
    resp = _send(client, _issue(client), platform="pc")
    assert resp.status_code == 429
    assert _err(resp) == "SMS_DAILY_LIMIT"


def test_ip_rate_limit(env, monkeypatch):
    client, _redis = env
    monkeypatch.setattr(settings, "SMS_HOURLY_LIMIT_PER_IP", 1)
    assert _send(client, _issue(client)).status_code == 200
    resp = _send(client, _issue(client), platform="pc")
    assert resp.status_code == 429
    assert _err(resp) == "IP_RATE_LIMITED"


def test_register_phone_already_exists(env, monkeypatch):
    client, redis = env
    monkeypatch.setattr(
        "app.services.sms_code_service.user_service.get_user_by_phone",
        AsyncMock(return_value=object()),
    )
    resp = _send(client, _issue(client))
    assert resp.status_code == 409
    assert _err(resp) == "PHONE_REGISTERED"
    assert "sms:code:register:13800138000" not in redis.hashes


def test_login_unregistered_returns_ok_without_sending(env):
    client, redis = env
    resp = _send(client, _issue(client), scene="login")
    assert resp.status_code == 200
    assert "sms:code:login:13800138000" not in redis.hashes


def test_sms_code_verify_once_and_five_attempts(env):
    import asyncio
    from app.services.sms_code_service import _hash_code

    _client, redis = env

    async def _run():
        await redis.hset(
            "sms:code:login:13800138001",
            mapping={"code_hash": _hash_code("123456"), "attempts": "0"},
        )
        await verify_sms_code("13800138001", "login", "123456")
        with pytest.raises(SmsFlowError) as expired:
            await verify_sms_code("13800138001", "login", "123456")
        assert expired.value.code == "SMS_CODE_INVALID"

        await redis.hset(
            "sms:code:login:13800138002",
            mapping={"code_hash": _hash_code("123456"), "attempts": "0"},
        )
        for _ in range(4):
            with pytest.raises(SmsFlowError):
                await verify_sms_code("13800138002", "login", "000000")
        with pytest.raises(SmsFlowError):
            await verify_sms_code("13800138002", "login", "000000")
        assert "sms:code:login:13800138002" not in redis.hashes

    asyncio.run(_run())


def test_tencent_missing_config_returns_503(env, monkeypatch):
    client, _redis = env
    monkeypatch.setattr(settings, "SMS_PROVIDER", "tencent")
    monkeypatch.setattr(settings, "SMS_SECRET_ID", "")
    reset_sms_provider()
    resp = _send(client, _issue(client))
    assert resp.status_code == 503
    assert _err(resp) == "SMS_NOT_CONFIGURED"
