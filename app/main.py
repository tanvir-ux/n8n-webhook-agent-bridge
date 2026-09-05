"""FastAPI bridge: n8n webhook → LLM/tool stub → JSON response."""

from __future__ import annotations

import os
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

from app.llm_stub import run_tool

load_dotenv()

app = FastAPI(
    title="n8n-webhook-agent-bridge",
    description="Receives n8n webhooks and calls an LLM/tool stub",
    version="0.1.0",
)


class WebhookBody(BaseModel):
    tool: str = Field(default="summarize", description="Tool name for the stub")
    prompt: Optional[str] = None
    text: Optional[str] = None
    message: Optional[str] = None
    meta: Optional[dict[str, Any]] = None


def _check_secret(header_value: Optional[str]) -> None:
    expected = os.getenv("WEBHOOK_SECRET", "").strip()
    if not expected:
        return  # open in local demos when unset
    if header_value != expected:
        raise HTTPException(status_code=401, detail="invalid webhook secret")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "UP", "service": "n8n-webhook-agent-bridge"}


@app.post("/webhook/n8n")
async def webhook_n8n(
    body: WebhookBody,
    x_webhook_secret: Optional[str] = Header(default=None),
) -> dict[str, Any]:
    _check_secret(x_webhook_secret)
    payload = body.model_dump(exclude_none=True)
    tool_result = run_tool(body.tool, payload)
    return {
        "ok": True,
        "received_tool": body.tool,
        "meta": body.meta or {},
        "agent": tool_result,
    }


@app.post("/webhook/n8n/raw")
async def webhook_n8n_raw(
    request: Request,
    x_webhook_secret: Optional[str] = Header(default=None),
) -> dict[str, Any]:
    """Accept any JSON shape n8n might POST (passthrough)."""
    _check_secret(x_webhook_secret)
    data = await request.json()
    if not isinstance(data, dict):
        data = {"prompt": str(data)}
    tool = str(data.get("tool") or "summarize")
    tool_result = run_tool(tool, data)
    return {"ok": True, "agent": tool_result}
