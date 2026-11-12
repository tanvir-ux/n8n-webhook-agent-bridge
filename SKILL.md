---
name: n8n Webhook Agent Bridge
description: Installs and runs a self-hosted FastAPI bridge that receives n8n webhooks and returns structured JSON from a local agent step. The default step is an offline stub; OpenAI is optional and uses the buyer's own API key.
summary: A self-hosted FastAPI bridge that lets an n8n workflow hand a payload to a custom agent step and get structured JSON back. By default the agent step is an offline stub. OpenAI is optional and uses your own key.
version: 0.1.0
tags:
  - n8n
  - webhook
  - fastapi
  - automation
  - agents
keywords:
  - n8n
  - webhook
  - FastAPI
  - agent bridge
  - LLM stub
  - OpenAI
  - workflow automation
use_cases:
  - Add a custom agent step to an n8n workflow when built-in nodes are not enough
  - Smoke-test an n8n-to-agent webhook path locally with an offline stub and no API key
  - Optionally forward the same webhook payload to OpenAI using your own key
docs_url: https://github.com/tanvir-ux/n8n-webhook-agent-bridge
---

# n8n Webhook Agent Bridge

## Read this first

- This skill is **self-hosted**. Your agent installs and starts the FastAPI bridge on a machine you control. Agensi does not host the service.
- The default agent step is an **offline stub**. It echoes a short processed result and does not call an LLM. You can try the full path without an API key.
- **OpenAI is optional** and uses the **buyer's own key**. The bridge reads `OPENAI_API_KEY` from the environment and calls `https://api.openai.com/v1/chat/completions` only when `USE_STUB_LLM` is set to `false` and a key is present. It never uses an Agensi key for this.
- Set a **webhook secret** in `.env` before you expose the bridge beyond localhost. If `WEBHOOK_SECRET` is set, n8n must send the same value in the `X-Webhook-Secret` header.

## What this skill does

This package contains a small FastAPI service that accepts webhooks from n8n, runs a tool/LLM stub (or an optional OpenAI call), and returns JSON that n8n can use in the next node.

```
n8n Webhook / Cron / Trigger
        │
        ▼
  POST /webhook/n8n   (this bridge, default port 8090)
        │
        ▼
  stub or optional OpenAI  →  JSON back to n8n
```

Use it when a workflow needs a custom agent step that n8n's built-in nodes do not cover yet.

## Prerequisites

- Python 3 with `pip` and the ability to create a virtual environment
- n8n, if you want to import and run the sample workflow (optional for the HTTP smoke tests)
- An OpenAI API key only if you choose to turn off stub mode

Work from the unpacked skill directory (the folder that contains `SKILL.md`, `app/`, `requirements.txt`, `.env.example`, and `n8n/`).

## 1. Create a virtual environment and install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
# On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

To run the packaged tests as well:

```bash
pip install -r requirements-dev.txt
pytest -q
```

## 2. Configure the environment

```bash
cp .env.example .env
```

Edit `.env`:

- Set `WEBHOOK_SECRET` to a long random value you do not commit. The sample n8n workflow sends this as `X-Webhook-Secret`. Leave the header and the env var in sync.
- Keep `USE_STUB_LLM=true` for the default offline stub.
- Leave `OPENAI_API_KEY` empty unless you later enable the optional OpenAI path.
- The documented listen port is `8090`.

Do not commit `.env`. Only `.env.example` should be kept in version control.

## 3. Start the bridge

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8090
```

Leave this process running while you test or connect n8n.

## 4. Check /health

```bash
curl -s http://127.0.0.1:8090/health
```

Expected:

```json
{"status":"UP","service":"n8n-webhook-agent-bridge"}
```

If this fails, the process is not listening on 8090, or another service is bound to that port.

## 5. Send a sample webhook

Use the same secret you put in `.env` (the example file ships with `change-me-in-local-env`):

```bash
curl -s -X POST http://127.0.0.1:8090/webhook/n8n \
  -H 'Content-Type: application/json' \
  -H 'X-Webhook-Secret: change-me-in-local-env' \
  -d '{"tool":"summarize","prompt":"Summarize our onboarding FAQ in 3 bullets"}'
```

If you changed `WEBHOOK_SECRET`, change the header to match. If `WEBHOOK_SECRET` is empty, the header is not required (local open demos only; do not use that configuration off localhost).

## 6. Interpret the JSON

A successful stub response looks like this:

```json
{
  "ok": true,
  "received_tool": "summarize",
  "meta": {},
  "agent": {
    "tool": "summarize",
    "mode": "stub",
    "input_preview": "Summarize our onboarding FAQ in 3 bullets",
    "result": "[stub:summarize] Processed 41 chars. Echo: Summarize our onboarding FAQ in 3 bullets"
  }
}
```

What the fields mean:

- `ok`: the webhook was accepted.
- `received_tool`: the `tool` value from the request body (default `summarize`).
- `meta`: optional metadata from the request; the sample n8n workflow sets `source` and `workflow`.
- `agent.mode`: `stub` in the default configuration. `openai` means a live OpenAI call succeeded. `stub-fallback` means an OpenAI call was attempted and failed, so the stub was used.
- `agent.result`: the stub echo, or the model text when OpenAI is enabled.

The typed endpoint accepts `tool`, `prompt` (or `text` or `message`), and optional `meta`. `POST /webhook/n8n/raw` accepts any JSON body and passes it through.

## 7. Import the sample n8n workflow and point it at the bridge

1. Keep the bridge running on port 8090.
2. In n8n, open **Workflow** → **Import from File** and choose `n8n/sample-webhook-to-bridge.json`.
3. Open the **HTTP Request → Bridge** node and set the URL:
   - `http://host.docker.internal:8090/webhook/n8n` if n8n runs in Docker on Mac or Windows
   - `http://127.0.0.1:8090/webhook/n8n` if n8n and the bridge both run on the host
   - On Linux Docker, `host.docker.internal` may be unavailable; use the host gateway IP or run n8n on the host.
4. Set the `X-Webhook-Secret` header to the same value as `WEBHOOK_SECRET` in `.env`. The sample reads `BRIDGE_WEBHOOK_SECRET` from the n8n environment, or falls back to `change-me-in-local-env`.
5. Activate or test the workflow. The sample Webhook node path is `agent-trigger`. POST a JSON body that includes `prompt` or `text` to that webhook, then confirm the response node returns the bridge JSON described above.

## Optional: use your own OpenAI key

Only do this if you want a real model response instead of the stub.

1. Put your key in `.env` as `OPENAI_API_KEY`. Do not put the key in chat, in `SKILL.md`, or in the n8n export.
2. Set `USE_STUB_LLM=false`.
3. Optionally set `OPENAI_MODEL` (the example default is `gpt-4o-mini`).
4. Restart uvicorn and send the sample curl again. A successful live call returns `"mode": "openai"`. If the call fails, the bridge returns `"mode": "stub-fallback"` and includes an `error` field.

The official OpenAI API is a network call made from the machine running the bridge, using the key in that environment.

## Troubleshooting

- **`/health` connection refused.** The uvicorn process is not running, or it is bound to a different host or port. Recheck the start command and `PORT`.
- **401 `invalid webhook secret`.** The `X-Webhook-Secret` header does not match `WEBHOOK_SECRET`. Align the curl header, the n8n node, and `.env`, then restart the bridge if you just changed `.env`.
- **n8n cannot reach the bridge.** Dockerized n8n cannot use `127.0.0.1` to mean the host; use `host.docker.internal` or the host gateway. Confirm `/health` from the same network namespace n8n uses.
- **`mode` is always `stub`.** `USE_STUB_LLM` is still true, or `OPENAI_API_KEY` is empty. Both must be set as described in the optional OpenAI section.
- **`mode` is `stub-fallback`.** The OpenAI request failed (key, quota, model name, or network). Read `agent.error` and fix the key or connectivity; the bridge will not retry on its own.
- **Import errors when starting uvicorn.** Activate the virtual environment and reinstall `requirements.txt` from the skill directory so `app` is the local package.
- **Port already in use.** Stop the other process on 8090, or change `PORT` and update the curl URL and the n8n HTTP Request node to match.

## Security notes

- Treat `.env` as secret. Never copy `OPENAI_API_KEY` or `WEBHOOK_SECRET` into the listing, into chat, or into a committed file.
- If `WEBHOOK_SECRET` is unset, the bridge accepts webhooks without a header. That is only for local open demos. Set a secret before binding to a public interface or exposing the port beyond localhost.
- This service does not include authentication beyond the shared webhook secret. Do not put it on the public internet without additional protection (firewall, reverse proxy, TLS).
