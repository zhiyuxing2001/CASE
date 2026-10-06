"""按任务路由：能力过滤 → 端点排序 → 回退链。

当前端点数 = 1，路由退化为直通，但契约完整——加第二个端点时
调用方无需改动。
"""

from __future__ import annotations

from .openai_compat import OpenAiCompatibleProvider
from .registry import build_registry
from .types import Capability, ChatRequest, ChatResponse, Task

#: 任务 → 能力需求。业务层只认任务名。
TASK_CAPS: dict[Task, frozenset[Capability]] = {
    Task.OCR_STRUCTURING: frozenset({Capability.VISION, Capability.JSON_MODE}),
    Task.CASE_QA: frozenset({Capability.JSON_MODE, Capability.STREAMING}),
    Task.NOTE_DRAFT: frozenset({Capability.STREAMING}),
    Task.NOTE_POLISH: frozenset({Capability.STREAMING}),
    Task.TERM_NORMALIZE: frozenset({Capability.JSON_MODE}),
}


class LlmRouter:
    def __init__(self, endpoints=None):
        self._providers = [
            OpenAiCompatibleProvider(e) for e in (endpoints or build_registry())
        ]

    @property
    def configured(self) -> bool:
        return any(p.endpoint.api_key for p in self._providers)

    def primary(self) -> dict:
        """给设置/状态页展示当前首选端点与模型。"""
        if not self._providers:
            return {"provider": "", "model": ""}
        p = self._providers[0]
        return {"provider": p.name, "model": p.endpoint.model}

    def resolve(self, task: Task):
        required = TASK_CAPS[task]
        return [
            p for p in self._providers
            if p.supports(required) and p.endpoint.api_key
        ]

    def chat(self, request: ChatRequest) -> ChatResponse | None:
        for provider in self.resolve(request.task):
            try:
                return provider.chat(request)
            except Exception:  # noqa: BLE001 — 走回退链
                continue
        return None


_router: LlmRouter | None = None


def get_router() -> LlmRouter:
    """懒加载路由：首次调用时按当前配置构建端点。"""
    global _router
    if _router is None:
        _router = LlmRouter()
    return _router


def reset_router() -> None:
    """清空缓存，使 API Key 等配置的改动在下次调用时立即生效。"""
    global _router
    _router = None
