"""病案分析 API 测试：频次统计的正确性。"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.audit import enable_audit
from app.main import app
from app.seed import seed_dictionaries


def _client(engine: Engine) -> TestClient:
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    enable_audit(factory)

    def override():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override
    return TestClient(app)


def test_analytics_frequencies(engine: Engine) -> None:
    seed_dictionaries(engine)
    client = _client(engine)
    try:
        pid = client.post("/api/patients", json={
            "patient_name": "统计患者", "gender": True, "birthday": "1970-01-01",
        }).json()["patient_id"]

        client.post("/api/records", json={
            "patient_id": pid, "clinic_date": "2026-01-01",
            "narrative": {"complaint": "胃痛", "body_of_tongue": "淡红",
                          "fur_of_tongue": "薄白", "pulse": "弦细"},
            "diagnosis": {"tcm_disease": "胃脘痛", "syndrome": "肝胃不和证"},
            "treatment": {"treatment_principle": "疏肝和胃"},
            "herbs": [
                {"herb_name": "柴胡", "dose": 10, "sequence": 0},
                {"herb_name": "白芍", "dose": 15, "sequence": 1},
                {"herb_name": "白芍", "dose": 15, "sequence": 2},
            ],
        })

        overview = client.get("/api/analytics/overview").json()
        assert overview["total_courses"] >= 1
        assert overview["distinct_herbs"] >= 2  # 柴胡、白芍

        syndromes = client.get("/api/analytics/syndromes").json()
        assert ("肝胃不和证", 1) in [(s["label"], s["count"]) for s in syndromes]

        herbs = client.get("/api/analytics/herbs").json()
        bai_shao = [h for h in herbs if h["label"] == "白芍"][0]
        assert bai_shao["count"] == 2
        assert bai_shao["avg_dose"] == 15.0

        tongue = client.get("/api/analytics/tongue").json()
        assert ("淡红", 1) in [(t["label"], t["count"]) for t in tongue["body"]]
        assert ("弦细", 1) in [(t["label"], t["count"]) for t in tongue["pulse"]]

        diseases = client.get("/api/analytics/diseases").json()
        assert ("胃脘痛", 1) in [(d["label"], d["count"]) for d in diseases]
    finally:
        app.dependency_overrides.pop(get_db, None)
