"""可用模型名单、角色拆分、公开接口与提交检查。"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.models.analysis import AnalysisParameters, SingleAnalysisRequest
from app.routers.auth_db import get_current_user
from app.routers.model_capabilities import router as model_capabilities_router
from app.routers.public_config import router as public_config_router
from app.services.available_models import (
    ModelCatalog,
    ModelEndpointError,
    build_catalog,
    resolve_available_endpoint,
    resolve_submission,
    select_available_configs,
    split_models_by_role,
    to_public_model,
)
from app.services.simple_analysis_service import (
    create_analysis_config,
    get_available_model_endpoint_sync,
)
from app.services.model_capability_service import ModelCapabilityService
from app.services.simple_analysis_service import SimpleAnalysisService


def _config(name, provider, enabled=True, roles=None):
    return SimpleNamespace(
        model_name=name,
        model_display_name=name,
        provider=provider,
        enabled=enabled,
        suitable_roles=roles if roles is not None else ["both"],
        capability_level=2,
        api_key="sk-secret",
        api_base="https://secret.example",
    )


def _providers(*items):
    return [SimpleNamespace(name=name, is_active=active) for name, active in items]


def test_unavailable_models_are_excluded():
    configs = [
        _config("off-model", "dashscope", enabled=False),
        _config("dead-provider", "disabled-co"),
        _config("orphan", "missing-co"),
        _config("kept", "dashscope"),
    ]
    selected = select_available_configs(
        configs,
        _providers(("dashscope", True), ("disabled-co", False)),
    )
    assert [item.model_name for item in selected] == ["kept"]


def test_same_name_keeps_first_active_provider():
    configs = [
        _config("shared", "disabled-co"),
        _config("shared", "dashscope"),
        _config("shared", "other"),
    ]
    selected = select_available_configs(
        configs,
        _providers(("dashscope", True), ("other", True), ("disabled-co", False)),
    )
    assert len(selected) == 1
    assert selected[0].provider == "dashscope"


def test_same_name_on_two_active_providers_keeps_first():
    configs = [
        _config("shared", "alpha"),
        _config("shared", "beta"),
    ]
    selected = select_available_configs(configs, _providers(("alpha", True), ("beta", True)))
    assert [item.provider for item in selected] == ["alpha"]


def test_role_split_and_empty_side_falls_back():
    quick_only = to_public_model(_config("fast", "dashscope", roles=["quick_analysis"]))
    deep_only = to_public_model(_config("slow", "dashscope", roles=["deep_analysis"]))
    both = to_public_model(_config("all", "dashscope", roles=["both"]))
    blank = to_public_model(_config("blank", "dashscope", roles=[]))

    quick, deep = split_models_by_role([quick_only, deep_only, both, blank])
    assert [item["name"] for item in quick] == ["fast", "all", "blank"]
    assert [item["name"] for item in deep] == ["slow", "all", "blank"]

    only_deep = [deep_only]
    quick_side, deep_side = split_models_by_role(only_deep)
    assert quick_side == only_deep
    assert deep_side == only_deep


def test_disabled_provider_absent_from_both_sides():
    catalog = build_catalog(
        SimpleNamespace(
            llm_configs=[
                _config("hidden", "disabled-co", roles=["quick_analysis"]),
                _config("shown", "dashscope", roles=["deep_analysis"]),
            ]
        ),
        _providers(("dashscope", True), ("disabled-co", False)),
    )
    assert catalog.models[0]["name"] == "shown"
    assert catalog.quick_models == catalog.models
    assert catalog.deep_models == catalog.models
    assert "sk-secret" not in str(catalog.models)


def _catalog_with(models):
    public = [to_public_model(item) for item in models]
    quick, deep = split_models_by_role(public)
    return public, quick, deep


def test_submit_rejects_unavailable_and_wrong_role():
    fast = _config("fast", "dashscope", roles=["quick_analysis"])
    slow = _config("slow", "dashscope", roles=["deep_analysis"])
    available, quick, deep = _catalog_with([fast, slow])

    with pytest.raises(ValueError, match="所选模型已不可用：gone"):
        resolve_submission("gone", "slow", quick, deep, available, None)

    with pytest.raises(ValueError, match="所选模型不适用于快速分析：slow"):
        resolve_submission("slow", "slow", quick, deep, available, None)

    assert resolve_submission("fast", "slow", quick, deep, available, None) == ("fast", "slow")


def test_submit_allows_any_available_model_when_role_side_falls_back():
    slow = _config("slow", "dashscope", roles=["deep_analysis"])
    other = _config("other", "dashscope", roles=["deep_analysis"])
    available, quick, deep = _catalog_with([slow, other])
    assert [item["name"] for item in quick] == ["slow", "other"]
    assert resolve_submission("other", "slow", quick, deep, available, None) == ("other", "slow")


def test_submit_without_models_uses_recommendation_then_first():
    fast = _config("fast", "dashscope", roles=["both"], )
    available, quick, deep = _catalog_with([fast])
    assert resolve_submission(None, None, quick, deep, available, ("fast", "fast")) == ("fast", "fast")
    assert resolve_submission(None, None, quick, deep, available, None) == ("fast", "fast")


def test_empty_catalog_rejects_submission():
    with pytest.raises(ValueError, match="当前没有可用的大模型"):
        resolve_submission(None, None, [], [], [], None)


def test_recommend_skips_disabled_provider_and_returns_none_without_candidate():
    service = ModelCapabilityService()
    disabled = SimpleNamespace(
        model_name="hidden",
        provider="disabled-co",
        enabled=True,
        suitable_roles=["both"],
        capability_level=5,
        features=["tool_calling"],
        performance_metrics={"cost": 1, "quality": 5},
    )
    visible = SimpleNamespace(
        model_name="visible",
        provider="dashscope",
        enabled=True,
        suitable_roles=["both"],
        capability_level=3,
        features=["tool_calling"],
        performance_metrics={"cost": 1, "quality": 4},
    )
    available = select_available_configs(
        [disabled, visible],
        _providers(("dashscope", True), ("disabled-co", False)),
    )
    pair = service.recommend_from_configs(available, "标准")
    assert pair == ("visible", "visible")

    no_tool = SimpleNamespace(
        model_name="plain",
        provider="dashscope",
        enabled=True,
        suitable_roles=["quick_analysis"],
        capability_level=2,
        features=[],
        performance_metrics={},
    )
    assert service.recommend_from_configs([no_tool], "标准") is None


def _public_client():
    app = FastAPI()
    app.include_router(public_config_router)
    app.dependency_overrides[get_current_user] = lambda: {"id": "u1", "is_admin": False}
    return TestClient(app)


def test_public_models_defaults_and_provider_failure():
    fast = _config("fast", "dashscope", roles=["quick_analysis"])
    slow = _config("slow", "dashscope", roles=["deep_analysis"])
    removed = _config("gone", "dashscope", roles=["quick_analysis"])
    config = SimpleNamespace(
        default_llm="gone",
        llm_configs=[fast, slow],
    )
    client = _public_client()
    with patch(
        "app.services.config_service.config_service.get_system_config",
        new=AsyncMock(return_value=config),
    ), patch(
        "app.services.available_models.fetch_provider_flags",
        new=AsyncMock(return_value=[{"name": "dashscope", "is_active": True}]),
    ), patch(
        "app.routers.public_config.config_provider.get_effective_system_settings",
        new=AsyncMock(return_value={"quick_analysis_model": "gone", "deep_analysis_model": "slow"}),
    ):
        resp = client.get("/api/config/public/models")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert [item["name"] for item in data["quick_models"]] == ["fast"]
    assert [item["name"] for item in data["deep_models"]] == ["slow"]
    assert data["default_quick_model"] == "fast"
    assert data["default_deep_model"] == "slow"
    assert removed.model_name not in str(data["models"])

    with patch(
        "app.services.config_service.config_service.get_system_config",
        new=AsyncMock(return_value=SimpleNamespace(default_llm=None, llm_configs=[])),
    ), patch(
        "app.services.available_models.fetch_provider_flags",
        new=AsyncMock(return_value=[]),
    ), patch(
        "app.routers.public_config.config_provider.get_effective_system_settings",
        new=AsyncMock(return_value={}),
    ):
        empty = client.get("/api/config/public/models")
    body = empty.json()["data"]
    assert body["models"] == []
    assert body["quick_models"] == []
    assert body["deep_models"] == []
    assert body["default_quick_model"] is None
    assert body["default_deep_model"] is None

    with patch(
        "app.services.available_models.fetch_provider_flags",
        new=AsyncMock(side_effect=Exception("db down")),
    ), patch(
        "app.services.config_service.config_service.get_system_config",
        new=AsyncMock(return_value=config),
    ):
        failed = client.get("/api/config/public/models")
    assert failed.status_code == 503


def test_recommend_endpoint_returns_null_without_candidate():
    app = FastAPI()
    app.include_router(model_capabilities_router)
    client = TestClient(app)
    catalog = ModelCatalog(config=None, configs=[], models=[], quick_models=[], deep_models=[])
    with patch(
        "app.services.available_models.load_model_catalog",
        new=AsyncMock(return_value=catalog),
    ):
        resp = client.post("/api/model-capabilities/recommend", json={"research_depth": "标准"})
    assert resp.status_code == 200
    assert resp.json()["data"] is None


def test_create_analysis_task_rejects_before_creating_task():
    service = SimpleAnalysisService()
    fast = _config("fast", "dashscope", roles=["quick_analysis"])
    slow = _config("slow", "dashscope", roles=["deep_analysis"])
    public, quick, deep = _catalog_with([fast, slow])
    catalog = ModelCatalog(
        config=None,
        configs=[fast, slow],
        models=public,
        quick_models=quick,
        deep_models=deep,
    )
    request = SingleAnalysisRequest(
        symbol="000001",
        parameters=AnalysisParameters(
            quick_analysis_model="gone",
            deep_analysis_model="slow",
        ),
    )

    async def run():
        with patch(
            "app.services.available_models.load_model_catalog",
            new=AsyncMock(return_value=catalog),
        ), patch.object(service.memory_manager, "create_task", new=AsyncMock()) as create_task:
            with pytest.raises(ValueError, match="所选模型已不可用：gone"):
                await service.create_analysis_task("user-1", request)
            create_task.assert_not_called()

    try:
        asyncio.run(run())
    finally:
        service._thread_pool.shutdown(wait=False)


def _live_provider(**extra):
    data = {
        "name": "dashscope",
        "is_active": True,
        "default_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key": "sk-current-provider-key",
    }
    data.update(extra)
    return data


def test_endpoint_uses_active_provider_url_and_current_key():
    stale = {
        "model_name": "shared",
        "provider": "old",
        "enabled": True,
        "api_base": "https://dashscope.aliyuncs.com/api/v1",
        "api_key": "sk-disabled-provider-key",
    }
    live = {
        "model_name": "shared",
        "provider": "dashscope",
        "enabled": True,
        "api_base": "  ",
        "api_key": "sk-copied-when-model-saved",
    }
    catalog = build_catalog(
        {"llm_configs": [stale, live]},
        [{"name": "old", "is_active": False}, {"name": "dashscope", "is_active": True}],
    )
    endpoint = resolve_available_endpoint("shared", catalog.configs[0], _live_provider())
    assert endpoint["provider"] == "dashscope"
    assert endpoint["backend_url"] == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    assert endpoint["api_key"] == "sk-current-provider-key"
    assert "api/v1" not in endpoint["backend_url"]


def test_endpoint_keeps_model_url_and_falls_back_to_model_key():
    endpoint = resolve_available_endpoint(
        "qwen-plus",
        {"provider": "dashscope", "api_base": "https://model.example/v1", "api_key": "sk-model-own-key"},
        _live_provider(api_key="your-api-key", default_base_url="https://provider.example/v1"),
    )
    assert endpoint["backend_url"] == "https://model.example/v1"
    assert endpoint["api_key"] == "sk-model-own-key"


def test_endpoint_fails_when_both_urls_empty_or_model_unavailable():
    with pytest.raises(ModelEndpointError, match="都未设置 API 基础 URL") as missing_url:
        resolve_available_endpoint(
            "qwen-plus",
            {"provider": "dashscope", "api_base": "", "api_key": "sk-copied"},
            _live_provider(default_base_url=""),
        )
    assert "api/v1" not in str(missing_url.value)

    with pytest.raises(ModelEndpointError, match="模型 gone 已不可用"):
        resolve_available_endpoint("gone", None, None)

    with pytest.raises(ModelEndpointError, match="模型 shared 已不可用"):
        resolve_available_endpoint(
            "shared",
            {"provider": "old", "api_base": "https://old.example/v1"},
            {"name": "old", "is_active": False, "default_base_url": "https://old.example/v1", "api_key": "sk-old"},
        )


def test_lookup_sync_reads_only_available_model():
    live = {
        "model_name": "shared",
        "provider": "dashscope",
        "api_base": "",
        "api_key": "sk-copied-when-model-saved",
    }
    catalog = ModelCatalog(config=None, configs=[live], models=[], quick_models=[], deep_models=[])
    with patch(
        "app.services.available_models.load_model_catalog_sync",
        return_value=catalog,
    ), patch(
        "app.services.simple_analysis_service._load_active_provider_sync",
        return_value=_live_provider(),
    ), patch(
        "app.services.simple_analysis_service._get_env_api_key_for_provider",
        return_value=None,
    ):
        info = get_available_model_endpoint_sync("shared")
    assert info["backend_url"] == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    assert info["api_key"] == "sk-current-provider-key"

    empty = ModelCatalog(config=None, configs=[], models=[], quick_models=[], deep_models=[])
    with patch("app.services.available_models.load_model_catalog_sync", return_value=empty):
        with pytest.raises(ModelEndpointError, match="模型 gone 已不可用"):
            get_available_model_endpoint_sync("gone")


def test_create_analysis_config_uses_resolved_endpoint_without_hardcoded_url():
    quick = {
        "provider": "dashscope",
        "backend_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key": "sk-current-provider-key",
    }
    deep = {**quick, "api_key": "sk-deep-current"}
    with patch(
        "app.services.simple_analysis_service.get_provider_and_url_by_model_sync",
        side_effect=AssertionError("不应再走旧查找"),
    ):
        config = create_analysis_config(
            "标准",
            ["market"],
            "qwen-plus",
            "qwen-max",
            "dashscope",
            quick_endpoint=quick,
            deep_endpoint=deep,
        )
    assert config["backend_url"] == quick["backend_url"]
    assert config["quick_api_key"] == "sk-current-provider-key"
    assert config["deep_api_key"] == "sk-deep-current"
    assert "api/v1" not in config["backend_url"]
