"""短信通道抽象。"""

from __future__ import annotations

from abc import ABC, abstractmethod


class SmsProviderError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


class SmsProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def send_code(self, phone: str, code: str, scene: str) -> None:
        """发送短信验证码。配置缺失或通道失败时应抛 SmsProviderError。"""
