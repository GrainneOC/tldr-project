import requests

OLLAMA_URL = "http://host.docker.internal:11434/api/generate"
MODEL_NAME = "llama3"  # model pulled from Ollama 


def generate(prompt: str) -> str:
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
    }
    resp = requests.post(OLLAMA_URL, json=payload)
    resp.raise_for_status()
    data = resp.json()
    return data.get("response", "")

