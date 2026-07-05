# Phase 7 LLM Provider Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a testable LLM provider boundary so planner, code generation, repair, and summarization can later call an OpenAI-compatible cloud model without leaking raw datasets.

**Architecture:** Extend settings with LLM configuration, add a small provider contract in `app/core/llm.py`, implement an OpenAI-compatible chat-completion adapter over `httpx`, and expose a status endpoint that reports whether the adapter is configured. This phase does not call an LLM from the orchestrator yet.

**Tech Stack:** FastAPI, dataclasses, httpx, pytest.

---

### Task 1: Test LLM Configuration And Adapter Contract

**Files:**
- Create: `backend/tests/test_llm_provider.py`

- [x] **Step 1: Write failing settings test**

Verify `build_settings()` reads:

```text
LLM_PROVIDER
LLM_BASE_URL
LLM_API_KEY
LLM_MODEL
```

and falls back to an unconfigured adapter when no key exists.

- [x] **Step 2: Write failing OpenAI-compatible adapter test**

Use `httpx.MockTransport` to assert the adapter sends a `POST /chat/completions` request with bearer auth, model, messages, and temperature, then parses the first assistant message.

- [x] **Step 3: Run tests to verify they fail**

Run: `.\.venv\Scripts\python -m pytest tests\test_llm_provider.py -q`

Expected: FAIL because LLM settings and adapter do not exist.

### Task 2: Extend Settings

**Files:**
- Modify: `backend/app/core/config.py`

- [x] **Step 1: Add LLM settings fields**

Add:

```python
llm_provider: str
llm_base_url: str
llm_api_key: str | None
llm_model: str
```

- [x] **Step 2: Use environment defaults**

Defaults:

```text
LLM_PROVIDER=openai-compatible
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4.1-mini
LLM_API_KEY or OPENAI_API_KEY
```

### Task 3: Implement Provider Boundary

**Files:**
- Create: `backend/app/core/llm.py`

- [x] **Step 1: Add dataclasses**

Add `LLMMessage`, `LLMRequest`, `LLMResponse`, and `LLMStatus`.

- [x] **Step 2: Add OpenAI-compatible client**

`OpenAICompatibleLLM.complete()` posts to `{base_url}/chat/completions`, parses `choices[0].message.content`, and raises `LLMProviderError` on non-2xx responses or malformed responses.

- [x] **Step 3: Add client factory**

`build_llm_client(settings)` returns a configured client when an API key exists and an unconfigured status otherwise.

### Task 4: Expose Status API

**Files:**
- Create: `backend/app/api/llm.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_llm_provider.py`

- [x] **Step 1: Add status endpoint**

`GET /api/llm/status` returns:

```json
{
  "provider": "openai-compatible",
  "model": "gpt-4.1-mini",
  "base_url": "https://api.openai.com/v1",
  "configured": false
}
```

- [x] **Step 2: Run all backend tests**

Run: `.\.venv\Scripts\python -m pytest -q`

Expected: all tests pass.

### Self-Review

- Spec coverage: This phase implements the LLM boundary only; planner/code generation integration stays in a later phase.
- Placeholder scan: No TODO/TBD placeholders remain.
- Type consistency: Status response fields match `LLMStatus`.
