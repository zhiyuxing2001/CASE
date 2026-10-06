"""端点注册表：从环境变量构建端点与路由。

默认只有 ``deepseek-api`` 一个端点；自托管落地时只需在 ``.env`` 把
``LLM_ENDPOINTS`` 改为 ``deepseek-api,selfhosted`` 并补上对应配置。
"""

from __future__ import annotations

import os

from ..config import settings
from .types import Capability, LlmEndpoint, ProviderKind

DEFAULT_CAPS = "vision,json_mode,tool_calls,long_context,streaming"


def _capabilities(raw: str) -> frozenset[Capability]:
    result: set[Capability] = set()
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            result.add(Capability(token))
        except ValueError:
            continue
    return frozenset(result)


def _db_setting(key: str) -> str:
    """从 app_setting 读设置项；表不存在或会话不可用时返回空串。"""
    try:
        from ..db import SessionLocal
        from ..models import AppSetting
        with SessionLocal() as session:
            row = session.get(AppSetting, key)
            return row.value if row and row.value else ""
    except Exception:  # noqa: BLE001
        return ""


def build_registry() -> tuple[LlmEndpoint, ...]:
    names = [
        n.strip()
        for n in os.getenv("LLM_ENDPOINTS", "deepseek-api").split(",")
        if n.strip()
    ]
    endpoints: list[LlmEndpoint] = []
    for name in names:
        prefix = f"LLM_{name.upper().replace('-', '_')}_"

        def get(field: str, default: str = "") -> str:
            return os.getenv(prefix + field, default)

        # deepseek-api 缺省时依次回落：环境变量 → 数据库 → .env
        db_base = db_key = db_model = ""
        if name == "deepseek-api":
            db_base = _db_setting("deepseek_base_url")
            db_key = _db_setting("deepseek_api_key")
            db_model = _db_setting("deepseek_model")
        base_url = get("BASE_URL", "") or db_base or settings.deepseek_base_url
        api_key = get("API_KEY", "") or db_key or settings.deepseek_api_key
        model = get("MODEL", "") or db_model or settings.deepseek_text_model
        caps = get("CAPABILITIES", DEFAULT_CAPS)
        kind_raw = get("KIND", "api")
        context = int(get("CONTEXT", "1000000") or "1000000")

        endpoints.append(LlmEndpoint(
            name=name,
            kind=ProviderKind(kind_raw) if kind_raw in {"api", "self_hosted"} else ProviderKind.API,
            base_url=base_url.rstrip("/"),
            api_key=api_key,
            model=model,
            capabilities=_capabilities(caps),
            context_window=context,
        ))
    return tuple(endpoints)
