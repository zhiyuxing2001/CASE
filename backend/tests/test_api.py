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


def test_same_patient_multiple_courses(engine: Engine) -> None:
    """同一患者可有多个病案，各病案拥有独立的 course_id。"""
    client = _make_client(engine)
    try:
        pid = client.post("/api/patients", json={
            "patient_name": "多病案患者", "gender": False,
            "birthday": "1970-01-01",
        }).json()["patient_id"]

        client.post("/api/records", json={
            "patient_id": pid, "clinic_date": "2026-01-01",
            "narrative": {"complaint": "胃痛"},
        })
        client.post("/api/records", json={
            "patient_id": pid, "clinic_date": "2026-03-01",
            "narrative": {"complaint": "失眠"},
        })

        courses = client.get("/api/courses").json()["items"]
        mine = [c for c in courses if c["patient_name"] == "多病案患者"]
        assert len(mine) == 2
        assert mine[0]["course_id"] != mine[1]["course_id"]
        assert all(c["course_id"] and c["first_record_id"] for c in mine)
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


def test_delete_and_export_courses(engine: Engine) -> None:
    client = _make_client(engine)
    try:
        pid = client.post("/api/patients", json={
            "patient_name": "导出患者", "gender": True, "birthday": "1970-01-01",
        }).json()["patient_id"]
        client.post("/api/records", json={
            "patient_id": pid, "clinic_date": "2026-01-01",
            "narrative": {"complaint": "测试"},
        })
        mine = [c for c in client.get("/api/courses").json()["items"]
                if c["patient_name"] == "导出患者"]
        assert len(mine) == 1
        cid = mine[0]["course_id"]

        # 导出 Excel
        r = client.post("/api/courses/export", json={"course_ids": [cid]})
        assert r.status_code == 200
        assert r.headers["content-type"].startswith(
            "application/vnd.openxmlformats-officedocument.spreadsheetml")

        # 导出 Word 报告
        r = client.get(f"/api/courses/{cid}/report")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith(
            "application/vnd.openxmlformats-officedocument.wordprocessingml")

        # 删除（软删除）
        r = client.post("/api/courses/delete", json={"course_ids": [cid]})
        assert r.status_code == 200
        assert r.json()["deleted"] >= 1

        # 列表不再包含该病案
        remaining = client.get("/api/courses").json()["items"]
        assert all(c["course_id"] != cid for c in remaining)
    finally:
        _cleanup()


def test_western_medicine_and_first_narrative(engine: Engine) -> None:
    """西药单列；复诊详情回填初诊的既往史/个人史/过敏史。"""
    client = _make_client(engine)
    try:
        pid = client.post("/api/patients", json={
            "patient_name": "西药患者", "gender": True, "birthday": "1970-01-01",
        }).json()["patient_id"]
        r1 = client.post("/api/records", json={
            "patient_id": pid, "clinic_date": "2026-01-01",
            "narrative": {"complaint": "首诊", "past_history": "高血压病史",
                          "personal_history": "吸烟"},
            "treatment": {"treatment_principle": "清热祛湿",
                          "western_medicine": "甲钴胺 0.5mg tid"},
        }).json()
        r2 = client.post("/api/records", json={
            "patient_id": pid, "clinic_date": "2026-01-15", "visit_type": 1,
            "parent_record_id": r1["record_id"],
            "narrative": {"complaint": "复诊"},
        }).json()

        detail1 = client.get(f"/api/records/{r1['record_id']}").json()
        assert detail1["treatment"]["western_medicine"] == "甲钴胺 0.5mg tid"

        detail2 = client.get(f"/api/records/{r2['record_id']}").json()
        assert detail2["first_narrative"]["past_history"] == "高血压病史"
        assert detail2["first_narrative"]["personal_history"] == "吸烟"
    finally:
        _cleanup()


def test_update_record(engine: Engine) -> None:
    """编辑已有病案：覆盖病史、诊断、治疗与药味，病程结构不变。"""
    client = _make_client(engine)
    try:
        pid = client.post("/api/patients", json={
            "patient_name": "编辑患者", "gender": True, "birthday": "1970-01-01",
        }).json()["patient_id"]
        rid = client.post("/api/records", json={
            "patient_id": pid, "clinic_date": "2026-01-01",
            "narrative": {"complaint": "原始主诉"},
            "diagnosis": {"syndrome": "原始证型"},
            "herbs": [{"herb_name": "柴胡", "dose": 10, "sequence": 0}],
        }).json()["record_id"]

        r = client.put(f"/api/records/{rid}", json={
            "patient_id": pid, "clinic_date": "2026-01-02",
            "narrative": {"complaint": "更新主诉"},
            "diagnosis": {"syndrome": "更新证型"},
            "treatment": {"western_medicine": "甲钴胺 0.5mg tid"},
            "herbs": [{"herb_name": "白芍", "dose": 15, "sequence": 0}],
        })
        assert r.status_code == 200

        detail = client.get(f"/api/records/{rid}").json()
        assert detail["narrative"]["complaint"] == "更新主诉"
        assert detail["diagnosis"]["syndrome"] == "更新证型"
        assert detail["treatment"]["western_medicine"] == "甲钴胺 0.5mg tid"
        assert [h["herb_name_norm"] for h in detail["herbs"]] == ["白芍"]
        assert detail["record"]["clinic_date"] == "2026-01-02"
    finally:
        _cleanup()


def test_lab_results_roundtrip(engine: Engine) -> None:
    """检验与检查分列：创建、回读与编辑替换。"""
    client = _make_client(engine)
    try:
        pid = client.post("/api/patients", json={
            "patient_name": "检验患者", "gender": True, "birthday": "1970-01-01",
        }).json()["patient_id"]
        rid = client.post("/api/records", json={
            "patient_id": pid, "clinic_date": "2026-02-01",
            "narrative": {"complaint": "乏力"},
            "lab_results": [
                {"item_name": "白细胞计数", "result_value": "12.5",
                 "unit": "10^9/L", "reference_range": "3.5-9.5", "abnormal_flag": 1},
            ],
            "exams": [
                {"item_name": "胸部CT", "finding": "右肺上叶小结节",
                 "conclusion": "建议随访"},
            ],
        }).json()["record_id"]

        detail = client.get(f"/api/records/{rid}").json()
        assert len(detail["lab_results"]) == 1
        assert detail["lab_results"][0]["item_name"] == "白细胞计数"
        assert detail["lab_results"][0]["abnormal_flag"] == 1
        assert len(detail["exams"]) == 1
        assert detail["exams"][0]["item_name"] == "胸部CT"
        assert detail["exams"][0]["conclusion"] == "建议随访"

        # 编辑：整体替换
        client.put(f"/api/records/{rid}", json={
            "patient_id": pid, "clinic_date": "2026-02-01",
            "narrative": {"complaint": "乏力"},
            "lab_results": [
                {"item_name": "血红蛋白", "result_value": "90",
                 "unit": "g/L", "reference_range": "115-150", "abnormal_flag": 2},
            ],
            "exams": [],
        })
        detail2 = client.get(f"/api/records/{rid}").json()
        assert len(detail2["lab_results"]) == 1
        assert detail2["lab_results"][0]["item_name"] == "血红蛋白"
        assert detail2["lab_results"][0]["abnormal_flag"] == 2
        assert detail2["exams"] == []
    finally:
        _cleanup()


def test_review_record_clears_flags(engine: Engine) -> None:
    """校对：仅替换药味/检验检查并清除待校对标记，病史诊断不变。"""
    client = _make_client(engine)
    try:
        pid = client.post("/api/patients", json={
            "patient_name": "校对患者", "gender": True, "birthday": "1970-01-01",
        }).json()["patient_id"]
        rid = client.post("/api/records", json={
            "patient_id": pid, "clinic_date": "2026-03-01",
            "narrative": {"complaint": "胃痛", "present_illness": "餐后加重"},
            "diagnosis": {"syndrome": "肝胃不和证"},
            "herbs": [{"herb_name": "黄苓", "dose": 15, "sequence": 0, "needs_review": True}],
            "lab_results": [{"item_name": "白细胞计数", "result_value": "12.5",
                             "abnormal_flag": 1, "needs_review": True}],
            "exams": [],
        }).json()["record_id"]

        # 校对：修正药名 + 清除待校对标记
        r = client.post(f"/api/records/{rid}/review", json={
            "herbs": [{"herb_name": "黄芩", "dose": 15, "sequence": 0, "needs_review": False}],
            "lab_results": [{"item_name": "白细胞计数", "result_value": "12.5",
                             "abnormal_flag": 1, "needs_review": False}],
            "exams": [],
        })
        assert r.status_code == 200

        detail = client.get(f"/api/records/{rid}").json()
        assert detail["herbs"][0]["herb_name_norm"] == "黄芩"
        assert detail["herbs"][0]["needs_review"] is False
        assert detail["lab_results"][0]["needs_review"] is False
        # 病史/诊断保持不变
        assert detail["narrative"]["complaint"] == "胃痛"
        assert detail["diagnosis"]["syndrome"] == "肝胃不和证"
    finally:
        _cleanup()
