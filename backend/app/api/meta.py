"""元数据路由：带教老师与患者（供筛选与联想）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import schemas
from ..models import InfoPatient, Mentor
from .deps import get_db

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/mentors", response_model=list[schemas.MentorOption])
def list_mentors(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Mentor)
        .where(Mentor.is_deleted.is_(False))
        .order_by(Mentor.is_primary.desc(), Mentor.mentor_name)
    ).scalars().all()
    return [
        schemas.MentorOption(mentor_id=m.mentor_id, mentor_name=m.mentor_name,
                             title=m.title)
        for m in rows
    ]


@router.get("/patients", response_model=list[schemas.PatientOption])
def list_patients(
    q: str = "",
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    stmt = select(InfoPatient).where(InfoPatient.is_deleted.is_(False))
    if q:
        stmt = stmt.where(InfoPatient.patient_name.like(f"%{q}%"))
    rows = db.execute(
        stmt.order_by(InfoPatient.patient_name).limit(limit)
    ).scalars().all()
    return [
        schemas.PatientOption(patient_id=p.patient_id,
                              patient_name=p.patient_name,
                              gender=bool(p.gender))
        for p in rows
    ]
