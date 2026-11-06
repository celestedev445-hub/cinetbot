"""Optional LLM assist. Rule-based extraction remains the source of truth for citations."""
from __future__ import annotations

import json
import logging

import httpx

from .config import settings

log = logging.getLogger(__name__)


def llm_enabled() -> bool:
    return bool(settings.use_llm and settings.openai_api_key)


def suggest_answer(question: str, page_text: str, candidates: list[str]) -> str | None:
    """Ask the LLM to pick among candidates already found on the page.
    Never invents a value: returns None if the model reply is not in page_text / candidates.
    """
    if not llm_enabled() or not candidates:
        return None
    prompt = {
        "question": question,
        "candidates": candidates[:8],
        "instruction": (
            "Pick the single best candidate that answers the question. "
            "Reply with JSON {\"answer\": \"...\"} using only one of the candidates. "
            "If none fit, reply {\"answer\": null}."
        ),
        "page_excerpt": page_text[:4000],
    }
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.post(
                f"{settings.openai_base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.openai_model,
                    "temperature": 0,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You only select from provided candidates. Never invent values.",
                        },
                        {"role": "user", "content": json.dumps(prompt)},
                    ],
                    "response_format": {"type": "json_object"},
                },
            )
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"]
            data = json.loads(content)
            answer = data.get("answer")
            if not answer or not isinstance(answer, str):
                return None
            answer = answer.strip()
            # Cite-or-abstain: must be one of the candidates (already proven on page)
            for c in candidates:
                if answer == c or answer.lower() == c.lower():
                    return c
            return None
    except Exception as exc:  # noqa: BLE001 — optional path must never break MVP
        log.warning("LLM assist skipped: %s", exc)
        return None
