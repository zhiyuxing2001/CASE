"""AI 助手 API 测试：未配置 Key 时的优雅降级。"""

from __future__ import annotations

import datetime as dt

from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.api import ai as ai_api
from app.api.deps import get_db
from app.main import app
from app.models import (CaseNarrative, Diagnosis, InfoPatient, InfoRecord,
                        Mentor)
from app.search import rebuild_search_index


class _NoKeyRouter:
    """无 Key 的路由桩，强制走降级分支。"""
    configured = False

    def primary(self):
        return {"provider": "deepseek-api", "model": "deepseek-chat"}

    def chat(self, request):
        return None


def _client(engine: Engine) -> TestClient:
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)

    def override():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override
    return TestClient(app)


def test_ai_degrades_without_key(engine: Engine, monkeypatch) -> None:
    monkeypatch.setattr(ai_api, "get_router", lambda: _NoKeyRouter())
    # 造一条带证型的病案并重建检索索引
    with Session(engine) as session:
        session.add(Mentor(mentor_id="M-AI", mentor_name="测试老师"))
        session.add(InfoPatient(patient_id="P-AI", patient_name="测试患者",
                                birthday=dt.date(1970, 1, 1), nationality="CHN"))
        session.flush()
        record = InfoRecord(patient_id="P-AI", father_id=0, visit_no=1,
                            clinic_date=dt.date(2026, 1, 1), age=50.0)
        session.add(record)
        session.flush()
        record.father_id = record.record_id
        session.add(CaseNarrative(record_id=record.record_id, patient_id="P-AI",
                                  complaint="胃脘胀痛", present_illness="餐后加重",
                                  body_of_tongue="淡", pulse="弦细"))
        session.add(Diagnosis(record_id=record.record_id, patient_id="P-AI",
                              tcm_disease="胃脘痛", syndrome="肝胃不和证"))
        session.commit()
        rid = record.record_id
    rebuild_search_index(engine)

    client = _client(engine)
    try:
        status = client.get("/api/ai/status").json()
        assert status["configured"] is False
        assert status["provider"] == "deepseek-api"

        # 问答降级为检索结果直出
        chat = client.post("/api/ai/chat", json={"question": "肝胃不和"}).json()
        assert chat["ai_configured"] is False
        assert chat["degraded"] is True
        assert len(chat["sources"]) >= 1
        assert chat["sources"][0]["syndrome"] == "肝胃不和证"

        # 引用某病案：即使无 Key，引用病案也应进入来源
        ref = client.post("/api/ai/chat", json={
            "question": "证型是什么", "case_id": rid,
        }).json()
        assert any(s["record_id"] == rid for s in ref["sources"])

        # 写作类任务明确返回未配置
        draft = client.post("/api/ai/draft", json={"topic": "测试"}).json()
        assert draft["ai_configured"] is False
        assert draft["text"] == ""
    finally:
        app.dependency_overrides.pop(get_db, None)
