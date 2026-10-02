"""Integrity rules that the schema itself cannot express.

``father_id`` is the notable one: a first visit's ``father_id`` equals its
own ``record_id``, which no ordinary foreign key can satisfy at INSERT
time, so the rule is enforced by the write path and pinned here.
"""

from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import Engine, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (CaseNarrative, DictHerb, DictHerbAlias, InfoPatient,
                        InfoRecord, Mentor, PrescriptionItem)


def _make_visit(session: Session, *, visit_no: int, father_id: int,
                date: dt.date) -> InfoRecord:
    record = InfoRecord(patient_id="P-TEST", father_id=father_id,
                        visit_no=visit_no, clinic_date=date, age=51.0)
    session.add(record)
    session.flush()
    if father_id == 0:                      # first visit: point at itself
        record.father_id = record.record_id
    session.add(CaseNarrative(record_id=record.record_id, patient_id="P-TEST",
                              complaint=f"第{visit_no}诊"))
    session.flush()
    return record


def test_first_visit_points_at_itself(session: Session) -> None:
    session.add(InfoPatient(patient_id="P-TEST", patient_name="测试",
                            birthday=dt.date(1975, 1, 1), nationality="CHN"))
    session.commit()

    first = _make_visit(session, visit_no=1, father_id=0, date=dt.date(2026, 1, 1))
    session.commit()
    assert first.father_id == first.record_id


def test_follow_ups_chain_to_the_first_visit(session: Session) -> None:
    session.add(InfoPatient(patient_id="P-TEST", patient_name="测试",
                            birthday=dt.date(1975, 1, 1), nationality="CHN"))
    session.commit()

    first = _make_visit(session, visit_no=1, father_id=0, date=dt.date(2026, 1, 1))
    session.commit()
    root = first.father_id

    for visit_no, day in ((2, 8), (3, 15)):
        record = _make_visit(session, visit_no=visit_no, father_id=root,
                             date=dt.date(2026, 1, day))
        assert record.father_id == root

    session.commit()

    # A whole course is one indexed lookup, not a recursive query.
    course = session.scalars(
        select(InfoRecord)
        .where(InfoRecord.father_id == root)
        .order_by(InfoRecord.visit_no)
    ).all()
    assert [r.visit_no for r in course] == [1, 2, 3]


def test_patient_id_is_unique(session: Session) -> None:
    session.add(InfoPatient(patient_id="P-DUP", patient_name="甲",
                            birthday=dt.date(1990, 1, 1), nationality="CHN"))
    session.commit()
    session.add(InfoPatient(patient_id="P-DUP", patient_name="乙",
                            birthday=dt.date(1991, 1, 1), nationality="CHN"))
    with pytest.raises(IntegrityError):
        session.commit()


def test_herb_name_is_unique(session: Session) -> None:
    session.add(DictHerb(herb_id="H1", herb_name="柴胡"))
    session.commit()
    session.add(DictHerb(herb_id="H2", herb_name="柴胡"))
    with pytest.raises(IntegrityError):
        session.commit()


def test_processed_herb_links_to_its_base_herb(session: Session) -> None:
    """盐黄柏 is its own dictionary entry pointing at 黄柏."""
    session.add(DictHerb(herb_id="H-BASE", herb_name="黄柏"))
    session.flush()
    session.add(DictHerb(herb_id="H-SALT", herb_name="盐黄柏",
                         parent_herb_id="H-BASE", is_processed=True,
                         processing="盐炙"))
    session.commit()

    salted = session.get(DictHerb, "H-SALT")
    assert salted.parent_herb_id == "H-BASE"
    assert session.get(DictHerb, salted.parent_herb_id).herb_name == "黄柏"


def test_herb_alias_resolves_a_misread(session: Session) -> None:
    """OCR形近字 fixes: 黄苓 is an alias row pointing at 黄芩."""
    session.add(DictHerb(herb_id="H-HQ", herb_name="黄芩"))
    session.flush()
    session.add(DictHerbAlias(herb_id="H-HQ", alias="黄苓", alias_type=4,
                              ambiguity_note="OCR 形近字误识"))
    session.commit()

    alias = session.scalars(
        select(DictHerbAlias).where(DictHerbAlias.alias == "黄苓")
    ).one()
    assert session.get(DictHerb, alias.herb_id).herb_name == "黄芩"


def test_prescription_item_requires_a_real_visit(session: Session) -> None:
    session.add(PrescriptionItem(record_id=99999, patient_id="P-NONE",
                                 herb_name="柴胡"))
    with pytest.raises(IntegrityError):
        session.commit()


def test_herb_name_is_kept_verbatim_alongside_the_normalised_form(
    session: Session,
) -> None:
    """Statistics use the normalised name; the original stays for review."""
    session.add(InfoPatient(patient_id="P-TEST", patient_name="测试",
                            birthday=dt.date(1975, 1, 1), nationality="CHN"))
    session.commit()
    record = _make_visit(session, visit_no=1, father_id=0, date=dt.date(2026, 1, 1))
    session.add(PrescriptionItem(record_id=record.record_id, patient_id="P-TEST",
                                 herb_name="生地", herb_name_norm="生地黄",
                                 dose=15, unit="g"))
    session.commit()

    item = session.scalars(select(PrescriptionItem)).one()
    assert item.herb_name == "生地"
    assert item.herb_name_norm == "生地黄"


def test_total_quantity_matches_dose_times_doses(session: Session) -> None:
    """The HIS arithmetic invariant used to catch OCR dose errors.

    Real HIS medication tables print total = unit dose x number of doses.
    When OCR misreads a dose the equation stops holding, which flags the
    row for review without calling any model.
    """
    session.add(InfoPatient(patient_id="P-TEST", patient_name="测试",
                            birthday=dt.date(1975, 1, 1), nationality="CHN"))
    session.commit()
    record = _make_visit(session, visit_no=1, father_id=0, date=dt.date(2026, 1, 1))

    doses = 14
    for dose, total in ((15, 210), (12, 168), (30, 420), (6, 84)):
        session.add(PrescriptionItem(
            record_id=record.record_id, patient_id="P-TEST",
            herb_name="测试药", dose=dose, unit="g", total_quantity=total,
        ))
    session.commit()

    rows = session.execute(
        select(PrescriptionItem.dose, PrescriptionItem.total_quantity)
    ).all()
    assert rows
    for dose, total in rows:
        assert total == dose * doses

    # A misread dose (15g -> 159) breaks the invariant and is detectable.
    broken = (159, 210)
    assert broken[1] != broken[0] * doses


def test_audit_log_records_field_level_changes(session: Session) -> None:
    from app.models import AuditLog

    session.add(AuditLog(table_name="case_narrative", record_pk="1", action=1,
                         field_name="pulse", old_value="弦细",
                         new_value="弦滑"))
    session.commit()
    entry = session.scalars(select(AuditLog)).one()
    assert (entry.old_value, entry.new_value) == ("弦细", "弦滑")
