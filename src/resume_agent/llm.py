"""Gemini 클라이언트 — 판독용/작성용 분리 + 재시도 + 모델 폴백.

무인 배치로 도는 에이전트라 503(고부하)·429(쿼터) 한 번에 공고 하나를 잃으면 안 된다.
같은 티어 안에서 모델을 단계적으로 강등하며 재시도한다.
"""
from __future__ import annotations

import os
import random
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

# 2026-08-19 실측으로 고정한 체인. 목록에 있다고 다 쓸 수 있는 게 아니다.
#   gemini-3.7-flash      429 (무료 티어 쿼터 초과)      → 제외
#   gemini-3.6-flash      503, 응답까지 112초           → 제외 (배치 전체를 잡아먹음)
#   gemini-2.5-pro        404 (이 키로 접근 불가)        → 제외
#   gemini-3.5-flash      OK 3.5s   / 2.5-flash OK 5.7s / 3.5-flash-lite OK 0.9s
READ_CHAIN = ["gemini-3.5-flash", "gemini-2.5-flash", "gemini-3.5-flash-lite"]
WRITE_CHAIN = ["gemini-3.5-flash", "gemini-2.5-flash"]

if os.getenv("MODEL_READ"):
    READ_CHAIN = [os.environ["MODEL_READ"], *READ_CHAIN]
if os.getenv("MODEL_WRITE"):
    WRITE_CHAIN = [os.environ["MODEL_WRITE"], *WRITE_CHAIN]

MODEL_READ = READ_CHAIN[0]
MODEL_WRITE = WRITE_CHAIN[0]

RETRIES_PER_MODEL = 2
CALL_TIMEOUT_MS = 90_000     # 한 호출이 배치 전체를 잡아먹지 않게
_client: genai.Client | None = None


def client() -> genai.Client:
    global _client
    if _client is None:
        key = os.getenv("GOOGLE_API_KEY")
        if not key:
            raise RuntimeError("GOOGLE_API_KEY 가 없습니다 (.env 확인)")
        _client = genai.Client(api_key=key)
    return _client


def _retryable(e: Exception) -> bool:
    """같은 모델로 다시 걸어볼 가치가 있는가.

    429(쿼터)는 기다린다고 풀리지 않으므로 재시도하지 않고 바로 다음 모델로 강등한다.
    이걸 재시도로 잡고 있으면 공고 하나에 수 분씩 날린다.
    """
    code = getattr(e, "code", None) or getattr(e, "status_code", None)
    if code in (429,) or "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
        return False
    if code in (500, 502, 503, 504):
        return True
    return any(x in str(e) for x in ("503", "UNAVAILABLE", "high demand"))


def _call(chain: list[str], contents, config, model: str | None = None):
    models = [model] if model else list(chain)
    # 지정 모델이 실패하면 나머지 체인으로 내려간다
    if model and model not in chain:
        models += chain
    elif model:
        models += [m for m in chain if m != model]

    last: Exception | None = None
    for m in models:
        for attempt in range(RETRIES_PER_MODEL):
            try:
                cfg = config
                if getattr(cfg, "http_options", None) is None:
                    cfg = cfg.model_copy(update={"http_options": types.HttpOptions(timeout=CALL_TIMEOUT_MS)})
                return client().models.generate_content(model=m, contents=contents, config=cfg)
            except Exception as e:  # noqa: BLE001
                last = e
                if not _retryable(e):
                    break
                time.sleep(min(2 ** attempt + random.random(), 12))
        print(f"    [llm] {m} 실패 → 다음 모델로 강등")
    raise RuntimeError(f"모든 모델 실패: {last}")


def generate_json(prompt: str, schema, model: str | None = None,
                  images: list[bytes] | None = None, temperature: float = 0.2):
    """구조화 출력 강제. schema 는 pydantic 모델 또는 JSON Schema dict."""
    parts: list = [types.Part.from_bytes(data=img, mime_type="image/png") for img in (images or [])]
    parts.append(types.Part.from_text(text=prompt))
    cfg = types.GenerateContentConfig(
        temperature=temperature,
        response_mime_type="application/json",
        response_schema=schema,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    resp = _call(READ_CHAIN, [types.Content(role="user", parts=parts)], cfg, model)
    return resp.parsed if getattr(resp, "parsed", None) is not None else resp.text


def generate_text(prompt: str, model: str | None = None, temperature: float = 0.3) -> str:
    cfg = types.GenerateContentConfig(
        temperature=temperature,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    resp = _call(WRITE_CHAIN, prompt, cfg, model)
    return resp.text or ""
