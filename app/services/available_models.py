"""可用模型名单与快速/深度拆分。

纯函数不做数据库访问。读取失败与「确实没有厂家」必须区分开。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Optional, Sequence, Tuple


class ModelCatalogError(Exception):
    """读取模型配置或厂家失败。调用方应返回 503，不要当成空名单。"""


class ModelEndpointError(Exception):
    """分析时模型已不可用，或模型和厂家都没有 API 地址。"""


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _as_text_list(value: Any) -> list[str]:
    if not value:
        return []
    items = value if isinstance(value, (list, tuple, set)) else [value]
    out: list[str] = []
    for item in items:
        if item is None:
            continue
        text = item.value if hasattr(item, "value") else str(item)
        text = text.strip()
        if text:
            out.append(text)
    return out


def normalize_roles(value: Any) -> list[str]:
    """空角色或缺失视为 both。"""
    roles = _as_text_list(value)
    return roles or ["both"]


def select_available_configs(llm_configs: Optional[Iterable[Any]], providers: Optional[Iterable[Any]]) -> list[Any]:
    """启用且厂家启用的模型。同一 model_name 只保留 llm_configs 里第一条可用配置。"""
    active_names = set()
    for provider in providers or []:
        name = _get(provider, "name")
        if name and _get(provider, "is_active"):
            active_names.add(name)

    selected: list[Any] = []
    seen: set[str] = set()
    for config in llm_configs or []:
        if _get(config, "enabled", True) is False:
            continue
        provider_name = _get(config, "provider")
        if provider_name not in active_names:
            continue
        model_name = _get(config, "model_name") or _get(config, "name")
        if not model_name or model_name in seen:
            continue
        seen.add(model_name)
        selected.append(config)
    return selected


def to_public_model(config: Any) -> dict[str, Any]:
    name = _get(config, "model_name") or _get(config, "name")
    display = _get(config, "model_display_name") or _get(config, "display_name") or name
    level = _get(config, "capability_level", 2)
    if level is None:
        level = 2
    raw_roles = _get(config, "suitable_roles", None)
    if raw_roles is None:
        raw_roles = _get(config, "roles", None)
    return {
        "name": name,
        "display_name": display,
        "provider": _get(config, "provider"),
        "capability_level": level,
        "roles": normalize_roles(raw_roles),
    }


_QUICK_ROLES = {"quick_analysis", "both"}
_DEEP_ROLES = {"deep_analysis", "both"}


def _matches_role(roles: Sequence[str], wanted: set[str]) -> bool:
    return bool(set(normalize_roles(roles)) & wanted)


def split_models_by_role(models: Sequence[dict[str, Any]]) -> Tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """按适用角色拆快速、深度。某一侧没有候选时，该侧退回整份名单。"""
    quick = [item for item in models if _matches_role(item.get("roles") or [], _QUICK_ROLES)]
    deep = [item for item in models if _matches_role(item.get("roles") or [], _DEEP_ROLES)]
    return (quick or list(models), deep or list(models))


def _nonempty_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _usable_api_key(value: Any) -> Optional[str]:
    text = _nonempty_text(value)
    if not text or text.startswith("your_") or text.startswith("your-"):
        return None
    return text


def resolve_available_endpoint(
    model_name: str,
    config: Any,
    provider: Any,
    env_api_key: Optional[str] = None,
) -> dict[str, Any]:
    """从一条可用模型及其厂家解析地址和密钥。

    地址：模型 api_base，否则厂家当前 default_base_url。两者都空则失败，不使用代码里的公共地址。
    密钥：厂家当前密钥优先，避免使用保存模型时复制的旧密钥；厂家没有时再用模型上的密钥，最后才用环境变量。
    """
    provider_name = _get(provider, "name") if provider is not None else None
    config_provider = _get(config, "provider") if config is not None else None
    if (
        config is None
        or provider is None
        or _get(provider, "is_active") is False
        or not provider_name
        or provider_name != config_provider
    ):
        raise ModelEndpointError(f"模型 {model_name} 已不可用")

    api_base = _nonempty_text(_get(config, "api_base"))
    provider_url = _nonempty_text(_get(provider, "default_base_url"))
    if api_base:
        backend_url = api_base
    elif provider_url:
        backend_url = provider_url
    else:
        raise ModelEndpointError(
            f"模型 {model_name} 未配置 API 地址：模型配置和厂家配置都未设置 API 基础 URL"
        )

    api_key = (
        _usable_api_key(_get(provider, "api_key"))
        or _usable_api_key(_get(config, "api_key"))
        or _usable_api_key(env_api_key)
    )
    return {
        "provider": provider_name,
        "backend_url": backend_url,
        "api_key": api_key,
    }


def pick_side_default(side_models: Sequence[dict[str, Any]], *preferred: Optional[str]) -> Optional[str]:
    names = [item.get("name") for item in side_models if item.get("name")]
    if not names:
        return None
    for name in preferred:
        if name and name in names:
            return name
    return names[0]


def explicit_model_name(params: Any, field: str) -> Optional[str]:
    """只认调用方真正传入的模型名。Pydantic 默认值不算传入。"""
    if params is None:
        return None
    fields_set = getattr(params, "model_fields_set", None)
    if fields_set is not None and field not in fields_set:
        return None
    value = _get(params, field, None)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def resolve_submission(
    quick: Optional[str],
    deep: Optional[str],
    quick_models: Sequence[dict[str, Any]],
    deep_models: Sequence[dict[str, Any]],
    available_models: Sequence[dict[str, Any]],
    recommend: Optional[Tuple[str, str]],
) -> Tuple[str, str]:
    """提交前确定快速、深度模型。不在对应侧名单里就抛出 ValueError。"""
    available_names = {item.get("name") for item in available_models if item.get("name")}
    quick_names = [item.get("name") for item in quick_models if item.get("name")]
    deep_names = [item.get("name") for item in deep_models if item.get("name")]
    quick_set = set(quick_names)
    deep_set = set(deep_names)

    def ensure(name: str, label: str, side_names: set[str]) -> None:
        if name not in available_names:
            raise ValueError(f"所选模型已不可用：{name}，请刷新页面后重新选择")
        if name not in side_names:
            raise ValueError(f"所选模型不适用于{label}：{name}，请刷新页面后重新选择")

    if not quick_names or not deep_names:
        if quick:
            ensure(quick, "快速分析", quick_set)
        if deep:
            ensure(deep, "深度决策", deep_set)
        raise ValueError("当前没有可用的大模型，请联系管理员在大模型配置中启用模型")

    recommended_quick = recommend[0] if recommend else None
    recommended_deep = recommend[1] if recommend else None

    def fill(current: Optional[str], label: str, ordered: list[str], side_names: set[str], recommended: Optional[str]) -> str:
        if current:
            ensure(current, label, side_names)
            return current
        if recommended and recommended in side_names:
            return recommended
        return ordered[0]

    if quick or deep:
        return (
            fill(quick, "快速分析", quick_names, quick_set, recommended_quick),
            fill(deep, "深度决策", deep_names, deep_set, recommended_deep),
        )

    if (
        recommended_quick
        and recommended_deep
        and recommended_quick in quick_set
        and recommended_deep in deep_set
    ):
        return recommended_quick, recommended_deep
    return quick_names[0], deep_names[0]


@dataclass
class ModelCatalog:
    config: Any
    configs: list[Any]
    models: list[dict[str, Any]]
    quick_models: list[dict[str, Any]]
    deep_models: list[dict[str, Any]]


def build_catalog(config: Any, providers: Optional[Iterable[Any]]) -> ModelCatalog:
    llm_configs = _get(config, "llm_configs", None) if config is not None else None
    configs = select_available_configs(llm_configs, providers)
    models = [to_public_model(item) for item in configs]
    quick_models, deep_models = split_models_by_role(models)
    return ModelCatalog(
        config=config,
        configs=configs,
        models=models,
        quick_models=quick_models,
        deep_models=deep_models,
    )


async def fetch_provider_flags() -> list[dict[str, Any]]:
    """只读厂家 name 与 is_active。失败抛 ModelCatalogError，空集合则返回空列表。"""
    from app.services.config_service import config_service

    try:
        db = await config_service._get_db()
        cursor = db.llm_providers.find({}, {"name": 1, "is_active": 1})
        return await cursor.to_list(length=None)
    except ModelCatalogError:
        raise
    except Exception as exc:
        raise ModelCatalogError("读取厂家失败") from exc


async def load_model_catalog() -> ModelCatalog:
    from app.services.config_service import config_service

    try:
        config = await config_service.get_system_config()
    except Exception as exc:
        raise ModelCatalogError("读取模型配置失败") from exc
    providers = await fetch_provider_flags()
    return build_catalog(config, providers)


def load_model_catalog_sync() -> ModelCatalog:
    """分析线程内使用。厂家读取失败抛错，不把异常当成空名单。"""
    from pymongo import MongoClient

    from app.core.config import settings

    client = MongoClient(settings.MONGO_URI)
    try:
        db = client[settings.MONGO_DB]
        try:
            config = db.system_configs.find_one({"is_active": True}, sort=[("version", -1)])
        except Exception as exc:
            raise ModelCatalogError("读取模型配置失败") from exc
        try:
            providers = list(db.llm_providers.find({}, {"name": 1, "is_active": 1}))
        except Exception as exc:
            raise ModelCatalogError("读取厂家失败") from exc
    finally:
        client.close()
    return build_catalog(config, providers)
