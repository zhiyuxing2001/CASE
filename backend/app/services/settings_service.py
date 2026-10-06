"""应用设置读写（app_setting 表）。

DeepSeek API Key 存于本地 SQLite（``data/case.db``，已 gitignore），
不再要求手工编辑 ``.env``；``.env`` 仅作首次兜底。
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from ..config import settings
from ..models import AppSetting

KEY_API_KEY = "deepseek_api_key"
KEY_BASE_URL = "deepseek_base_url"
KEY_MODEL = "deepseek_model"

_ALL = (KEY_API_KEY, KEY_BASE_URL, KEY_MODEL)


def _mask(key: str) -> str:
    if not key:
        return ""
    return f"••••{key[-4:]}"


def effective_api_key(db: Session) -> str:
    """生效的 API Key：数据库优先，.env 兜底。"""
    row = db.get(AppSetting, KEY_API_KEY)
    if row and row.value:
        return row.value
    return settings.deepseek_api_key


def get_ai_config(db: Session) -> dict:
    rows = {
        row.key: row.value
        for row in db.query(AppSetting).filter(AppSetting.key.in_(_ALL)).all()
    }
    api_key = rows.get(KEY_API_KEY, "") or settings.deepseek_api_key
    base_url = rows.get(KEY_BASE_URL, "") or settings.deepseek_base_url
    model = rows.get(KEY_MODEL, "") or settings.deepseek_text_model
    return {
        "configured": bool(api_key),
        "api_key_masked": _mask(api_key),
        "base_url": base_url,
        "model": model,
    }


def save_ai_config(
    db: Session,
    api_key: str | None,
    base_url: str | None,
    model: str | None,
) -> None:
    updates: dict[str, str] = {}
    if api_key is not None:
        updates[KEY_API_KEY] = api_key
    if base_url is not None:
        updates[KEY_BASE_URL] = base_url
    if model is not None:
        updates[KEY_MODEL] = model
    for key, value in updates.items():
        row = db.get(AppSetting, key)
        if row is None:
            db.add(AppSetting(key=key, value=value))
        else:
            row.value = value
    db.commit()


def clear_api_key(db: Session) -> None:
    row = db.get(AppSetting, KEY_API_KEY)
    if row is not None:
        db.delete(row)
        db.commit()
