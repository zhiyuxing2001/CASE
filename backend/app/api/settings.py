"""应用设置路由：DeepSeek API Key 等。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..llm import reset_router
from ..services import settings_service
from .deps import get_db

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/ai", response_model=schemas.AiSettingsOut)
def get_ai_settings(db: Session = Depends(get_db)) -> schemas.AiSettingsOut:
    return schemas.AiSettingsOut(**settings_service.get_ai_config(db))


@router.put("/ai", response_model=schemas.AiSettingsOut)
def update_ai_settings(
    payload: schemas.AiSettingsUpdate,
    db: Session = Depends(get_db),
) -> schemas.AiSettingsOut:
    settings_service.save_ai_config(db, payload.api_key,
                                    payload.base_url, payload.model)
    reset_router()  # 配置改动立即生效
    return schemas.AiSettingsOut(**settings_service.get_ai_config(db))


@router.delete("/ai", response_model=schemas.AiSettingsOut)
def clear_ai_settings(db: Session = Depends(get_db)) -> schemas.AiSettingsOut:
    settings_service.clear_api_key(db)
    reset_router()
    return schemas.AiSettingsOut(**settings_service.get_ai_config(db))
