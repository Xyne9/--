import json

import httpx
from fastapi.testclient import TestClient

from app.core.config import build_settings, get_settings
from app.main import app


def test_build_settings_reads_llm_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_PROVIDER", "openai-compatible")
    monkeypatch.setenv("LLM_BASE_URL", "https://llm.example/v1")
    monkeypatch.setenv("LLM_API_KEY", "sk-test")
    monkeypatch.setenv("LLM_MODEL", "analysis-model")

    settings = build_settings(str(tmp_path / "workspace"))

    assert settings.llm_provider == "openai-compatible"
    assert settings.llm_base_url == "https://llm.example/v1"
    assert settings.llm_api_key == "sk-test"
    assert settings.llm_model == "analysis-model"


def test_build_settings_falls_back_to_openai_api_key(monkeypatch, tmp_path):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")

    settings = build_settings(str(tmp_path / "workspace"))

    assert settings.llm_api_key == "sk-openai"


def test_openai_compatible_llm_posts_chat_completion_request():
    from app.core.llm import LLMMessage, LLMRequest, OpenAICompatibleLLM

    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["path"] = request.url.path
        captured["authorization"] = request.headers["Authorization"]
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl_test",
                "model": "analysis-model",
                "choices": [{"message": {"role": "assistant", "content": "Profile looks healthy."}}],
            },
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = OpenAICompatibleLLM(
        base_url="https://llm.example/v1",
        api_key="sk-test",
        model="analysis-model",
        http_client=http_client,
    )

    response = provider.complete(
        LLMRequest(
            messages=[LLMMessage(role="user", content="Summarize the profile.")],
            temperature=0.1,
        )
    )

    assert captured["method"] == "POST"
    assert captured["path"] == "/v1/chat/completions"
    assert captured["authorization"] == "Bearer sk-test"
    assert captured["payload"] == {
        "model": "analysis-model",
        "messages": [{"role": "user", "content": "Summarize the profile."}],
        "temperature": 0.1,
    }
    assert response.content == "Profile looks healthy."
    assert response.model == "analysis-model"


def test_llm_status_api_reports_configuration(monkeypatch, tmp_path):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    settings = build_settings(str(tmp_path / "workspace"))
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)

    try:
        response = client.get("/api/llm/status")
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()

    assert response.status_code == 200
    assert response.json() == {
        "provider": "openai-compatible",
        "model": "gpt-4.1-mini",
        "base_url": "https://api.openai.com/v1",
        "configured": False,
    }
