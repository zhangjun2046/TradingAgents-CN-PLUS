"""短信验证码生成、存储、冷却与限流。"""

from __future__ import annotations

import hashlib
import random
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from app.core.config import settings
from app.core.redis_client import RedisService, get_redis
from app.services.captcha_service import CaptchaError, verify_captcha
from app.services.sms import SmsProviderError, get_sms_provider
from app.services.user_service import user_service

try:
    from tradingagents.utils.logging_manager import get_logger
except ImportError:
    import logging

    def get_logger(name: str) -> logging.Logger:
        return logging.getLogger(name)

logger = get_logger("sms_code_service")

PLATFORMS = ("h5", "pc")
SCENES = ("register", "login", "reset")
PHONE_PREFIX_LEN = 3
MAX_VERIFY_ATTEMPTS = 5


class SmsFlowError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def mask_phone(phone: str) -> str:
    if len(phone) < 7:
        return "****"
    return f"{phone[:PHONE_PREFIX_LEN]}****{phone[-4:]}"


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _code_key(scene: str, phone: str) -> str:
    return f"sms:code:{scene}:{phone}"


def _cooldown_key(platform: str, scene: str, phone: str) -> str:
    return f"sms:cooldown:{platform}:{scene}:{phone}"


def _daily_key(phone: str, now: datetime) -> str:
    return f"sms:daily:{now.strftime('%Y%m%d')}:{phone}"


def _ip_key(ip: str, now: datetime) -> str:
    return f"sms:ip:{now.strftime('%Y%m%d%H')}:{ip}"


def _now() -> datetime:
    try:
        return datetime.now(ZoneInfo(settings.TIMEZONE))
    except Exception:
        return datetime.now()


def _seconds_until_end_of_day(now: datetime) -> int:
    tomorrow = datetime.combine(now.date() + timedelta(days=1), datetime.min.time(), tzinfo=now.tzinfo)
    return max(int((tomorrow - now).total_seconds()), 1)


def _redis():
    try:
        return get_redis()
    except Exception as exc:
        logger.error("Redis 不可用: %s", exc)
        raise SmsFlowError(503, "REDIS_UNAVAILABLE", "验证码服务暂不可用") from exc


def _client_ip(request) -> str:
    forwarded = ""
    if request is not None:
        forwarded = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For") or ""
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host or "unknown"
    return "unknown"


async def send_sms_code(
    *,
    phone: str,
    scene: str,
    platform: str,
    captcha_id: str,
    captcha_code: str,
    request=None,
) -> dict:
    """按 tech_solution 7.2.1 顺序发短信。"""
    platform = (platform or "").strip().lower()
    scene = (scene or "").strip().lower()
    phone = (phone or "").strip()

    if platform not in PLATFORMS:
        raise SmsFlowError(400, "PLATFORM_INVALID", "platform 必须为 h5 或 pc")
    if scene not in SCENES:
        raise SmsFlowError(400, "PLATFORM_INVALID", "scene 必须为 register、login 或 reset")
    if not phone.isdigit() or len(phone) != 11:
        raise SmsFlowError(400, "CAPTCHA_INVALID", "手机号格式不正确")

    try:
        await verify_captcha(captcha_id, captcha_code)
        captcha_ok = True
    except CaptchaError as exc:
        raise SmsFlowError(exc.status, exc.code, exc.message) from exc

    existing = await user_service.get_user_by_phone(phone)
    if scene == "register" and existing is not None:
        logger.info(
            "sms_send phone=%s scene=%s platform=%s provider=%s result=phone_registered captcha=%s",
            mask_phone(phone),
            scene,
            platform,
            get_sms_provider().name,
            captcha_ok,
        )
        raise SmsFlowError(409, "PHONE_REGISTERED", "手机号已注册")
    if scene in ("login", "reset") and existing is None:
        logger.info(
            "sms_send phone=%s scene=%s platform=%s provider=%s result=skipped_unregistered captcha=%s",
            mask_phone(phone),
            scene,
            platform,
            get_sms_provider().name,
            captcha_ok,
        )
        return {
            "expires_in": settings.SMS_CODE_TTL_SECONDS,
            "resend_after": settings.SMS_RESEND_INTERVAL_SECONDS,
        }

    redis = _redis()
    cooldown_key = _cooldown_key(platform, scene, phone)
    try:
        acquired = await redis.set(
            cooldown_key,
            "1",
            nx=True,
            ex=settings.SMS_RESEND_INTERVAL_SECONDS,
        )
    except Exception as exc:
        raise SmsFlowError(503, "REDIS_UNAVAILABLE", "验证码服务暂不可用") from exc
    if not acquired:
        raise SmsFlowError(429, "SMS_TOO_FREQUENT", "发送太频繁，请稍后再试")

    now = _now()
    try:
        redis_svc = RedisService()
        daily_count = await redis_svc.increment_with_ttl(
            _daily_key(phone, now),
            _seconds_until_end_of_day(now),
        )
        if daily_count > settings.SMS_DAILY_LIMIT_PER_PHONE:
            await redis.delete(cooldown_key)
            raise SmsFlowError(429, "SMS_DAILY_LIMIT", "今日发送次数已达上限")

        ip = _client_ip(request)
        ip_count = await redis_svc.increment_with_ttl(_ip_key(ip, now), 3600)
        if ip_count > settings.SMS_HOURLY_LIMIT_PER_IP:
            await redis.delete(cooldown_key)
            raise SmsFlowError(429, "IP_RATE_LIMITED", "请求过于频繁，请稍后再试")
    except SmsFlowError:
        raise
    except Exception as exc:
        await redis.delete(cooldown_key)
        raise SmsFlowError(503, "REDIS_UNAVAILABLE", "验证码服务暂不可用") from exc

    provider = get_sms_provider()
    code = settings.SMS_MOCK_CODE if provider.name == "mock" else f"{random.randint(0, 999999):06d}"
    try:
        await redis.hset(
            _code_key(scene, phone),
            mapping={"code_hash": _hash_code(code), "attempts": "0"},
        )
        await redis.expire(_code_key(scene, phone), settings.SMS_CODE_TTL_SECONDS)
        await provider.send_code(phone, code, scene)
    except SmsProviderError as exc:
        await redis.delete(cooldown_key)
        raise SmsFlowError(exc.status, exc.code, exc.message) from exc
    except Exception as exc:
        await redis.delete(cooldown_key)
        logger.error("短信发送异常: %s", exc)
        raise SmsFlowError(503, "REDIS_UNAVAILABLE", "验证码服务暂不可用") from exc

    logger.info(
        "sms_send phone=%s scene=%s platform=%s provider=%s result=ok captcha=%s",
        mask_phone(phone),
        scene,
        platform,
        provider.name,
        captcha_ok,
    )
    return {
        "expires_in": settings.SMS_CODE_TTL_SECONDS,
        "resend_after": settings.SMS_RESEND_INTERVAL_SECONDS,
    }


async def verify_sms_code(phone: str, scene: str, code: str) -> None:
    """校验短信验证码：成功删除；错误累计 5 次后作废。供 P1.3 与本单元测试使用。"""
    redis = _redis()
    key = _code_key(scene, phone)
    try:
        data = await redis.hgetall(key)
    except Exception as exc:
        raise SmsFlowError(503, "REDIS_UNAVAILABLE", "验证码服务暂不可用") from exc
    if not data or not data.get("code_hash"):
        raise SmsFlowError(400, "SMS_CODE_INVALID", "验证码错误或已过期")

    if data["code_hash"] == _hash_code(code or ""):
        await redis.delete(key)
        return

    attempts = int(data.get("attempts") or 0) + 1
    if attempts >= MAX_VERIFY_ATTEMPTS:
        await redis.delete(key)
    else:
        await redis.hset(key, mapping={"attempts": str(attempts)})
    raise SmsFlowError(400, "SMS_CODE_INVALID", "验证码错误或已过期")
