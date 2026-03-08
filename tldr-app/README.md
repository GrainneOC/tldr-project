## Running the TL;DR app with Ollama (Linux + Docker)

This app expects an Ollama server running on your host machine and exposes a FastAPI service in Docker that talks to it.

### Prerequisites

- Ollama installed and running on the host (default port `11434`).
- Docker and Docker Compose installed.

### 1. Configure Ollama to listen on all interfaces (Linux)

By default, Ollama listens on `127.0.0.1:11434`, which is not reachable from Docker containers.  
Configure it via a systemd override:

```bash
sudo mkdir -p /etc/systemd/system/ollama.service.d

sudo tee /etc/systemd/system/ollama.service.d/override.conf >/dev/null << 'EOF'
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
EOF

sudo systemctl daemon-reload
sudo systemctl restart ollama

