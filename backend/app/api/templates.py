"""界面模板路由：模板的增删改查。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from ulid import ULID

from .. import schemas
from ..models import DictTemplate
from .deps import get_db

router = APIRouter(prefix="/api/templates", tags=["templates"])


def _out(t: DictTemplate) -> schemas.TemplateOut:
    return schemas.TemplateOut(
        template_id=t.template_id,
        name=t.name,
        doc_type=t.doc_type or 0,
        field_anchors=[schemas.TemplateAnchor(**a) for a in (t.field_anchors or [])],
        table_columns=[schemas.TemplateAnchor(**a) for a in (t.table_columns or [])],
    )


@router.get("", response_model=list[schemas.TemplateOut])
def list_templates(db: Session = Depends(get_db)):
    rows = db.execute(
        select(DictTemplate).where(DictTemplate.is_active.is_(True))
        .order_by(DictTemplate.doc_type, DictTemplate.name)
    ).scalars().all()
    return [_out(t) for t in rows]


@router.get("/{template_id}", response_model=schemas.TemplateOut)
def get_template(template_id: str, db: Session = Depends(get_db)):
    template = db.get(DictTemplate, template_id)
    if template is None or template.is_active is False:
        raise HTTPException(status_code=404, detail="模板不存在")
    return _out(template)


@router.post("", response_model=schemas.TemplateOut, status_code=201)
def create_template(payload: schemas.TemplateUpsert,
                    db: Session = Depends(get_db)):
    template = DictTemplate(
        template_id=str(ULID()),
        name=payload.name,
        doc_type=payload.doc_type,
        field_anchors=[a.model_dump() for a in payload.field_anchors],
        table_columns=[a.model_dump() for a in payload.table_columns],
    )
    db.add(template)
    db.commit()
    return _out(template)


@router.put("/{template_id}", response_model=schemas.TemplateOut)
def update_template(template_id: str, payload: schemas.TemplateUpsert,
                    db: Session = Depends(get_db)):
    template = db.get(DictTemplate, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="模板不存在")
    template.name = payload.name
    template.doc_type = payload.doc_type
    template.field_anchors = [a.model_dump() for a in payload.field_anchors]
    template.table_columns = [a.model_dump() for a in payload.table_columns]
    db.commit()
    return _out(template)


@router.delete("/{template_id}", status_code=204)
def delete_template(template_id: str, db: Session = Depends(get_db)):
    template = db.get(DictTemplate, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="模板不存在")
    template.is_active = False
    db.commit()
