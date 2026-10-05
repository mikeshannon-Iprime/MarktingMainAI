"""Unified LLM client — Ollama (local) first, OpenAI fallback."""

from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request
from typing import Any, Dict, Optional, Tuple

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _openai_api_key() -> str | None:
    settings = get_settings()
    return settings.openai_api_key or os.getenv("OPENAI_API_KEY")


def call_ollama(
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    timeout_seconds: int | None = None,
) -> str:
    settings = get_settings()
    base_url = (settings.ollama_base_url or "http://localhost:11434").rstrip("/")
    model_name = model or settings.ollama_model or "mistral"
    timeout = timeout_seconds if timeout_seconds is not None else settings.ollama_timeout_seconds
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
    }
    request = urllib.request.Request(
        f"{base_url}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except socket.timeout as exc:
        raise TimeoutError(f"Ollama request timed out after {timeout}s.") from exc
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, socket.timeout):
            raise TimeoutError(f"Ollama request timed out after {timeout}s.") from exc
        raise
    message = data.get("message") or {}
    content = message.get("content")
    if not content:
        raise RuntimeError("Ollama returned an empty response.")
    return str(content)


def call_openai(system_prompt: str, user_prompt: str, model: str | None = None) -> str:
    api_key = _openai_api_key()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured.")

    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI

    settings = get_settings()
    model_name = model or settings.openai_model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    llm = ChatOpenAI(model=model_name, temperature=0, api_key=api_key)
    prompt = ChatPromptTemplate.from_messages(
        [("system", system_prompt), ("human", user_prompt)]
    )
    chain = prompt | llm
    response = chain.invoke({})
    return response.content if hasattr(response, "content") else str(response)


def invoke_llm(
    system_prompt: str,
    user_prompt: str,
    *,
    timeout_seconds: Optional[int] = None,
    skip_if_unavailable: bool = False,
) -> Tuple[str, Dict[str, Any]]:
    """Prefer local Ollama when enabled; otherwise use OpenAI."""
    settings = get_settings()
    meta: Dict[str, Any] = {
        "provider": "none",
        "model": None,
        "status": "skipped",
        "useLocalLlm": settings.use_local_llm,
    }

    if skip_if_unavailable and not llm_available():
        meta["message"] = (
            "LLM reasoning skipped. Start Ollama with "
            f"`ollama run {settings.ollama_model}`, or set OPENAI_API_KEY in backend/.env."
        )
        return "", meta

    if settings.use_local_llm:
        try:
            content = call_ollama(system_prompt, user_prompt, timeout_seconds=timeout_seconds)
            meta.update(
                {
                    "provider": "ollama",
                    "model": settings.ollama_model,
                    "status": "ok",
                }
            )
            return content, meta
        except TimeoutError as exc:
            meta["ollamaError"] = str(exc)
            logger.warning("Ollama timed out: %s", exc)
            meta["message"] = (
                f"Ollama timed out after {timeout_seconds or settings.ollama_timeout_seconds}s. "
                "Rule-based and ML parsing still completed."
            )
        except Exception as exc:
            meta["ollamaError"] = str(exc)
            logger.warning("Ollama call failed: %s", exc)

    if _openai_api_key():
        try:
            content = call_openai(system_prompt, user_prompt)
            meta.update(
                {
                    "provider": "openai",
                    "model": settings.openai_model,
                    "status": "ok",
                }
            )
            return content, meta
        except Exception as exc:
            meta["openaiError"] = str(exc)
            logger.warning("OpenAI call failed: %s", exc)

    if meta.get("message"):
        pass
    elif settings.use_local_llm and not _openai_api_key():
        meta["message"] = (
            "LLM reasoning skipped. Start Ollama with "
            f"{settings.ollama_model}, or set OPENAI_API_KEY in backend/.env."
        )
    elif not _openai_api_key():
        meta["message"] = (
            "LLM reasoning skipped. Set USE_LOCAL_LLM=true with Ollama running, "
            "or configure OPENAI_API_KEY."
        )
    else:
        meta["message"] = "LLM reasoning unavailable."

    return "", meta


def llm_available() -> bool:
    settings = get_settings()
    if settings.use_local_llm:
        try:
            base_url = (settings.ollama_base_url or "http://localhost:11434").rstrip("/")
            request = urllib.request.Request(f"{base_url}/api/tags", method="GET")
            with urllib.request.urlopen(request, timeout=3) as response:
                return response.status == 200
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
    return bool(_openai_api_key())
