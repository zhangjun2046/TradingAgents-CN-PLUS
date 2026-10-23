"""按配置返回短信 Provider 单例。"""

from __future__ import annotations

from typing import Optional

from app.core.config import settings
from app.services.sms.base import SmsProvider, SmsProviderError
from app.services.sms.mock_provider import MockSmsProvider
from app.services.sms.tencent_provider import TencentSmsProvider

_provider: Optional[SmsProvider] = None


def get_sms_provider() -> SmsProvider:
    global _provider
    if _provider is not None:
        return _provider
    name = (settings.SMS_PROVIDER or "mock").strip().lower()
    if name == "tencent":
        _provider = TencentSmsProvider()
    else:
        _provider = MockSmsProvider()
    return _provider


def reset_sms_provider() -> None:
    """测试用：清掉单例。"""
    global _provider
    _provider = None


__all__ = ["SmsProvider", "SmsProviderError", "get_sms_provider", "reset_sms_provider"]
