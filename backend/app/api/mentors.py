"""导师路由：列表、简介详情与增删改。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from ulid import ULID

from .. import schemas
from ..models import (CaseNarrative, Diagnosis, InfoPatient, InfoRecord,
                      LearningNote, Mentor)
from .deps import get_db

router = APIRouter(prefix="/api/mentors", tags=["mentors"])


def _visit_counts(db: Session) -> dict[str, int]:
    rows = db.execute(
        select(InfoRecord.mentor_id, func.count())
        .where(InfoRecord.is_deleted.is_(False), InfoRecord.mentor_id.is_not(None))
        .group_by(InfoRecord.mentor_id)
    ).all()
    return {mid: c for mid, c in rows if mid}


def _note_counts(db: Session) -> dict[str, int]:
    rows = db.execute(
        select(LearningNote.mentor_id, func.count())
        .where(LearningNote.is_deleted.is_(False),
               LearningNote.mentor_id.is_not(None))
        .group_by(LearningNote.mentor_id)
    ).all()
    return {mid: c for mid, c in rows if mid}


def _detail(db: Session, mentor: Mentor) -> schemas.MentorDetail:
    visit_count = db.scalar(
        select(func.count()).where(InfoRecord.mentor_id == mentor.mentor_id,
                                   InfoRecord.is_deleted.is_(False))) or 0
    note_count = db.scalar(
        select(func.count()).where(LearningNote.mentor_id == mentor.mentor_id,
                                   LearningNote.is_deleted.is_(False))) or 0

    top_syndromes = db.execute(
        select(Diagnosis.syndrome, func.count())
        .join(InfoRecord, InfoRecord.record_id == Diagnosis.record_id)
        .where(InfoRecord.mentor_id == mentor.mentor_id,
               InfoRecord.is_deleted.is_(False), Diagnosis.syndrome != "")
        .group_by(Diagnosis.syndrome)
        .order_by(func.count().desc())
        .limit(8)
    ).all()

    recent = db.execute(
        select(InfoRecord, InfoPatient.patient_name,
               CaseNarrative.complaint, Diagnosis.syndrome)
        .join(InfoPatient, InfoPatient.patient_id == InfoRecord.patient_id)
        .outerjoin(CaseNarrative, CaseNarrative.record_id == InfoRecord.record_id)
        .outerjoin(Diagnosis, Diagnosis.record_id == InfoRecord.record_id)
        .where(InfoRecord.mentor_id == mentor.mentor_id,
               InfoRecord.is_deleted.is_(False))
        .order_by(InfoRecord.clinic_date.desc(), InfoRecord.record_id.desc())
        .limit(8)
    ).all()

    return schemas.MentorDetail(
        mentor_id=mentor.mentor_id,
        mentor_name=mentor.mentor_name,
        title=mentor.title,
        affiliation=mentor.affiliation,
        department=mentor.department,
        expertise=mentor.expertise,
        clinic_time=mentor.clinic_time,
        clinic_location=mentor.clinic_location,
        bio=mentor.bio,
        is_primary=bool(mentor.is_primary),
        notes=mentor.notes,
        visit_count=visit_count,
        note_count=note_count,
        top_syndromes=[schemas.MentorSyndrome(syndrome=s, count=c)
                       for s, c in top_syndromes if s],
        recent_records=[schemas.MentorRecordBrief(
            record_id=r.record_id, patient_name=pn,
            clinic_date=str(r.clinic_date),
            complaint=complaint or "", syndrome=syndrome or "",
        ) for r, pn, complaint, syndrome in recent],
    )


@router.get("", response_model=list[schemas.MentorOption])
def list_options(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Mentor).where(Mentor.is_deleted.is_(False))
        .order_by(Mentor.is_primary.desc(), Mentor.mentor_name)
    ).scalars().all()
    return [schemas.MentorOption(mentor_id=m.mentor_id,
                                 mentor_name=m.mentor_name, title=m.title)
            for m in rows]


@router.get("/list", response_model=list[schemas.MentorSummary])
def list_mentors(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Mentor).where(Mentor.is_deleted.is_(False))
        .order_by(Mentor.is_primary.desc(), Mentor.mentor_name)
    ).scalars().all()
    visits = _visit_counts(db)
    notes = _note_counts(db)
    return [schemas.MentorSummary(
        mentor_id=m.mentor_id, mentor_name=m.mentor_name, title=m.title,
        department=m.department, expertise=m.expertise,
        is_primary=bool(m.is_primary),
        visit_count=visits.get(m.mentor_id, 0),
        note_count=notes.get(m.mentor_id, 0),
    ) for m in rows]


@router.post("", response_model=schemas.MentorDetail, status_code=201)
def create_mentor(payload: schemas.MentorUpsert,
                  db: Session = Depends(get_db)):
    mentor = Mentor(mentor_id=str(ULID()), **payload.model_dump())
    db.add(mentor)
    db.commit()
    return _detail(db, mentor)


@router.get("/{mentor_id}", response_model=schemas.MentorDetail)
def get_mentor(mentor_id: str, db: Session = Depends(get_db)):
    mentor = db.get(Mentor, mentor_id)
    if mentor is None or mentor.is_deleted:
        raise HTTPException(status_code=404, detail="导师不存在")
    return _detail(db, mentor)


@router.put("/{mentor_id}", response_model=schemas.MentorDetail)
def update_mentor(mentor_id: str, payload: schemas.MentorUpsert,
                  db: Session = Depends(get_db)):
    mentor = db.get(Mentor, mentor_id)
    if mentor is None or mentor.is_deleted:
        raise HTTPException(status_code=404, detail="导师不存在")
    for key, value in payload.model_dump().items():
        setattr(mentor, key, value)
    db.commit()
    return _detail(db, mentor)


@router.delete("/{mentor_id}", status_code=204)
def delete_mentor(mentor_id: str, db: Session = Depends(get_db)):
    mentor = db.get(Mentor, mentor_id)
    if mentor is None:
        raise HTTPException(status_code=404, detail="导师不存在")
    mentor.is_deleted = True
    db.commit()
