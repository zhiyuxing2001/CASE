"""Audit trail behaviour: every change to a case is recorded."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.audit import DELETE, INSERT, UPDATE, enable_audit, suspend_audit
from app.models import AuditLog, CaseNarrative, InfoPatient


def _factory(engine: Engine) -> sessionmaker[Session]:
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    enable_audit(factory)
    return factory


def _seed_patient(session: Session) -> None:
    session.add(InfoPatient(patient_id="P-AUDIT", patient_name="审计测试",
                            birthday=dt.date(1980, 1, 1), nationality="CHN"))
    session.commit()


def test_insert_is_recorded(engine: Engine) -> None:
    factory = _factory(engine)
    with factory() as session:
        _seed_patient(session)

    with factory() as session:
        rows = session.scalars(
            select(AuditLog).where(AuditLog.table_name == "info_patient")
        ).all()
        assert len(rows) == 1
        assert rows[0].action == INSERT
        # info_patient declares the integer `id` as its primary key;
        # `patient_id` is a separate unique business key used for joins.
        assert rows[0].record_pk == "1"


def test_update_records_field_level_old_and_new(engine: Engine) -> None:
    factory = _factory(engine)
    with factory() as session:
        _seed_patient(session)

    with factory() as session:
        narrative = CaseNarrative(record_id=1, patient_id="P-AUDIT",
                                  complaint="胃脘胀痛", pulse="弦细")
        session.add(narrative)
        session.commit()

    with factory() as session:
        narrative = session.get(CaseNarrative, 1)
        narrative.pulse = "弦滑"
        session.commit()

    with factory() as session:
        entry = session.scalars(
            select(AuditLog).where(AuditLog.action == UPDATE,
                                   AuditLog.field_name == "pulse")
        ).one()
        assert entry.table_name == "case_narrative"
        assert entry.record_pk == "1"
        assert entry.old_value == "弦细"
        assert entry.new_value == "弦滑"


def test_delete_is_recorded(engine: Engine) -> None:
    factory = _factory(engine)
    with factory() as session:
        _seed_patient(session)

    with factory() as session:
        session.add(CaseNarrative(record_id=1, patient_id="P-AUDIT",
                                  complaint="待删除"))
        session.commit()

    with factory() as session:
        session.delete(session.get(CaseNarrative, 1))
        session.commit()

    with factory() as session:
        deleted = session.scalars(
            select(AuditLog).where(AuditLog.action == DELETE)
        ).all()
        assert any(row.table_name == "case_narrative" for row in deleted)


def test_unaudited_tables_produce_no_rows(engine: Engine) -> None:
    """Dictionary seeding and OCR bookkeeping must not flood the log."""
    from app.models import DictHerb

    factory = _factory(engine)
    with factory() as session:
        session.add(DictHerb(herb_id="H1", herb_name="柴胡"))
        session.commit()

    with factory() as session:
        assert session.scalars(
            select(AuditLog).where(AuditLog.table_name == "dict_herb")
        ).all() == []


def test_audit_can_be_suspended_for_bulk_import(engine: Engine) -> None:
    factory = _factory(engine)
    with factory() as session:
        with suspend_audit(session):
            session.add(InfoPatient(patient_id="P-BULK", patient_name="批量",
                                    birthday=dt.date(1990, 1, 1),
                                    nationality="CHN"))
            session.commit()

    with factory() as session:
        assert session.scalars(
            select(AuditLog).where(AuditLog.record_pk == "P-BULK")
        ).all() == []


def test_multiple_field_changes_produce_one_row_each(engine: Engine) -> None:
    factory = _factory(engine)
    with factory() as session:
        _seed_patient(session)

    with factory() as session:
        session.add(CaseNarrative(record_id=1, patient_id="P-AUDIT",
                                  complaint="初诊", pulse="弦细"))
        session.commit()

    with factory() as session:
        narrative = session.get(CaseNarrative, 1)
        narrative.pulse = "弦滑"
        narrative.body_of_tongue = "红"
        session.commit()

    with factory() as session:
        fields = {
            row.field_name
            for row in session.scalars(
                select(AuditLog).where(AuditLog.action == UPDATE)
            )
        }
        assert {"pulse", "body_of_tongue"} <= fields
