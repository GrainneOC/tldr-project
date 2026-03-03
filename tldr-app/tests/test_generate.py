from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_generate_endpoint_returns_text():
    payload = {"prompt": "Hello, summarise this"}
    response = client.post("/generate", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "text" in data
    assert isinstance(data["text"], str)
    assert len(data["text"]) > 0
