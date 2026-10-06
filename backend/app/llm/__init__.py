"""LLM 接入层。"""

from __future__ import annotations

import json

from .router import LlmRouter, get_router, reset_router
from .types import (Capability, ChatRequest, ChatResponse, LlmEndpoint,
                    Message, ProviderKind, Task, Usage)


def parse_json(text: str) -> dict:
    """容错解析模型输出：剥离可能的 markdown 代码围栏。"""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()
    return json.loads(cleaned)


__all__ = [
    "Capability", "ChatRequest", "ChatResponse", "LlmEndpoint", "Message",
    "ProviderKind", "Task", "Usage", "LlmRouter", "get_router", "reset_router",
    "parse_json",
]
