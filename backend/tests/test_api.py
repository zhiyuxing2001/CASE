"""API 层集成测试：患者与病案的写入、病程链、药名归一。

重点回归三件事：InfoPatient 必须按业务键 patient_id 查询（其主键是整型
id）；初诊 father_id 自指、复诊接续 visit_no；OCR 错字药名在写入时归一到
字典标准名。
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_db
from app.audit import enable_audit
from app.main import app
from app.models import Mentor
from app.seed import seed_dictionaries


def _make_client(engine: Engine) -> TestClient:
    with Session(engine) as session:
        session.add(Mentor(mentor_id="M-API", mentor_name="接口老师"))
        session.commit()

    # 与生产 SessionLocal 对齐：挂审计监听，确保写路径产生字段级留痕
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    enable_audit(factory)

    def override_get_db():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def _cleanup() -> None:
    app.dependency_overrides.pop(get_db, None)


def test_create_patient_and_full_record(engine: Engine) -> None:
    seed_dictionaries(engine)
    client = _make_client(engine)
    try:
        r = client.post("/api/patients", json={
            "patient_name": "接口测试患者", "gender": True,
            "birthday": "1970-03-15",
        })
        assert r.status_code == 201
        pid = r.json()["patient_id"]

        r = client.post("/api/records", json={
            "patient_id": pid, "clinic_date": "2026-07-01", "age": 56.0,
            "mentor_id": "M-API",
            "narrative": {"complaint": "腹胀纳呆2周", "pulse": "濡缓"},
            "diagnosis": {"tcm_disease": "痞满", "syndrome": "脾胃虚弱证"},
            "treatment": {"treatment_principle": "健脾和胃", "dose_count": 7},
            "herbs": [
                {"herb_name": "党参", "dose": 15, "sequence": 0},
                {"herb_name": "黄苓", "dose": 9, "sequence": 1},  # OCR 错字
            ],
        })
        assert r.status_code == 201
        rid = r.json()["record_id"]

        detail = client.get(f"/api/records/{rid}").json()
        assert [h["herb_name_norm"] for h in detail["herbs"]] == ["党参", "黄芩"]
        assert detail["record"]["visit_no"] == 1

        # 复诊
        r = client.post("/api/records", json={
            "patient_id": pid, "clinic_date": "2026-07-15", "age": 56.0,
            "visit_type": 1, "parent_record_id": rid,
            "narrative": {"complaint": "服药后复诊"},
            "treatment": {"treatment_principle": "健脾和胃"},
        })
        assert r.status_code == 201

        course = client.get(f"/api/records/{rid}/course").json()
        assert [v["visit_no"] for v in course] == [1, 2]
        assert all(v["record_id"] for v in course)

        # 病程列表：一个系列一行，而非每次就诊一行
        courses = client.get("/api/courses").json()
        mine = [c for c in courses["items"] if c["patient_name"] == "接口测试患者"]
        assert len(mine) == 1
        assert mine[0]["visit_count"] == 2
        assert mine[0]["complaint"] == "腹胀纳呆2周"  # 初诊主诉，而非“服药后复诊”

        # 修改历史：API 写入经审计会话，应产生字段级留痕
        history = client.get(f"/api/records/{rid}/history").json()
        assert any(e["table_name"] == "info_record" for e in history)
        assert any(e["table_name"] == "prescription_item" for e in history)
    finally:
        _cleanup()


def test_create_record_requires_existing_patient(engine: Engine) -> None:
    client = _make_client(engine)
    try:
        r = client.post("/api/records", json={
            "patient_id": "NO-SUCH-PATIENT", "clinic_date": "2026-07-01",
            "narrative": {"complaint": "测试"},
        })
        assert r.status_code == 404
    finally:
        _cleanup()


def test_health_reports_ai_not_configured(engine: Engine) -> None:
    client = _make_client(engine)
    try:
        health = client.get("/api/health").json()
        assert health["status"] == "ok"
        assert health["ai_configured"] in (True, False)
    finally:
        _cleanup()
