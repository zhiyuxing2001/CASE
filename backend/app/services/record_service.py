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
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session
from ulid import ULID

from .. import schemas
from ..dictionary import collect_dictionary, resolve_herb
from ..models import (CaseNarrative, Diagnosis, ExamReport, InfoPatient,
                      InfoRecord, LabResult, PrescriptionItem, Treatment)


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
        usage=t.usage, advice=t.advice, western_medicine=t.western_medicine,
        other_treatment=t.other_treatment,
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

    for lab in payload.lab_results:
        db.add(LabResult(
            record_id=record.record_id, patient_id=payload.patient_id,
            item_name=lab.item_name,
            result_value=lab.result_value, unit=lab.unit,
            reference_range=lab.reference_range,
            abnormal_flag=lab.abnormal_flag,
            needs_review=lab.needs_review, confidence=lab.confidence,
        ))

    for exam in payload.exams:
        db.add(ExamReport(
            record_id=record.record_id, patient_id=payload.patient_id,
            item_name=exam.item_name, finding=exam.finding,
            conclusion=exam.conclusion,
            needs_review=exam.needs_review, confidence=exam.confidence,
        ))

    collect_dictionary(db, payload)  # 半自动收集新药名/证型/术语

    db.commit()
    return record.record_id


def _apply(obj, data: dict) -> None:
    """把 payload 字段覆盖到 ORM 对象上（仅覆盖 payload 中的字段）。"""
    for key, value in data.items():
        setattr(obj, key, value)


def update_record(db: Session, record_id: int,
                  payload: schemas.RecordCreate) -> int:
    """编辑已有就诊：覆盖元数据、病史、诊断、治疗，药味整体替换。

    不修改病程结构（patient_id / course_id / father_id / visit_no）。
    """
    record = db.get(InfoRecord, record_id)
    if record is None or record.is_deleted:
        raise HTTPException(status_code=404, detail="病案不存在")

    record.clinic_date = payload.clinic_date
    record.visit_type = payload.visit_type
    record.age = payload.age or 0
    record.doctor_name = payload.doctor_name
    record.mentor_id = payload.mentor_id
    record.department = payload.department
    record.addr = payload.addr

    narrative = db.get(CaseNarrative, record_id)
    if narrative is None:
        narrative = CaseNarrative(record_id=record_id, patient_id=record.patient_id)
        db.add(narrative)
    _apply(narrative, payload.narrative.model_dump())

    diagnosis = db.get(Diagnosis, record_id)
    if diagnosis is None:
        diagnosis = Diagnosis(record_id=record_id, patient_id=record.patient_id)
        db.add(diagnosis)
    _apply(diagnosis, payload.diagnosis.model_dump())

    treatment = db.get(Treatment, record_id)
    if treatment is None:
        treatment = Treatment(record_id=record_id, patient_id=record.patient_id)
        db.add(treatment)
    _apply(treatment, payload.treatment.model_dump())

    _replace_clinical_items(db, record, payload.herbs,
                            payload.lab_results, payload.exams)

    collect_dictionary(db, payload)  # 半自动收集新药名/证型/术语

    db.commit()
    return record_id


def _replace_clinical_items(db: Session, record: InfoRecord,
                            herbs, lab_results, exams) -> None:
    """整体替换药味、检验与检查（不触碰病史/诊断/治疗元数据）。"""
    rid = record.record_id
    pid = record.patient_id

    db.execute(delete(PrescriptionItem).where(PrescriptionItem.record_id == rid))
    for herb in herbs:
        resolution = resolve_herb(db, herb.herb_name)
        db.add(PrescriptionItem(
            record_id=rid, patient_id=pid,
            sequence=herb.sequence, herb_name=herb.herb_name,
            herb_name_norm=resolution.normalised, herb_id=resolution.herb_id,
            dose=herb.dose, unit=herb.unit, processing=herb.processing,
            decoction_note=herb.decoction_note, role=herb.role,
            needs_review=herb.needs_review, confidence=herb.confidence,
        ))

    db.execute(delete(LabResult).where(LabResult.record_id == rid))
    for lab in lab_results:
        db.add(LabResult(
            record_id=rid, patient_id=pid,
            item_name=lab.item_name,
            result_value=lab.result_value, unit=lab.unit,
            reference_range=lab.reference_range,
            abnormal_flag=lab.abnormal_flag,
            needs_review=lab.needs_review, confidence=lab.confidence,
        ))

    db.execute(delete(ExamReport).where(ExamReport.record_id == rid))
    for exam in exams:
        db.add(ExamReport(
            record_id=rid, patient_id=pid,
            item_name=exam.item_name, finding=exam.finding,
            conclusion=exam.conclusion,
            needs_review=exam.needs_review, confidence=exam.confidence,
        ))


def review_record(db: Session, record_id: int,
                  payload: schemas.RecordReviewRequest) -> int:
    """校对：仅整体替换药味与检验检查，病史/诊断/治疗保持不变。

    用于待校对病案——用户修正并确认 flagged 项后，清除 needs_review。
    """
    record = db.get(InfoRecord, record_id)
    if record is None or record.is_deleted:
        raise HTTPException(status_code=404, detail="病案不存在")

    _replace_clinical_items(db, record, payload.herbs,
                            payload.lab_results, payload.exams)
    db.commit()
    return record_id
