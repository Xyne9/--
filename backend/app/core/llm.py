from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import AppSettings


@dataclass(frozen=True)
class LLMMessage:
    role: str
    content: str


@dataclass(frozen=True)
class LLMRequest:
    messages: list[LLMMessage]
    temperature: float = 0.2


@dataclass(frozen=True)
class LLMResponse:
    content: str
    model: str
    raw: dict[str, Any]


@dataclass(frozen=True)
class LLMStatus:
    provider: str
    model: str
    base_url: str
    configured: bool


class LLMProviderError(RuntimeError):
    pass


class OpenAICompatibleLLM:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        http_client: httpx.Client | None = None,
        timeout_seconds: float = 60.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.http_client = http_client or httpx.Client()
        self.timeout_seconds = timeout_seconds

    def complete(self, request: LLMRequest) -> LLMResponse:
        payload = {
            "model": self.model,
            "messages": [{"role": message.role, "content": message.content} for message in request.messages],
            "temperature": request.temperature,
        }
        try:
            response = self.http_client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            body = response.json()
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"LLM request failed: {exc}") from exc
        except ValueError as exc:
            raise LLMProviderError("LLM response was not valid JSON") from exc

        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMProviderError("LLM response did not include an assistant message") from exc
        if not isinstance(content, str):
            raise LLMProviderError("LLM assistant message content was not text")
        return LLMResponse(content=content, model=body.get("model", self.model), raw=body)


def llm_status(settings: AppSettings) -> LLMStatus:
    return LLMStatus(
        provider=settings.llm_provider,
        model=settings.llm_model,
        base_url=settings.llm_base_url,
        configured=bool(settings.llm_api_key),
    )


def build_llm_client(
    settings: AppSettings,
    http_client: httpx.Client | None = None,
) -> OpenAICompatibleLLM:
    if settings.llm_provider != "openai-compatible":
        raise LLMProviderError(f"Unsupported LLM provider: {settings.llm_provider}")
    if not settings.llm_api_key:
        raise LLMProviderError("LLM API key is not configured")
    return OpenAICompatibleLLM(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        http_client=http_client,
    )
