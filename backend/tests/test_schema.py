"""Schema-level checks: the database matches the reviewed specification."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import Engine, inspect, text
from sqlalchemy.orm import Session

from app.models import (CaseNarrative, InfoPatient, InfoRecord,
                        PrescriptionItem)
from app.search import install_search_schema

REPO_ROOT = Path(__file__).resolve().parents[2]

EXPECTED_TABLES = {
    # 主数据
    "info_patient", "info_record", "mentor",
    # 病案主体
    "case_narrative",
    # 诊断与治疗
    "diagnosis", "treatment", "prescription_item",
    # 字典
    "dict_herb", "dict_herb_alias", "dict_syndrome", "dict_formula",
    "dict_term",
    # 跟师学习
    "learning_note", "mentor_comment", "note_record_link",
    # 来源与溯源
    "source_document", "attachment", "ocr_job", "ocr_field_confidence",
    # 系统
    "audit_log", "app_setting",
}


def test_all_expected_tables_exist(engine: Engine) -> None:
    names = set(inspect(engine).get_table_names())
    assert EXPECTED_TABLES <= names, EXPECTED_TABLES - names
    assert len(EXPECTED_TABLES) == 21


def test_tables_removed_by_design_review_stay_removed(engine: Engine) -> None:
    """The free-text redesign must not quietly grow the history tables back."""
    names = set(inspect(engine).get_table_names())
    removed = {
        "complaint_and_present_illness", "chronic_diseases",
        "communicable_diseases_related", "personal_history",
        "menorrhea_and_obstetric_history", "other_history", "hospital_exam",
        "diagnosis_item",
    }
    assert not (removed & names), removed & names


def test_unsigned_tinyint_renders_as_documented(engine: Engine) -> None:
    """Enum columns keep the specification's type name in the DDL."""
    with engine.connect() as connection:
        ddl = connection.execute(text(
            "SELECT sql FROM sqlite_master WHERE name = 'info_record'"
        )).scalar_one()
    assert "UNSIGNED TINYINT" in ddl


def test_foreign_keys_are_enforced(engine: Engine) -> None:
    """SQLite ignores foreign keys unless the pragma is switched on."""
    with engine.connect() as connection:
        assert connection.execute(text("PRAGMA foreign_keys")).scalar_one() == 1

    with Session(engine) as session:
        session.add(InfoRecord(
            patient_id="NO-SUCH-PATIENT", father_id=0,
            clinic_date=__import__("datetime").date(2026, 1, 1), age=30.0,
        ))
        with pytest.raises(Exception):
            session.commit()


def test_soft_delete_column_defaults_to_zero(session: Session) -> None:
    import datetime as dt

    patient = InfoPatient(patient_id="P-SD", patient_name="软删除测试",
                          birthday=dt.date(1990, 1, 1), nationality="CHN")
    session.add(patient)
    session.commit()
    assert patient.is_deleted in (False, 0)


def test_search_schema_is_idempotent(engine: Engine) -> None:
    """init_db may run more than once; installing twice must not fail."""
    install_search_schema(engine)
    install_search_schema(engine)
    names = set(inspect(engine).get_table_names())
    assert "case_search" in names


def test_spec_workbook_matches_models() -> None:
    """The reviewed workbook and the ORM models must not drift apart."""
    spec_path = REPO_ROOT / "docs" / "case-database-spec.xlsx"
    if not spec_path.is_file():
        pytest.skip("structure specification workbook not present")

    from scripts.check_spec_drift import read_spec, render_column_type
    from app.models import Base

    spec = read_spec(spec_path)
    models = {
        name: {c.name: render_column_type(c) for c in table.columns}
        for name, table in Base.metadata.tables.items()
    }
    assert set(spec) == set(models)
    for table in spec:
        assert spec[table] == models[table], table
