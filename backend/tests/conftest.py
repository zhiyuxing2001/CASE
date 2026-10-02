"""Shared pytest fixtures: a fresh database per test."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.db import make_engine
from app.models import (Base, CaseNarrative, Diagnosis, InfoPatient,
                        InfoRecord, Mentor, PrescriptionItem, Treatment)
from app.search import install_search_schema


@pytest.fixture()
def engine(tmp_path: Path) -> Engine:
    eng = make_engine(f"sqlite:///{tmp_path / 'case-test.db'}")
    Base.metadata.create_all(eng)
    install_search_schema(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def session(engine: Engine) -> Session:
    with Session(engine) as sess:
        yield sess


@pytest.fixture()
def sample_case(session: Session) -> int:
    """One complete visit: patient, mentor, narrative, diagnosis, herbs.

    Mirrors the shape of the real handwritten teaching form that drove
    the design — a chief complaint, a free-text history, tongue and pulse,
    a syndrome, a treatment principle and a short prescription.
    """
    session.add(Mentor(mentor_id="M-TEST", mentor_name="测试老师"))
    session.add(InfoPatient(
        patient_id="P-TEST", patient_name="测试患者",
        birthday=dt.date(1975, 1, 1), nationality="CHN", gender=True,
    ))
    session.flush()

    record = InfoRecord(
        patient_id="P-TEST", father_id=0, visit_no=1,
        clinic_date=dt.date(2026, 3, 5), age=51.0, mentor_id="M-TEST",
    )
    session.add(record)
    session.flush()
    record.father_id = record.record_id          # first visit points at itself

    session.add(CaseNarrative(
        record_id=record.record_id, patient_id="P-TEST",
        complaint="胃脘胀痛3月余",
        present_illness="餐后加重，伴嗳气反酸，睡眠欠佳。",
        past_history="高血压7年。",
        body_of_tongue="淡红", fur_of_tongue="薄白", pulse="弦细",
    ))
    session.add(Diagnosis(
        record_id=record.record_id, patient_id="P-TEST",
        tcm_disease="胃脘痛", syndrome="肝胃不和证",
        wm_diagnosis="慢性胃炎", patterns_analysis="湿热瘀阻之象",
    ))
    session.add(Treatment(
        record_id=record.record_id, patient_id="P-TEST",
        treatment_principle="疏肝理气和胃", formula_name="柴胡疏肝散",
        dose_count=7, decoction="水煎服", usage="日一剂，分早晚温服",
    ))
    for index, (herb, dose) in enumerate(
        [("柴胡", 10), ("白芍", 15), ("枳壳", 10), ("甘草", 6)]
    ):
        session.add(PrescriptionItem(
            record_id=record.record_id, patient_id="P-TEST", sequence=index,
            herb_name=herb, herb_name_norm=herb, dose=dose, unit="g",
        ))
    session.commit()
    return record.record_id
