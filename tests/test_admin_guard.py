"""P1.4：require_admin 与公开模型接口。"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.deps import require_admin
from app.routers import config as config_router
from app.routers import database as database_router
from app.routers import logs as logs_router
from app.routers import operation_logs as operation_logs_router
from app.routers import public_config as public_config_router
from app.routers import sync as sync_router
from app.routers import system_config as system_config_router
from app.routers import usage_statistics as usage_router
from app.routers.auth_db import get_current_user


USER = {"id": "u1", "username": "13800138000", "is_admin": False}
ADMIN = {"id": "a1", "username": "admin", "is_admin": True}


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(config_router.router, prefix="/api")
    app.include_router(public_config_router.router)
    app.include_router(usage_router.router)
    app.include_router(sync_router.router)
    app.include_router(system_config_router.router, prefix="/api/system")
    app.include_router(database_router.router, prefix="/api/system")
    app.include_router(logs_router.router, prefix="/api/system")
    app.include_router(operation_logs_router.router, prefix="/api/system")
    return app


def _client(user: dict | None) -> TestClient:
    app = _app()
    if user is not None:

        async def _current():
            return user

        app.dependency_overrides[get_current_user] = _current
    return TestClient(app)


ADMIN_PATHS = [
    ("POST", "/api/config/reload"),
    ("GET", "/api/usage/records"),
    ("GET", "/api/sync/stock_basics/status"),
    ("GET", "/api/system/config/validate"),
    ("GET", "/api/system/database/status"),
    ("GET", "/api/system/system-logs/files"),
    ("GET", "/api/system/logs/list"),
]


def test_require_admin_direct():
    import asyncio
    from fastapi import HTTPException

    async def _run():
        try:
            await require_admin(USER)
            raise AssertionError("expected 403")
        except HTTPException as exc:
            assert exc.status_code == 403
            assert exc.detail == "FORBIDDEN"
        assert await require_admin(ADMIN) == ADMIN

    asyncio.run(_run())


def test_user_gets_403_on_admin_routes():
    client = _client(USER)
    for method, path in ADMIN_PATHS:
        resp = client.request(method, path)
        assert resp.status_code == 403, (path, resp.status_code, resp.text)
        assert resp.json()["detail"] == "FORBIDDEN"


def test_unauthenticated_gets_401():
    client = _client(None)
    resp = client.post("/api/config/reload")
    assert resp.status_code == 401
    resp = client.get("/api/config/public/models")
    assert resp.status_code == 401


def test_admin_reload_not_forbidden():
    client = _client(ADMIN)
    with patch("app.core.config_bridge.reload_bridged_config", return_value=True), patch(
        "app.routers.config.log_operation", new_callable=AsyncMock
    ):
        resp = client.post("/api/config/reload")
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_public_models_user_ok_no_secrets():
    fake = SimpleNamespace(
        default_llm="qwen-plus",
        llm_configs=[
            SimpleNamespace(
                enabled=True,
                model_name="qwen-plus",
                model_display_name="Qwen Plus",
                provider="dashscope",
                capability_level=3,
                suitable_roles=["both"],
                api_key="sk-secret",
                api_base="https://secret.example",
            )
        ],
    )
    client = _client(USER)
    with patch(
        "app.routers.public_config.config_service.get_system_config",
        new=AsyncMock(return_value=fake),
    ):
        resp = client.get("/api/config/public/models")
    assert resp.status_code == 200
    body = resp.json()
    data = body["data"]
    assert data["default_quick_model"] == "qwen-plus"
    assert data["default_deep_model"] == "qwen-plus"
    model = data["models"][0]
    assert model == {
        "name": "qwen-plus",
        "display_name": "Qwen Plus",
        "provider": "dashscope",
        "capability_level": 3,
        "roles": ["both"],
    }
    dumped = str(body)
    assert "sk-secret" not in dumped
    assert "secret.example" not in dumped
    assert "api_key" not in dumped
    assert "api_base" not in dumped
