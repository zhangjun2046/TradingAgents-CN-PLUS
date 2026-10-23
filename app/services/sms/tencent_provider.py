"""腾讯云短信通道骨架（P1.2）。签名/模板未配置时发送失败，不静默。"""

from __future__ import annotations

from app.core.config import settings
from app.services.sms.base import SmsProvider, SmsProviderError

try:
    from tradingagents.utils.logging_manager import get_logger
except ImportError:
    import logging

    def get_logger(name: str) -> logging.Logger:
        return logging.getLogger(name)

logger = get_logger("sms.tencent")


class TencentSmsProvider(SmsProvider):
    name = "tencent"

    def _ensure_config(self) -> None:
        missing = [
            name
            for name, value in (
                ("SMS_SECRET_ID", settings.SMS_SECRET_ID),
                ("SMS_SECRET_KEY", settings.SMS_SECRET_KEY),
                ("SMS_SDK_APP_ID", settings.SMS_SDK_APP_ID),
                ("SMS_SIGN_NAME", settings.SMS_SIGN_NAME),
                ("SMS_TEMPLATE_ID", settings.SMS_TEMPLATE_ID),
            )
            if not (value or "").strip()
        ]
        if missing:
            logger.error("腾讯云短信配置缺失: %s", ",".join(missing))
            raise SmsProviderError(
                503,
                "SMS_NOT_CONFIGURED",
                "短信通道未配置，请联系管理员",
            )

    async def send_code(self, phone: str, code: str, scene: str) -> None:
        self._ensure_config()
        try:
            from tencentcloud.common import credential
            from tencentcloud.sms.v20210111 import sms_client, models
        except ImportError as exc:
            raise SmsProviderError(
                503,
                "SMS_NOT_CONFIGURED",
                "短信通道未配置，请联系管理员",
            ) from exc

        cred = credential.Credential(settings.SMS_SECRET_ID, settings.SMS_SECRET_KEY)
        client = sms_client.SmsClient(cred, settings.SMS_REGION)
        req = models.SendSmsRequest()
        req.SmsSdkAppId = settings.SMS_SDK_APP_ID
        req.SignName = settings.SMS_SIGN_NAME
        req.TemplateId = settings.SMS_TEMPLATE_ID
        req.TemplateParamSet = [code]
        req.PhoneNumberSet = [f"+86{phone}" if not phone.startswith("+") else phone]
        _ = scene
        try:
            resp = client.SendSms(req)
        except Exception as exc:
            logger.error("腾讯云短信发送失败: %s", exc)
            raise SmsProviderError(503, "SMS_SEND_FAILED", "短信发送失败，请稍后重试") from exc

        status = None
        if getattr(resp, "SendStatusSet", None):
            status = resp.SendStatusSet[0]
        if status is not None and getattr(status, "Code", "") not in ("Ok", "ok", "OK"):
            logger.error("腾讯云短信返回失败: %s", getattr(status, "Code", ""))
            raise SmsProviderError(503, "SMS_SEND_FAILED", "短信发送失败，请稍后重试")
