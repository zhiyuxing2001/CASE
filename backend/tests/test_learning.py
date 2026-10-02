"""跟师学习 API 测试：笔记增改查、导师点评、进度看板。"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_db
from app.audit import enable_audit
from app.main import app
from app.models import Mentor


def _client(engine: Engine) -> TestClient:
    with Session(engine) as session:
        session.add(Mentor(mentor_id="M-LRN", mentor_name="学习导师"))
        session.commit()

    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    enable_audit(factory)

    def override():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override
    return TestClient(app)


def test_note_crud_and_comment(engine: Engine) -> None:
    client = _client(engine)
    try:
        # 创建
        r = client.post("/api/learning/notes", json={
            "note_type": 1, "title": "湿热证治心得", "content_md": "# 要点\n清热祛湿",
            "mentor_id": "M-LRN",
        })
        assert r.status_code == 201
        note_id = r.json()["note_id"]
        assert r.json()["word_count"] > 0
        assert r.json()["mentor_name"] == "学习导师"

        # 列表
        r = client.get("/api/learning/notes")
        assert r.status_code == 200
        assert any(n["note_id"] == note_id for n in r.json()["items"])

        # 更新
        r = client.put(f"/api/learning/notes/{note_id}", json={
            "title": "湿热证治心得（修订）", "status": 1,
        })
        assert r.status_code == 200
        assert r.json()["title"] == "湿热证治心得（修订）"

        # 点评
        r = client.post(f"/api/learning/notes/{note_id}/comments", json={
            "mentor_id": "M-LRN", "content": "辨证准确，方药可再精简。",
        })
        assert r.status_code == 201
        assert r.json()["content"].startswith("辨证准确")

        # 详情包含点评
        r = client.get(f"/api/learning/notes/{note_id}")
        assert len(r.json()["comments"]) == 1

        # 进度看板
        r = client.get("/api/learning/progress")
        assert r.status_code == 200
        assert r.json()["total_records"] >= 0
    finally:
        app.dependency_overrides.pop(get_db, None)
