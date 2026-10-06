"""病案写入服务。

写入顺序对 SQLite 外键至关重要：父表（患者、老师）已存在，本服务只负责
创建就诊及其临床子表。record 行先 flush 以获得 record_id，再写子表。

病程链规则（与 course_id / father_id 契约一致）：
- 初诊（无 parent_record_id）：生成新 course_id（ULID 病案号），
  father_id 指向自身，visit_no = 1
- 复诊（给定 parent_record_id）：继承父记录的 course_id 与 father_id，
  visit_no = 该病案最大 visit_no + 1
"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from ulid import ULID

from .. import schemas
from ..dictionary import resolve_herb
from ..models import (CaseNarrative, Diagnosis, InfoPatient, InfoRecord,
                      PrescriptionItem, Treatment)


def create_record(db: Session, payload: schemas.RecordCreate) -> int:
    # InfoPatient 的主键是整型 id，patient_id 是唯一业务键，须按业务键查
    patient = db.scalar(
        select(InfoPatient).where(InfoPatient.patient_id == payload.patient_id)
    )
    if patient is None:
        raise HTTPException(status_code=404, detail="患者不存在")

    if payload.parent_record_id is not None:
        parent = db.get(InfoRecord, payload.parent_record_id)
        if parent is None:
            raise HTTPException(status_code=404, detail="父病案不存在")
        father_id = parent.father_id
        course_id = parent.course_id
        visit_no = (db.scalar(
            select(func.max(InfoRecord.visit_no)).where(
                InfoRecord.course_id == course_id
            )
        ) or 0) + 1
    else:
        father_id = 0
        course_id = str(ULID())  # 新病案：独立的病案号
        visit_no = 1

    record = InfoRecord(
        patient_id=payload.patient_id,
        course_id=course_id,
        father_id=father_id,
        visit_no=visit_no,
        visit_type=payload.visit_type,
        clinic_date=payload.clinic_date,
        age=payload.age or 0,
        doctor_name=payload.doctor_name,
        mentor_id=payload.mentor_id,
        department=payload.department,
        addr=payload.addr,
    )
    db.add(record)
    db.flush()  # 获得 record_id
    record.father_id = father_id or record.record_id  # 初诊自指

    n = payload.narrative
    db.add(CaseNarrative(
        record_id=record.record_id, patient_id=payload.patient_id,
        complaint=n.complaint, present_illness=n.present_illness,
        past_history=n.past_history, personal_history=n.personal_history,
        allergy_history=n.allergy_history, body_of_tongue=n.body_of_tongue,
        fur_of_tongue=n.fur_of_tongue, pulse=n.pulse, other_cond=n.other_cond,
        physical_exam=n.physical_exam, auxiliary_exam=n.auxiliary_exam,
        notes=n.notes,
    ))

    d = payload.diagnosis
    db.add(Diagnosis(
        record_id=record.record_id, patient_id=payload.patient_id,
        tcm_disease=d.tcm_disease, syndrome=d.syndrome,
        syndrome_id=d.syndrome_id, wm_diagnosis=d.wm_diagnosis,
        patterns_analysis=d.patterns_analysis,
        differential_diagnosis=d.differential_diagnosis, notes=d.notes,
    ))

    t = payload.treatment
    db.add(Treatment(
        record_id=record.record_id, patient_id=payload.patient_id,
        treatment_principle=t.treatment_principle, formula_name=t.formula_name,
        formula_id=t.formula_id, dose_count=t.dose_count, decoction=t.decoction,
        usage=t.usage, advice=t.advice, other_treatment=t.other_treatment,
    ))

    for herb in payload.herbs:
        resolution = resolve_herb(db, herb.herb_name)
        db.add(PrescriptionItem(
            record_id=record.record_id, patient_id=payload.patient_id,
            sequence=herb.sequence, herb_name=herb.herb_name,
            herb_name_norm=resolution.normalised, herb_id=resolution.herb_id,
            dose=herb.dose, unit=herb.unit, processing=herb.processing,
            decoction_note=herb.decoction_note, role=herb.role,
            needs_review=herb.needs_review, confidence=herb.confidence,
        ))

    db.commit()
    return record.record_id
