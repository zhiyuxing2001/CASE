"""End-to-end walk through what the archive has to do.

Uses the shape of the real HIS export that drove the design: one patient,
five visits, a printed prescription whose herbs and doses were recognised
from a scan, and a Chinese full-text search over the result.

The dose/quantity arithmetic is included because it is the one check that
catches OCR dose errors without calling a model.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import Engine, func, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.audit import enable_audit
from app.dictionary import resolve_herb
from app.models import (Base, CaseNarrative, Diagnosis, DictHerb, DictHerbAlias,
                        InfoPatient, InfoRecord, Mentor, PrescriptionItem,
                        Treatment)
from app.search import (install_search_schema, rebuild_search_index,
                        search_cases)
from app.seed import seed_dictionaries

# One visit's prescription as recognised from the printed HIS table.
# unit dose and the printed total are both recorded.
PRESCRIPTION = [
    ("黄芩片", 15, 210), ("盐黄柏", 15, 210), ("苦参", 12, 168),
    ("金银花", 9, 126), ("浮萍", 15, 210), ("醋莪术", 12, 168),
    ("醋三棱", 15, 210), ("茯苓", 30, 420), ("薏苡仁", 30, 420),
    ("莲子心", 12, 168), ("炒酸枣仁", 15, 210), ("砂烫枳实", 12, 168),
    ("醋延胡索", 12, 168), ("甘草片", 6, 84),
]
DOSES_PER_COURSE = 14


def _build(engine: Engine, session: Session) -> int:
    """Create one patient with a five-visit course; return the root visit id."""
    session.add(Mentor(mentor_id="M-E2E", mentor_name="带教老师"))
    session.add(InfoPatient(patient_id="P-E2E", patient_name="病例甲",
                            birthday=dt.date(1971, 1, 25), nationality="CHN",
                            gender=False))
    session.flush()

    root = None
    for visit_no in range(1, 6):
        record = InfoRecord(
            patient_id="P-E2E", father_id=root or 0, visit_no=visit_no,
            visit_type=0 if visit_no == 1 else 1,
            clinic_date=dt.date(2026, 3, 31) + dt.timedelta(days=14 * (visit_no - 1)),
            age=55.0, mentor_id="M-E2E", department="消化科门诊",
        )
        session.add(record)
        session.flush()
        record.father_id = root or record.record_id
        root = root or record.record_id

        session.add(CaseNarrative(
            record_id=record.record_id, patient_id="P-E2E",
            complaint="带状疱疹后遗神经痛3月" if visit_no == 1 else "服药后复诊",
            present_illness="左侧腹皮疹疼痛，遗留神经疼痛，刺痛，睡眠差。",
            past_history="发现血糖升高2年，高血压病史。",
            body_of_tongue="暗红稍紫", fur_of_tongue="苔稍黄", pulse="弦滑稍数",
            auxiliary_exam="2026-03-25 外院生化：空腹血糖7.5mmol/L，HbA1c 6.9%。",
        ))
        session.add(Diagnosis(
            record_id=record.record_id, patient_id="P-E2E",
            syndrome="湿热瘀阻证", wm_diagnosis="带状疱疹后神经痛；睡眠障碍；2型糖尿病",
            patterns_analysis="舌暗红苔黄腻，湿热瘀阻之象。",
        ))
        session.add(Treatment(
            record_id=record.record_id, patient_id="P-E2E",
            treatment_principle="清热祛湿，理气活血止痛",
            dose_count=DOSES_PER_COURSE, decoction="机械煎药（含2袋）",
            usage="每天一次（10点）",
        ))
        for index, (herb, dose, total) in enumerate(PRESCRIPTION):
            # Resolve against the dictionary the way the entry form does:
            # keep the original wording, store the standard name alongside.
            resolution = resolve_herb(session, herb)
            session.add(PrescriptionItem(
                record_id=record.record_id, patient_id="P-E2E",
                sequence=index, herb_name=herb,
                herb_name_norm=resolution.normalised,
                herb_id=resolution.herb_id,
                dose=dose, unit="g", total_quantity=total, frequency="BID",
            ))
    session.commit()
    return root


def test_full_archive_workflow(engine: Engine) -> None:
    Base.metadata.create_all(engine)
    install_search_schema(engine)
    seed_dictionaries(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    enable_audit(factory)

    with factory() as session:
        root = _build(engine, session)

    with factory() as session:
        # --- the course hangs together ---
        visits = session.scalars(
            select(InfoRecord).where(InfoRecord.father_id == root)
            .order_by(InfoRecord.visit_no)
        ).all()
        assert [v.visit_no for v in visits] == [1, 2, 3, 4, 5]

        # --- the prescription survived in full, on every visit ---
        count = session.scalar(
            select(func.count()).select_from(PrescriptionItem)
            .where(PrescriptionItem.record_id == root)
        )
        assert count == len(PRESCRIPTION)

        # --- the HIS arithmetic invariant holds, so OCR doses are checkable ---
        rows = session.execute(
            select(PrescriptionItem.herb_name, PrescriptionItem.dose,
                   PrescriptionItem.total_quantity)
        ).all()
        for _herb, dose, total in rows:
            assert total == dose * DOSES_PER_COURSE

        # --- herb names resolve against the seeded dictionary ---
        unresolved = session.scalars(
            select(PrescriptionItem.herb_name)
            .where(PrescriptionItem.herb_id.is_(None))
        ).all()
        assert unresolved == [], f"字典未覆盖: {set(unresolved)}"

        # --- and a misread name can be traced back to the right herb ---
        misread = session.scalars(
            select(DictHerb.herb_name)
            .join(DictHerbAlias, DictHerbAlias.herb_id == DictHerb.herb_id)
            .where(DictHerbAlias.alias == "黄苓")
        ).one()
        assert misread == "黄芩"

        # --- search reaches every part of the record ---
        for term in ("带状疱疹", "湿热瘀阻证", "清热祛湿", "醋延胡索", "弦滑"):
            assert search_cases(session, term), f"检索不到：{term}"

        # --- and the two-character pitfall is handled ---
        assert search_cases(session, "弦细") == []
        assert search_cases(session, "弦滑")

    # --- the index can be rebuilt from the base tables at any time ---
    with engine.connect() as connection:
        connection.exec_driver_sql("DELETE FROM case_search")
    assert rebuild_search_index(engine) == 5
    with factory() as session:
        assert search_cases(session, "带状疱疹")
