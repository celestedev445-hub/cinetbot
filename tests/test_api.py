from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_home_has_start_url_field():
    r = client.get("/")
    assert r.status_code == 200
    assert "start_url" in r.text
    assert "CiteBot" in r.text


def test_api_ask_empty_question():
    r = client.post("/api/ask", json={"question": ""})
    assert r.status_code == 200
    data = r.json()
    assert data["abstained"] is True
    assert data["reason"] == "empty_question"


def test_api_ask_accepts_start_url():
    # Network may fail; ensure schema accepts start_url and returns shape
    r = client.post(
        "/api/ask",
        json={
            "question": "What is the Pro plan price?",
            "start_url": "https://example.com/pricing",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert "abstained" in data
    assert "hops" in data
    assert "answer" in data
