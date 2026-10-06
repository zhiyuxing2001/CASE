"""应用设置 API 测试：API Key 的存取、脱敏与不泄露。"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_db
from app.main import app
from app.services import settings_service


def _client(engine: Engine) -> TestClient:
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)

    def override():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override
    return TestClient(app)


def test_ai_settings_crud_and_no_leak(engine: Engine) -> None:
    client = _client(engine)
    secret = "sk-test-secret-1234"
    try:
        # 初始未配置
        data = client.get("/api/settings/ai").json()
        assert data["configured"] is False
        assert data["api_key_masked"] == ""

        # 保存 Key
        data = client.put("/api/settings/ai", json={
            "api_key": secret, "base_url": "https://api.deepseek.com",
            "model": "deepseek-flash",
        }).json()
        assert data["configured"] is True
        assert data["api_key_masked"] == "••••1234"
        assert secret not in json.dumps(data)  # 完整 Key 永不回传

        # 回读仍是脱敏
        data = client.get("/api/settings/ai").json()
        assert data["api_key_masked"] == "••••1234"
        assert secret not in json.dumps(data)

        # 生效 key 来自数据库
        with Session(engine) as session:
            assert settings_service.effective_api_key(session) == secret

        # 清除后回落为未配置
        data = client.delete("/api/settings/ai").json()
        assert data["configured"] is False
    finally:
        app.dependency_overrides.pop(get_db, None)
