"""图形验证码：SpecCaptcha + Redis 存答案哈希。"""

from __future__ import annotations

import hashlib
import uuid
from typing import Tuple

from easy_captcha import SpecCaptcha

from app.core.config import settings
from app.core.redis_client import get_redis

try:
    from tradingagents.utils.logging_manager import get_logger
except ImportError:
    import logging

    def get_logger(name: str) -> logging.Logger:
        return logging.getLogger(name)

logger = get_logger("captcha_service")


class CaptchaError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def _hash_answer(answer: str) -> str:
    return hashlib.sha256(answer.strip().lower().encode("utf-8")).hexdigest()


def _captcha_key(captcha_id: str) -> str:
    return f"captcha:{captcha_id}"


def _redis():
    try:
        return get_redis()
    except Exception as exc:
        logger.error("Redis 不可用，无法签发/校验图形验证码: %s", exc)
        raise CaptchaError(503, "REDIS_UNAVAILABLE", "验证码服务暂不可用") from exc


async def create_captcha() -> Tuple[str, str]:
    """生成图形验证码。返回 (captcha_id, image_base64)，不含 data: 前缀。"""
    captcha = SpecCaptcha(
        settings.CAPTCHA_WIDTH,
        settings.CAPTCHA_HEIGHT,
        settings.CAPTCHA_LENGTH,
    )
    answer = captcha.text()
    image_b64 = captcha.to_base64("")
    captcha_id = str(uuid.uuid4())
    redis = _redis()
    try:
        await redis.setex(
            _captcha_key(captcha_id),
            settings.CAPTCHA_TTL_SECONDS,
            _hash_answer(answer),
        )
    except CaptchaError:
        raise
    except Exception as exc:
        logger.error("写入图形验证码失败: %s", exc)
        raise CaptchaError(503, "REDIS_UNAVAILABLE", "验证码服务暂不可用") from exc
    logger.info("captcha_issued id=%s", captcha_id)
    return captcha_id, image_b64


async def verify_captcha(captcha_id: str, code: str) -> None:
    """核销图形验证码。成功即删除；失败不删除以便错误可刷新重取（过期/缺失除外）。"""
    if not captcha_id or not (code or "").strip():
        raise CaptchaError(400, "CAPTCHA_INVALID", "图形验证码错误或未携带")

    redis = _redis()
    key = _captcha_key(captcha_id)
    try:
        stored = await redis.get(key)
    except Exception as exc:
        logger.error("读取图形验证码失败: %s", exc)
        raise CaptchaError(503, "REDIS_UNAVAILABLE", "验证码服务暂不可用") from exc

    if not stored:
        raise CaptchaError(400, "CAPTCHA_EXPIRED", "图形验证码不存在或已过期")

    if stored != _hash_answer(code):
        raise CaptchaError(400, "CAPTCHA_INVALID", "图形验证码错误或未携带")

    await redis.delete(key)
