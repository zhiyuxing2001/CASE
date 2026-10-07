"""提示词相关端点测试：OCR 结构化降级、术语归一本地优先。"""

from __future__ import annotations

import pathlib

import pytest

pytest.importorskip("ocrmac")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import Engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.api import ocr as ocr_api  # noqa: E402
from app.api.deps import get_db  # noqa: E402
from app.audit import enable_audit  # noqa: E402
from app.config import settings  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import seed_dictionaries  # noqa: E402

SAMPLE = pathlib.Path(__file__).resolve().parents[2] / "tools" / "ocr_test_sample.png"


class _NoKeyRouter:
    configured = False

    def primary(self):
        return {"provider": "deepseek-api", "model": "deepseek-chat"}

    def chat(self, request):
        return None


def _client(engine: Engine) -> TestClient:
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    enable_audit(factory)

    def override():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override
    return TestClient(app)


def test_ocr_structure_degrades_without_key(engine, monkeypatch, tmp_path) -> None:
    if not SAMPLE.is_file():
        pytest.skip("样例图不存在")
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(ocr_api, "get_router", lambda: _NoKeyRouter())
    (tmp_path / "attachments").mkdir()

    client = _client(engine)
    try:
        with open(SAMPLE, "rb") as fh:
            aid = client.post("/api/attachments",
                              files={"file": ("rx.png", fh, "image/png")}).json()["attach_id"]
        job = client.post("/api/ocr/jobs", json={"attach_id": aid}).json()
        r = client.post(f"/api/ocr/jobs/{job['job_id']}/structure")
        assert r.status_code == 200
        data = r.json()
        assert data["degraded"] is True
        assert data["ai_configured"] is False
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_normalize_herb_local(engine) -> None:
    seed_dictionaries(engine)
    client = _client(engine)
    try:
        r = client.post("/api/dict/herbs/normalize", json={"term": "黄苓"})
        assert r.status_code == 200
        data = r.json()
        assert data["matched_by"] == "local"
        assert data["normalised"] == "黄芩"
        assert data["herb_id"]
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_commit_with_structured(engine, monkeypatch, tmp_path) -> None:
    if not SAMPLE.is_file():
        pytest.skip("样例图不存在")
    seed_dictionaries(engine)
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    (tmp_path / "attachments").mkdir()

    client = _client(engine)
    try:
        with open(SAMPLE, "rb") as fh:
            aid = client.post("/api/attachments",
                              files={"file": ("rx.png", fh, "image/png")}).json()["attach_id"]
        job = client.post("/api/ocr/jobs", json={"attach_id": aid}).json()

        r = client.post(f"/api/ocr/jobs/{job['job_id']}/commit", json={
            "patient_name": "结构化患者", "gender": True, "birthday": "1970-01-01",
            "clinic_date": "2026-08-10",
            "structured": {
                "narrative": {"complaint": "胃脘胀痛3月余", "present_illness": "餐后加重",
                              "body_of_tongue": "淡红", "fur_of_tongue": "薄白", "pulse": "弦细"},
                "diagnosis": {"tcm_disease": "胃脘痛", "syndrome": "肝胃不和证",
                              "wm_diagnosis": "慢性胃炎"},
                "treatment": {"treatment_principle": "疏肝理气和胃",
                              "formula_name": "柴胡疏肝散", "dose_count": 7},
                "herbs": [
                    {"sequence": 0, "herb_name": "柴胡", "dose": 10, "unit": "g"},
                    {"sequence": 1, "herb_name": "白芍", "dose": 15, "unit": "g",
                     "needs_review": True, "confidence": 0.4},
                ],
            },
        })
        assert r.status_code == 200
        rid = r.json()["record_id"]

        detail = client.get(f"/api/records/{rid}").json()
        assert detail["narrative"]["body_of_tongue"] == "淡红"
        assert detail["diagnosis"]["syndrome"] == "肝胃不和证"
        assert detail["treatment"]["treatment_principle"] == "疏肝理气和胃"
        herbs = detail["herbs"]
        assert len(herbs) == 2
        assert herbs[1]["needs_review"] is True
        assert herbs[0]["herb_name_norm"] == "柴胡"
    finally:
        app.dependency_overrides.pop(get_db, None)
