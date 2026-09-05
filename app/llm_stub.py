"""LLM / tool stub invoked by the bridge after an n8n webhook."""

from __future__ import annotations

import os
from typing import Any


def run_tool(tool_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    use_stub = os.getenv("USE_STUB_LLM", "true").lower() in {"1", "true", "yes"}
    prompt = str(payload.get("prompt") or payload.get("text") or payload.get("message") or "")
    prompt = prompt.strip() or "(empty prompt)"

    if use_stub or not os.getenv("OPENAI_API_KEY", "").strip():
        return {
            "tool": tool_name,
            "mode": "stub",
            "input_preview": prompt[:200],
            "result": f"[stub:{tool_name}] Processed {len(prompt)} chars. "
            f"Echo: {prompt[:120]}{'…' if len(prompt) > 120 else ''}",
        }

    # Optional real call — skeleton keeps it simple.
    try:
        import httpx

        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        api_key = os.getenv("OPENAI_API_KEY", "")
        resp = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": f"You are tool '{tool_name}'. Reply briefly."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        return {"tool": tool_name, "mode": "openai", "result": text}
    except Exception as exc:
        return {
            "tool": tool_name,
            "mode": "stub-fallback",
            "error": str(exc),
            "result": f"[stub fallback] {prompt[:120]}",
        }
