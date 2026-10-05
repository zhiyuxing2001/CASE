"""提示词相关端点测试：OCR 结构化降级、术语归一本地优先。"""

from __future__ import annotations

import pathlib

import pytest

pytest.importorskip("ocrmac")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import Engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.api.deps import get_db  # noqa: E402
from app.audit import enable_audit  # noqa: E402
from app.config import settings  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import seed_dictionaries  # noqa: E402

SAMPLE = pathlib.Path(__file__).resolve().parents[2] / "tools" / "ocr_test_sample.png"


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
