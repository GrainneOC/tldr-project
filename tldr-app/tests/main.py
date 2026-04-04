from fastapi.testclient import TestClient
from unittest.mock import patch
import json

from main import app

client = TestClient(app)


def test_generate_endpoint_returns_structured_output():
    payload = {"prompt": "Users must provide ID and submit a report every 30 days."}

    mocked_output = json.dumps({
        "obligations": ["Submit a report every 30 days."],
        "required_data": ["Provide ID."],
        "deadlines": ["Every 30 days."],
        "applies_to": ["Users."],
        "unclear_points": []
    })

    with patch("main.ollama_generate", return_value=mocked_output):
        response = client.post("/generate", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "obligations" in data
    assert "required_data" in data
    assert "deadlines" in data
    assert "applies_to" in data
    assert "unclear_points" in data
    assert isinstance(data["obligations"], list)
    assert isinstance(data["required_data"], list)
