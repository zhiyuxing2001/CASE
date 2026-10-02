"""字典维护与数据管理 API 测试。"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.audit import enable_audit
from app.config import settings
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


def test_herb_crud_and_admin(engine: Engine, monkeypatch, tmp_path) -> None:
    seed_dictionaries(engine)
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    (tmp_path / "backups").mkdir()

    client = _client(engine)
    try:
        # 药名增改删（软删除）
        r = client.post("/api/dict/herbs", json={
            "herb_name": "测试药", "pinyin": "ceshiyao", "category": "清热药",
        })
        assert r.status_code == 201
        herb_id = r.json()["herb_id"]
        assert r.json()["pinyin"] == "ceshiyao"

        r = client.put(f"/api/dict/herbs/{herb_id}", json={
            "herb_name": "测试药", "pinyin": "ceshiyao", "category": "补虚药",
        })
        assert r.status_code == 200
        assert r.json()["category"] == "补虚药"

        r = client.delete(f"/api/dict/herbs/{herb_id}")
        assert r.status_code == 204

        # 统计与完整性自检
        r = client.get("/api/admin/stats")
        assert r.status_code == 200
        assert any(t["table"] == "dict_herb" for t in r.json()["tables"])

        r = client.get("/api/admin/check")
        assert r.status_code == 200
        assert r.json()["foreign_key_violations"] == 0

        # 备份
        r = client.post("/api/admin/backup", json={})
        assert r.status_code == 200
        assert r.json()["size"] > 0

        backups = client.get("/api/admin/backups").json()
        assert len(backups) >= 1

        # 审计页
        r = client.get("/api/admin/audit")
        assert r.status_code == 200
        assert "items" in r.json()
    finally:
        app.dependency_overrides.pop(get_db, None)
