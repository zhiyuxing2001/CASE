"""界面模板 API 与按模板提取测试。"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.main import app
from app.ocr.template import extract_fields


def _client(engine: Engine) -> TestClient:
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)

    def override():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override
    return TestClient(app)


def test_template_crud(engine: Engine) -> None:
    client = _client(engine)
    try:
        r = client.post("/api/templates", json={
            "name": "HIS 病历界面", "doc_type": 0,
            "field_anchors": [
                {"label": "主诉", "field": "narrative.complaint"},
                {"label": "证型", "field": "diagnosis.syndrome"},
            ],
            "table_columns": [],
        })
        assert r.status_code == 201
        tid = r.json()["template_id"]

        r = client.get("/api/templates")
        assert any(t["template_id"] == tid for t in r.json())

        r = client.put(f"/api/templates/{tid}", json={
            "name": "HIS 病历界面 v2", "doc_type": 0,
            "field_anchors": [{"label": "主诉", "field": "narrative.complaint"}],
            "table_columns": [{"label": "药名", "field": "herbs[].herb_name"}],
        })
        assert r.json()["name"] == "HIS 病历界面 v2"
        assert r.json()["table_columns"][0]["field"] == "herbs[].herb_name"

        assert client.delete(f"/api/templates/{tid}").status_code == 204
        # 软删除后不再出现在列表
        assert all(t["template_id"] != tid
                   for t in client.get("/api/templates").json())
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_extract_fields_by_template() -> None:
    lines = [
        {"text": "主诉：胃脘胀痛", "confidence": 0.9},
        {"text": "现病史：餐后加重", "confidence": 0.9},
        {"text": "证型：肝胃不和证", "confidence": 0.9},
    ]
    anchors = [
        {"label": "主诉", "field": "narrative.complaint"},
        {"label": "证型", "field": "diagnosis.syndrome"},
    ]
    flat = extract_fields(lines, anchors)
    assert flat["narrative.complaint"] == "胃脘胀痛"
    assert flat["diagnosis.syndrome"] == "肝胃不和证"
    # 未在模板中的字段不提取
    assert "narrative.present_illness" not in flat
