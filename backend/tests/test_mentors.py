"""导师列表与简介详情测试。"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.main import app


def _client(engine: Engine) -> TestClient:
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)

    def override():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override
    return TestClient(app)


def test_mentor_list_detail_and_crud(engine: Engine) -> None:
    client = _client(engine)
    try:
        r = client.post("/api/mentors", json={
            "mentor_name": "姚教授", "title": "主任医师",
            "department": "消化科", "expertise": "慢性胃炎",
            "clinic_time": "周二上午", "clinic_location": "门诊3楼303",
            "bio": "擅长脾胃病", "is_primary": True,
        })
        assert r.status_code == 201
        mid = r.json()["mentor_id"]

        # 造一个该导师的病案
        pid = client.post("/api/patients", json={
            "patient_name": "导师患者", "gender": True, "birthday": "1970-01-01",
        }).json()["patient_id"]
        client.post("/api/records", json={
            "patient_id": pid, "clinic_date": "2026-01-01",
            "mentor_id": mid,
            "narrative": {"complaint": "胃脘胀痛"},
            "diagnosis": {"syndrome": "肝胃不和证"},
            "herbs": [],
        })

        # 列表：含跟诊次数
        m = next(x for x in client.get("/api/mentors/list").json()
                 if x["mentor_id"] == mid)
        assert m["visit_count"] == 1
        assert m["expertise"] == "慢性胃炎"
        assert m["is_primary"] is True

        # 详情：简介 + 统计 + 高频证型 + 最近病案
        d = client.get(f"/api/mentors/{mid}").json()
        assert d["visit_count"] == 1
        assert d["clinic_time"] == "周二上午"
        assert d["clinic_location"] == "门诊3楼303"
        assert d["bio"] == "擅长脾胃病"
        assert d["top_syndromes"][0]["syndrome"] == "肝胃不和证"
        assert len(d["recent_records"]) == 1
        assert d["recent_records"][0]["patient_name"] == "导师患者"

        # 更新
        r = client.put(f"/api/mentors/{mid}", json={
            "mentor_name": "姚教授", "title": "主任医师",
            "department": "消化科", "expertise": "慢性胃炎",
            "clinic_time": "周二、四上午", "clinic_location": "门诊3楼305",
            "bio": "擅长脾胃病", "is_primary": True,
        })
        assert r.json()["clinic_location"] == "门诊3楼305"

        # 软删除后不在列表
        assert client.delete(f"/api/mentors/{mid}").status_code == 204
        assert all(x["mentor_id"] != mid
                   for x in client.get("/api/mentors/list").json())
    finally:
        app.dependency_overrides.pop(get_db, None)
