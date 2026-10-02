"""OCR 流水线集成测试：上传 → 本地识别 → 校对入库。

依赖 macOS Vision（ocrmac）；不可用时跳过。
"""

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

SAMPLE = pathlib.Path(__file__).resolve().parents[2] / "tools" / "ocr_test_sample.png"


def _client(engine: Engine) -> TestClient:
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    enable_audit(factory)

    def override():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override
    return TestClient(app)


def test_upload_ocr_commit(engine: Engine, monkeypatch, tmp_path) -> None:
    if not SAMPLE.is_file():
        pytest.skip("样例图不存在")

    # 附件目录隔离到临时目录，避免污染真实 data/。
    # attachments_dir 是 data_dir 的派生 property，改 data_dir 即可。
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    (tmp_path / "attachments").mkdir()

    client = _client(engine)
    try:
        with open(SAMPLE, "rb") as fh:
            r = client.post("/api/attachments",
                            files={"file": ("rx.png", fh, "image/png")})
        assert r.status_code == 201
        aid = r.json()["attach_id"]
        assert r.json()["quality"]["width"] > 0

        r = client.post("/api/ocr/jobs", json={"attach_id": aid})
        assert r.status_code == 201
        job = r.json()
        assert len(job["lines"]) > 0
        assert all("bbox" in line for line in job["lines"])

        r = client.post(f"/api/ocr/jobs/{job['job_id']}/commit", json={
            "patient_name": "OCR测试患者", "gender": True,
            "birthday": "1970-01-01", "clinic_date": "2026-08-10",
            "complaint": "胃脘胀痛3月余",
        })
        assert r.status_code == 200
        rid = r.json()["record_id"]

        detail = client.get(f"/api/records/{rid}").json()
        assert "胃脘胀痛" in detail["narrative"]["raw_ocr_text"]
    finally:
        app.dependency_overrides.pop(get_db, None)
