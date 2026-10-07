"""病案记录路由：列表、详情、病程。"""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import schemas
from ..models import (AuditLog, CaseNarrative, Diagnosis, InfoPatient, InfoRecord,
                      Mentor, PrescriptionItem, Treatment)
from ..search import search_cases
from ..services.record_service import create_record
from .deps import get_db

router = APIRouter(prefix="/api/records", tags=["records"])


def _summary_query():
    herb_count = (
        select(func.count(PrescriptionItem.item_id))
        .where(PrescriptionItem.record_id == InfoRecord.record_id)
        .correlate(InfoRecord)
        .scalar_subquery()
    )
    needs_review = (
        select(func.count(PrescriptionItem.item_id))
        .where(
            PrescriptionItem.record_id == InfoRecord.record_id,
            PrescriptionItem.needs_review.is_(True),
        )
        .correlate(InfoRecord)
        .scalar_subquery()
    )
    return (
        select(
            InfoRecord.record_id,
            InfoRecord.clinic_date,
            InfoRecord.visit_no,
            InfoRecord.visit_type,
            InfoRecord.patient_id,
            InfoPatient.patient_name,
            CaseNarrative.complaint,
            Diagnosis.syndrome,
            Diagnosis.tcm_disease,
            herb_count.label("herb_count"),
            Mentor.mentor_name,
            (needs_review > 0).label("needs_review"),
        )
        .join(InfoPatient, InfoPatient.patient_id == InfoRecord.patient_id)
        .outerjoin(CaseNarrative, CaseNarrative.record_id == InfoRecord.record_id)
        .outerjoin(Diagnosis, Diagnosis.record_id == InfoRecord.record_id)
        .outerjoin(Mentor, Mentor.mentor_id == InfoRecord.mentor_id)
        .where(InfoRecord.is_deleted.is_(False))
    )


def _apply_filters(stmt, *, syndrome, herb, mentor_id, patient_id,
                   date_from, date_to, visit_type):
    if syndrome:
        stmt = stmt.where(Diagnosis.syndrome.like(f"%{syndrome}%"))
    if herb:
        stmt = stmt.where(
            InfoRecord.record_id.in_(
                select(PrescriptionItem.record_id).where(
                    PrescriptionItem.herb_name.like(f"%{herb}%")
                )
            )
        )
    if mentor_id:
        stmt = stmt.where(InfoRecord.mentor_id == mentor_id)
    if patient_id:
        stmt = stmt.where(InfoRecord.patient_id == patient_id)
    if date_from:
        stmt = stmt.where(InfoRecord.clinic_date >= date_from)
    if date_to:
        stmt = stmt.where(InfoRecord.clinic_date <= date_to)
    if visit_type is not None:
        stmt = stmt.where(InfoRecord.visit_type == visit_type)
    return stmt


def _row_to_summary(row) -> schemas.RecordSummary:
    return schemas.RecordSummary(
        record_id=row.record_id,
        clinic_date=row.clinic_date,
        visit_no=row.visit_no,
        visit_type=row.visit_type or 0,
        patient_id=row.patient_id,
        patient_name=row.patient_name or "",
        complaint=row.complaint or "",
        syndrome=row.syndrome or "",
        tcm_disease=row.tcm_disease or "",
        herb_count=row.herb_count or 0,
        mentor_name=row.mentor_name or "",
        needs_review=bool(row.needs_review),
    )


@router.get("", response_model=schemas.RecordList)
def list_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str = "",
    syndrome: str = "",
    herb: str = "",
    mentor_id: str = "",
    patient_id: str = "",
    date_from: date | None = None,
    date_to: date | None = None,
    visit_type: int | None = None,
    db: Session = Depends(get_db),
) -> schemas.RecordList:
    stmt = _apply_filters(
        _summary_query(),
        syndrome=syndrome, herb=herb, mentor_id=mentor_id,
        patient_id=patient_id, date_from=date_from, date_to=date_to,
        visit_type=visit_type,
    )

    # 全文检索：先由 FTS/LIKE 路由拿到命中的 record_id
    if q:
        hits = search_cases(db, q, limit=1000)
        ids = [h["record_id"] for h in hits]
        if not ids:
            return schemas.RecordList(total=0, page=page, page_size=page_size,
                                      items=[])
        stmt = stmt.where(InfoRecord.record_id.in_(ids))

    total = db.scalar(
        select(func.count()).select_from(stmt.subquery())
    ) or 0

    rows = db.execute(
        stmt.order_by(InfoRecord.clinic_date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return schemas.RecordList(
        total=total,
        page=page,
        page_size=page_size,
        items=[_row_to_summary(row) for row in rows],
    )


@router.get("/{record_id}", response_model=schemas.RecordDetail)
def get_record(record_id: int, db: Session = Depends(get_db)) -> schemas.RecordDetail:
    record = db.get(InfoRecord, record_id)
    if record is None or record.is_deleted:
        raise HTTPException(status_code=404, detail="病案不存在")

    patient = db.scalar(
        select(InfoPatient).where(InfoPatient.patient_id == record.patient_id)
    )
    narrative = db.get(CaseNarrative, record_id)
    diagnosis = db.get(Diagnosis, record_id)
    treatment = db.get(Treatment, record_id)

    herbs = db.execute(
        select(PrescriptionItem)
        .where(PrescriptionItem.record_id == record_id)
        .order_by(PrescriptionItem.sequence)
    ).scalars().all()

    course_rows = db.execute(
        select(InfoRecord, CaseNarrative.complaint, Diagnosis.syndrome)
        .outerjoin(CaseNarrative, CaseNarrative.record_id == InfoRecord.record_id)
        .outerjoin(Diagnosis, Diagnosis.record_id == InfoRecord.record_id)
        .where(InfoRecord.father_id == record.father_id,
               InfoRecord.is_deleted.is_(False))
        .order_by(InfoRecord.visit_no)
    ).all()

    def _row(obj) -> dict[str, Any]:
        return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}

    def _iso(obj, key: str) -> Any:
        value = getattr(obj, key, None)
        return value.isoformat() if value is not None else None

    # 首诊病案文本：既往史、个人史、过敏史等“只记一次”的字段取自首诊
    first_record = course_rows[0][0] if course_rows else record
    first_narrative = db.get(CaseNarrative, first_record.record_id)

    return schemas.RecordDetail(
        record={**_row(record), "clinic_date": _iso(record, "clinic_date")},
        patient=schemas.PatientBrief(
            patient_id=patient.patient_id,
            patient_name=patient.patient_name,
            gender=bool(patient.gender),
            age=record.age,
        ),
        narrative={} if narrative is None else {
            c.name: getattr(narrative, c.name) for c in narrative.__table__.columns
        },
        first_narrative={} if first_narrative is None else {
            c.name: getattr(first_narrative, c.name)
            for c in first_narrative.__table__.columns
        },
        diagnosis={} if diagnosis is None else {
            c.name: getattr(diagnosis, c.name) for c in diagnosis.__table__.columns
        },
        treatment={} if treatment is None else {
            c.name: getattr(treatment, c.name) for c in treatment.__table__.columns
        },
        herbs=[schemas.HerbItem(
            sequence=h.sequence, herb_name=h.herb_name,
            herb_name_norm=h.herb_name_norm, herb_id=h.herb_id,
            dose=h.dose, unit=h.unit, processing=h.processing,
            decoction_note=h.decoction_note, role=h.role,
            needs_review=bool(h.needs_review),
        ) for h in herbs],
        course=[
            {**_row(v), "clinic_date": _iso(v, "clinic_date"),
             "complaint": complaint or "", "syndrome": syndrome or ""}
            for v, complaint, syndrome in course_rows
        ],
    )


@router.get("/{record_id}/course")
def get_course(record_id: int, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    record = db.get(InfoRecord, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="病案不存在")

    visits = db.execute(
        select(InfoRecord)
        .where(InfoRecord.father_id == record.father_id,
               InfoRecord.is_deleted.is_(False))
        .order_by(InfoRecord.visit_no)
    ).scalars().all()

    return [
        {
            "record_id": v.record_id,
            "clinic_date": v.clinic_date.isoformat(),
            "visit_no": v.visit_no,
            "visit_type": v.visit_type or 0,
        }
        for v in visits
    ]


@router.post("", response_model=schemas.RecordCreated, status_code=201)
def create_record_endpoint(
    payload: schemas.RecordCreate,
    db: Session = Depends(get_db),
) -> schemas.RecordCreated:
    record_id = create_record(db, payload)
    return schemas.RecordCreated(record_id=record_id)


_AUDITED_TABLES = ("info_record", "case_narrative", "diagnosis", "treatment",
                   "prescription_item")


@router.get("/{record_id}/history", response_model=list[schemas.AuditEntry])
def get_history(record_id: int, db: Session = Depends(get_db)) -> list[schemas.AuditEntry]:
    """该病案关联的字段级修改历史。

    prescription_item 的主键是 item_id，需先查出该病案的全部药味主键，
    再与 record_id 一并作为 record_pk 过滤。
    """
    item_ids = [
        i for i in db.execute(
            select(PrescriptionItem.item_id).where(
                PrescriptionItem.record_id == record_id)
        ).scalars()
    ]
    pks = {str(record_id)} | {str(i) for i in item_ids}

    rows = db.execute(
        select(AuditLog)
        .where(AuditLog.record_pk.in_(pks),
               AuditLog.table_name.in_(_AUDITED_TABLES))
        .order_by(AuditLog.changed_at.desc())
        .limit(200)
    ).scalars().all()

    return [
        schemas.AuditEntry(
            table_name=row.table_name,
            action=row.action,
            field_name=row.field_name,
            old_value=row.old_value,
            new_value=row.new_value,
            changed_at=row.changed_at.isoformat(sep=" "),
            note=row.note,
        )
        for row in rows
    ]
