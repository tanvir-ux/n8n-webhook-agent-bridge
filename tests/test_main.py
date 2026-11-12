"""HTTP tests for the n8n webhook agent bridge."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "UP",
        "service": "n8n-webhook-agent-bridge",
    }


def test_stub_webhook_response(monkeypatch) -> None:
    monkeypatch.delenv("WEBHOOK_SECRET", raising=False)
    monkeypatch.setenv("USE_STUB_LLM", "true")

    response = client.post(
        "/webhook/n8n",
        json={
            "tool": "summarize",
            "prompt": "Summarize our onboarding FAQ in 3 bullets",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["received_tool"] == "summarize"
    assert body["agent"]["tool"] == "summarize"
    assert body["agent"]["mode"] == "stub"
    assert "result" in body["agent"]
    assert "[stub:summarize]" in body["agent"]["result"]
    assert "Processed" in body["agent"]["result"]


def test_secret_rejection(monkeypatch) -> None:
    monkeypatch.setenv("WEBHOOK_SECRET", "expected-secret")

    missing = client.post(
        "/webhook/n8n",
        json={"tool": "summarize", "prompt": "hello"},
    )
    assert missing.status_code == 401
    assert missing.json() == {"detail": "invalid webhook secret"}

    wrong = client.post(
        "/webhook/n8n",
        json={"tool": "summarize", "prompt": "hello"},
        headers={"X-Webhook-Secret": "wrong-secret"},
    )
    assert wrong.status_code == 401
    assert wrong.json() == {"detail": "invalid webhook secret"}
