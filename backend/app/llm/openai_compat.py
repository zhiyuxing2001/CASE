"""OpenAI 兼容实现：一个类同时覆盖 DeepSeek API 与自托管。

DeepSeek 与 vLLM/SGLang 都暴露 OpenAI 兼容的 ``/chat/completions``，
因此只写一个实现类，自托管落地时不新增 Provider，只新增端点配置。
"""

from __future__ import annotations

import time

import httpx

from .types import ChatRequest, ChatResponse, LlmEndpoint, Usage


class OpenAiCompatibleProvider:
    def __init__(self, endpoint: LlmEndpoint):
        self.endpoint = endpoint
        self.name = endpoint.name
        self.kind = endpoint.kind
        self.capabilities = endpoint.capabilities

    def supports(self, required) -> bool:
        return self.capabilities.issuperset(set(required))

    def chat(self, request: ChatRequest) -> ChatResponse:
        url = f"{self.endpoint.base_url.rstrip('/')}/chat/completions"
        payload: dict = {
            "model": self.endpoint.model,
            "messages": [{"role": m.role, "content": m.content}
                         for m in request.messages],
            "temperature": request.temperature,
            "stream": False,
        }
        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens
        if request.json_schema is not None:
            payload["response_format"] = {"type": "json_object"}

        start = time.monotonic()
        with httpx.Client(timeout=request.timeout_s) as client:
            resp = client.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {self.endpoint.api_key}"},
            )
            resp.raise_for_status()
            data = resp.json()

        latency_ms = int((time.monotonic() - start) * 1000)
        choice = data["choices"][0]["message"]
        usage = data.get("usage", {})

        return ChatResponse(
            text=choice.get("content") or "",
            provider=self.name,
            model=self.endpoint.model,
            usage=Usage(
                tokens_in=usage.get("prompt_tokens", 0),
                tokens_cached=usage.get("prompt_cache_hit_tokens", 0),
                tokens_out=usage.get("completion_tokens", 0),
                cost_yuan=0.0,
            ),
            latency_ms=latency_ms,
        )

    def stream(self, request: ChatRequest):
        # 简化为一次非流式调用；流式 SSE 解析在自托管/正式版再接
        yield self.chat(request)

    def health(self) -> dict:
        return {"name": self.name, "ok": True, "configured": bool(self.endpoint.api_key)}
