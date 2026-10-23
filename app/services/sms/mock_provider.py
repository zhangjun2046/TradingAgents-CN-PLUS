"""Mock 短信通道：不真实发送，日志输出验证码。"""

from __future__ import annotations

from app.core.config import settings
from app.services.sms.base import SmsProvider

try:
    from tradingagents.utils.logging_manager import get_logger
except ImportError:
    import logging

    def get_logger(name: str) -> logging.Logger:
        return logging.getLogger(name)

logger = get_logger("sms.mock")


class MockSmsProvider(SmsProvider):
    name = "mock"

    async def send_code(self, phone: str, code: str, scene: str) -> None:
        masked = f"{phone[:3]}****{phone[-4:]}" if len(phone) >= 7 else "****"
        logger.info(
            "sms_send phone=%s scene=%s provider=mock result=ok mock_code=%s",
            masked,
            scene,
            code or settings.SMS_MOCK_CODE,
        )
