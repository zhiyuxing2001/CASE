"""Provider 协议——自托管预留的核心契约。

API 与自托管共用同一实现类（OpenAI 兼容协议），因此这里只定义
业务层依赖的最小契约。
"""

from __future__ import annotations

from typing import Iterable, Iterator, Protocol

from .types import Capability, ChatRequest, ChatResponse, ProviderKind


class LlmProvider(Protocol):
    name: str
    kind: ProviderKind
    capabilities: frozenset[Capability]

    def supports(self, required: Iterable[Capability]) -> bool: ...

    def chat(self, request: ChatRequest) -> ChatResponse: ...

    def stream(self, request: ChatRequest) -> Iterator[ChatResponse]: ...

    def health(self) -> dict: ...
