"""LLM 接入层类型：能力、任务、请求/响应与端点。

业务代码只声明能力需求与任务名，永不声明模型名——这是将来加自托管
端点时"只改配置、不改调用方"的关键。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Mapping, Sequence


class Capability(StrEnum):
    VISION = "vision"
    JSON_MODE = "json_mode"
    TOOL_CALLS = "tool_calls"
    LONG_CONTEXT = "long_context"
    STREAMING = "streaming"


class ProviderKind(StrEnum):
    API = "api"
    SELF_HOSTED = "self_hosted"


class Task(StrEnum):
    OCR_STRUCTURING = "ocr_structuring"
    CASE_QA = "case_qa"
    NOTE_DRAFT = "note_draft"
    NOTE_POLISH = "note_polish"
    TERM_NORMALIZE = "term_normalize"


@dataclass(frozen=True)
class Message:
    role: str
    content: str


@dataclass(frozen=True)
class ChatRequest:
    task: Task
    messages: Sequence[Message]
    temperature: float = 0.2
    max_tokens: int | None = None
    json_schema: Mapping[str, Any] | None = None
    timeout_s: float = 60.0


@dataclass(frozen=True)
class Usage:
    tokens_in: int = 0
    tokens_cached: int = 0
    tokens_out: int = 0
    cost_yuan: float = 0.0


@dataclass(frozen=True)
class ChatResponse:
    text: str
    provider: str
    model: str
    usage: Usage
    latency_ms: int
    degraded: bool = False


@dataclass(frozen=True)
class LlmEndpoint:
    name: str
    kind: ProviderKind
    base_url: str
    api_key: str
    model: str
    capabilities: frozenset[Capability]
    context_window: int
    priority: int = 100
    price_input: float = 0.0
    price_input_cached: float = 0.0
    price_output: float = 0.0
