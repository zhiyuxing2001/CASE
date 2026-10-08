"""提示词维护路由：查看、覆盖与恢复默认系统提示词。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..llm import prompts
from ..models import AppSetting
from .deps import get_db

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


def _setting_key(key: str) -> str:
    return f"prompt_{key}"


def _out(key: str, current: str, is_modified: bool) -> schemas.PromptOut:
    name, description, default = prompts.SYSTEM_PROMPTS[key]
    return schemas.PromptOut(
        key=key, name=name, description=description,
        current=current, default=default, is_modified=is_modified,
    )


@router.get("", response_model=list[schemas.PromptOut])
def list_prompts(db: Session = Depends(get_db)):
    result: list[schemas.PromptOut] = []
    for key in prompts.SYSTEM_PROMPTS:
        row = db.get(AppSetting, _setting_key(key))
        current = row.value if row and row.value else ""
        result.append(_out(key, current or prompts.SYSTEM_PROMPTS[key][2],
                           is_modified=bool(current)))
    return result


@router.put("/{key}", response_model=schemas.PromptOut)
def update_prompt(key: str, payload: schemas.PromptUpdate,
                  db: Session = Depends(get_db)):
    if key not in prompts.SYSTEM_PROMPTS:
        raise HTTPException(status_code=404, detail="提示词不存在")
    row = db.get(AppSetting, _setting_key(key))
    if row is None:
        db.add(AppSetting(key=_setting_key(key), value=payload.value))
    else:
        row.value = payload.value
    db.commit()
    return _out(key, payload.value, is_modified=bool(payload.value.strip()))


@router.delete("/{key}", status_code=204)
def reset_prompt(key: str, db: Session = Depends(get_db)):
    if key not in prompts.SYSTEM_PROMPTS:
        raise HTTPException(status_code=404, detail="提示词不存在")
    row = db.get(AppSetting, _setting_key(key))
    if row is not None:
        db.delete(row)
        db.commit()
