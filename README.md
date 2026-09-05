# n8n-webhook-agent-bridge

**Small FastAPI bridge** that receives webhooks from **n8n** and calls an LLM/tool stub. Handy when a workflow needs a custom agent step that n8n’s built-in nodes do not cover yet.

## Flow

```
n8n Webhook / Cron / Trigger
        │
        ▼
  POST /webhook/n8n   (this bridge)
        │
        ▼
  LLM / tool stub  →  JSON back to n8n
```

## Quick start

```bash
cd n8n-webhook-agent-bridge
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# optional: set WEBHOOK_SECRET=your-local-secret

uvicorn app.main:app --reload --host 0.0.0.0 --port 8090
```

Smoke test without n8n:

```bash
curl -s http://127.0.0.1:8090/health

curl -s -X POST http://127.0.0.1:8090/webhook/n8n \
  -H 'Content-Type: application/json' \
  -H 'X-Webhook-Secret: change-me-in-local-env' \
  -d '{"tool":"summarize","prompt":"Summarize our onboarding FAQ in 3 bullets"}'
```

## Connect n8n → this bridge

1. Start the bridge on port **8090** (see above).
2. In n8n: **Import** `n8n/sample-webhook-to-bridge.json` (Workflow menu → Import from File).
3. Open the **HTTP Request → Bridge** node:
   - URL: `http://host.docker.internal:8090/webhook/n8n` if n8n runs in Docker on Mac/Windows, or `http://127.0.0.1:8090/webhook/n8n` if both run on the host.
   - Header `X-Webhook-Secret` must match `WEBHOOK_SECRET` in `.env` (or leave both empty for local open demos).
4. Activate / test the workflow. The sample Webhook node path is `agent-trigger`.

### Expected response shape

```json
{
  "ok": true,
  "received_tool": "summarize",
  "meta": { "source": "n8n" },
  "agent": {
    "tool": "summarize",
    "mode": "stub",
    "result": "[stub:summarize] …"
  }
}
```

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness |
| POST | `/webhook/n8n` | Typed body (`tool`, `prompt` / `text` / `message`) |
| POST | `/webhook/n8n/raw` | Any JSON passthrough |

## Env

| Variable | Notes |
|----------|-------|
| `WEBHOOK_SECRET` | If set, require `X-Webhook-Secret` header |
| `USE_STUB_LLM` | `true` (default) = offline stub |
| `OPENAI_API_KEY` | Optional real path |
| `PORT` | Documented default **8090** |

No secrets are committed — only `.env.example`.

MIT License.
