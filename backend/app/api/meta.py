"""元数据路由：带教老师与患者（供筛选与联想）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from ulid import ULID

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


@router.get("/patients/{patient_id}", response_model=schemas.PatientBrief)
def get_patient(patient_id: str,
                db: Session = Depends(get_db)) -> schemas.PatientBrief:
    patient = db.scalar(select(InfoPatient).where(
        InfoPatient.patient_id == patient_id))
    if patient is None:
        raise HTTPException(status_code=404, detail="患者不存在")
    return schemas.PatientBrief(
        patient_id=patient.patient_id,
        patient_name=patient.patient_name,
        gender=bool(patient.gender),
    )


@router.post("/patients", response_model=schemas.PatientCreated,
             status_code=201)
def create_patient(
    payload: schemas.PatientCreate,
    db: Session = Depends(get_db),
) -> schemas.PatientCreated:
    patient_id = str(ULID())
    db.add(InfoPatient(
        patient_id=patient_id,
        patient_name=payload.patient_name,
        gender=payload.gender,
        birthday=payload.birthday,
        nationality=payload.nationality,
        id_no=payload.id_no,
        job=payload.job,
        tel=payload.tel,
        addr_region=payload.addr_region,
    ))
    db.commit()
    return schemas.PatientCreated(patient_id=patient_id)
