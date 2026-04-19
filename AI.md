## AI Prompt & Response Log

- I'm starting a final year project. The app will be a FastAPI service that takes a block of text and sends it to an LLM for summarisation. I also need a CI pipeline and Kubernetes manifests for deployment. What directory structure would you recommend, and how should I set up the basic FastAPI app to start?
```
  A clean structure for this kind of project is to keep the application code, CI config, and deployment manifests in separate top-level directories so they can be developed and reviewed independently:


tldr-project/
├── tldr-app/               # Application code
│   ├── main.py
│   ├── requirements.txt
│   └── Dockerfile
├── tldr-app-chart/         # Helm chart for Kubernetes deployment
├── tldr-manifests/         # ArgoCD Application manifest
├── scripts/                # Data processing and pipeline scripts
└── .github/workflows/      # GitHub Actions CI/CD pipeline


For the FastAPI app, start with a health endpoint and a stub POST endpoint you can build on:

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Terms Long; Didn't Read - TL;DR")

class GenerateRequest(BaseModel):
    prompt: str

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/generate")
async def generate(req: GenerateRequest):
    # Placeholder — LLM integration to follow
    return {"response": f"Received: {req.prompt}"}


Run it with:

```bash
pip install fastapi uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload


The `--reload` flag restarts the server automatically on file saves, which is useful during development. The health endpoint at `/health` will also double as your liveness and readiness probe when you deploy to Kubernetes later.

---
```
- I want to create a separate `llm_client.py` module that handles all communication with Ollama. It should take a prompt string, POST it to the Ollama API, and return the plain text response. The Ollama server will be running on the host machine. What should this look like?
```
Keep it focused — a single `generate()` function that wraps the Ollama `/api/generate` endpoint:

```python
import requests

OLLAMA_URL = "http://host.docker.internal:11434/api/generate"
MODEL_NAME = "llama3"

def generate(prompt: str) -> str:
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
    }
    resp = requests.post(OLLAMA_URL, json=payload, timeout=300)
    resp.raise_for_status()
    data = resp.json()
    return data.get("response", "").strip()


A few things to note:

- **`stream: False`** tells Ollama to return the complete response in one JSON object rather than streaming tokens — simpler to handle in a synchronous endpoint.
- **`timeout=300`** gives the model up to five minutes. LLM inference on CPU is slow and a short timeout will cause spurious failures.
- **`resp.raise_for_status()`** raises an exception for any 4xx/5xx response, which is the right default.
- The URL uses `host.docker.internal` so the same code works both locally and when the app runs inside Docker, with Ollama staying on the host.

Add `requests` to your `requirements.txt`.
```
- What should go in `requirements.txt` for a minimal FastAPI app that calls Ollama over HTTP? I want to keep the container image as small as possible.
```
Three packages — that is all you need:


fastapi
uvicorn
requests


`fastapi` pulls in `pydantic` and `starlette` automatically. `uvicorn` is the ASGI server. `requests` handles the outbound HTTP call to Ollama.

Do not add anything you are not using. Every extra package is additional CVE surface area — which matters in a project where you are actively scanning for vulnerabilities. Using `python:3.13-slim` as your base image already cuts the OS footprint considerably; a lean `requirements.txt` compounds that benefit.

If you are using `uv` to manage the project, lock your dependencies with:

```bash
uv lock


Commit the `uv.lock` file. This ensures reproducible installs across your local environment and CI.
```
-  I want to add a `tests/` directory with a basic test for the health endpoint. What is the simplest setup using pytest and FastAPI's test client?
```
FastAPI includes a `TestClient` built on `httpx` that lets you test endpoints without running a live server. Install the dependencies:

```bash
pip install pytest httpx


Create `tests/test_health.py`:

```python
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


Run with:

```bash
pytest -q


The `-q` flag gives compact output, which is clean for CI logs. Note that if pytest finds no tests it exits with code 5 — your CI workflow handles this by checking whether the `tests/` directory exists before running pytest, avoiding a false failure on an empty test suite.
```
- I have `llm_client.py` working. Now I want to update the `/generate` endpoint in `main.py` so it actually calls the LLM. The response should be structured JSON with five fields: `obligations`, `required_data`, `deadlines`, `applies_to`, and `unclear_points`. How do I handle the prompt engineering and parse the model output reliably?
```
  The key challenge is that LLMs do not always return perfectly formatted JSON — they sometimes add preamble, trailing commentary, or wrap the output in markdown code fences. The safest approach is to instruct the model explicitly to return only JSON, then use a regex to extract the JSON object before parsing.

Update `main.py`:

```python
import json
import re
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from llm_client import generate as ollama_generate

app = FastAPI(title="Terms Long; Didn't Read - TL;DR")

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

class GenerateRequest(BaseModel):
    prompt: str

class GenerateResponse(BaseModel):
    obligations: list[str]
    required_data: list[str]
    deadlines: list[str]
    applies_to: list[str]
    unclear_points: list[str]

@app.get("/")
async def root():
    return FileResponse(STATIC_DIR / "index.html")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    full_prompt = f"""
You are a compliance and policy summarisation assistant.
Read the text and return ONLY valid JSON with this exact structure:
{{
  "obligations": ["..."],
  "required_data": ["..."],
  "deadlines": ["..."],
  "applies_to": ["..."],
  "unclear_points": ["..."]
}}
Rules:
- obligations: list the key duties, obligations, or required actions.
- required_data: list documents, data, evidence, or information required.
- deadlines: list timing requirements, due dates, or frequency obligations.
- applies_to: list who the rule or policy appears to apply to.
- unclear_points: list anything ambiguous, missing, or not clearly specified.
- Use short, practical bullet-style strings.
- If a section has nothing clear, return an empty list.
- Do not include markdown.
- Do not include any text before or after the JSON.
Text:
{req.prompt}
""".strip()

    llm_output = ollama_generate(full_prompt)
    print("RAW MODEL OUTPUT:", llm_output)

    try:
        match = re.search(r'\{.*\}', llm_output, re.DOTALL)
        if not match:
            raise HTTPException(status_code=500, detail="Model did not return valid JSON.")
        data = json.loads(match.group())
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Model did not return valid JSON.")

    for key in ["obligations", "required_data", "deadlines", "applies_to", "unclear_points"]:
        if key not in data or not isinstance(data[key], list):
            raise HTTPException(status_code=500, detail=f"Model response missing or invalid field: {key}")

    return data


The `print("RAW MODEL OUTPUT:", llm_output)` line is intentionally left in during development — it is invaluable for seeing what the model actually returns when things go wrong.
```
- My FastAPI app works when I run it locally calling Ollama, but when I run it inside Docker on Linux I get connection refused on `host.docker.internal:11434`. What is the issue?
```
On Linux, `host.docker.internal` is not automatically resolved by Docker the way it is on Docker Desktop for Mac and Windows. The container cannot reach `127.0.0.1` on the host by default.

There are two fixes:

**Option 1 — `extra_hosts` in Docker Compose (recommended)**

Add this to your service definition in `docker-compose.yml`. It maps `host.docker.internal` to the host gateway at container startup:

```yaml
services:
  tldr-app:
    image: tldr-app:latest
    build: .
    ports:
      - "8000:8000"
    extra_hosts:
      - "host.docker.internal:host-gateway"


No code changes needed — `llm_client.py` continues using `http://host.docker.internal:11434` as the endpoint.

**Option 2 — Configure Ollama to listen on all interfaces**

By default Ollama binds to `127.0.0.1`. Override this with a systemd drop-in:

```bash
sudo mkdir -p /etc/systemd/system/ollama.service.d

sudo tee /etc/systemd/system/ollama.service.d/override.conf >/dev/null << 'EOF'
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
EOF

sudo systemctl daemon-reload
sudo systemctl restart ollama


Option 1 is preferable — it keeps the Ollama configuration untouched and makes the Docker networking requirement self-documenting in the Compose file.
```
- I want to deploy my containerised FastAPI app to a local Kubernetes cluster using Helm, with the image pulled from GHCR. Can you walk me through creating the cluster with kind and setting up the Helm chart?
```
**Create the cluster:**

```bash
kind create cluster --name tldr-cluster
kubectl cluster-info --context kind-tldr-cluster


**Helm chart structure:**


tldr-app-chart/
├── Chart.yaml
├── values.yaml
└── templates/
    ├── deployment.yaml
    └── service.yaml


The key section of `values.yaml` for pulling from GHCR:

```yaml
image:
  repository: ghcr.io/grainneoc/tldr-app
  pullPolicy: IfNotPresent
  tag: latest

containerPort: 8000

service:
  type: ClusterIP
  port: 80


**Deploy:**

```bash
helm install tldr-app ./tldr-app-chart \
  --namespace tldr \
  --create-namespace


**Check it:**

```bash
kubectl get pods -n tldr
kubectl get svc -n tldr


The service type is `ClusterIP` (internal only). To access it locally, use port-forward:

```bash
kubectl port-forward svc/tldr-app 8080:80 -n tldr
``

Since GHCR packages are private by default on first push, you will need an image pull secret in the namespace, or set the package to public in GitHub after the first push.
```
- I have Helm deploying the app manually. Now I want ArgoCD to watch the repository and automatically sync the cluster whenever the image tag in `values.yaml` changes. How do I set up ArgoCD and write the Application manifest?
```
 **Install ArgoCD:**

```bash
kubectl create namespace argocd
kubectl apply -n argocd \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
``

Access the UI:

```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
``

Retrieve the initial admin password:

```bash
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d
``

**Application manifest** — save to `tldr-manifests/application.yaml`:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: tldr-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/grainneoc/tldr-project.git
    targetRevision: main
    path: tldr-app-chart
    helm:
      valueFiles:
        - values.yaml
  destination:
    server: https://kubernetes.default.svc
    namespace: tldr
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
``

Apply it:

```bash
kubectl apply -f tldr-manifests/application.yaml
``

With `selfHeal: true`, ArgoCD automatically reverts any manual changes to the cluster back to what Git says. With `prune: true`, it removes Kubernetes resources that no longer exist in the chart. Once the CI pipeline commits an updated `image.tag` to `values.yaml`, ArgoCD detects the change and redeploys automatically — no manual `helm upgrade` required.
```
- I want the CI pipeline to push the Docker image to GHCR after a successful scan, tagged with the commit SHA. How do I authenticate to GHCR in GitHub Actions and structure the publish job?
```
Add a `publish-image` job gated on `policy-check` passing and running only on merges to `main`:

```yaml
publish-image:
  runs-on: ubuntu-latest
  needs: policy-check
  if: github.ref == 'refs/heads/main'
  permissions:
    contents: write
    packages: write
  env:
    IMAGE_ID: ghcr.io/grainneoc/tldr-app:${{ github.sha }}

  steps:
    - uses: actions/checkout@v4

    - name: Log in to GHCR
      uses: docker/login-action@v3
      with:
        registry: ghcr.io
        username: ${{ github.actor }}
        password: ${{ secrets.GHCR_TOKEN }}

    - name: Build and push image
      run: |
        cd tldr-app
        docker build -t $IMAGE_ID .
        docker push $IMAGE_ID
``

For the token: go to GitHub → Settings → Developer settings → Personal access tokens, generate a token with `write:packages` and `read:packages` scopes, and add it as a repository secret named `GHCR_TOKEN`.

The `permissions: packages: write` block at the job level is also required — without it the workflow will be denied even with a valid PAT. Tag each image with `${{ github.sha }}` rather than `latest` so each push produces an immutable, traceable tag that ArgoCD can detect as a genuine change.
```
- After pushing the image to GHCR I need to update `image.tag` in `values.yaml` with the new commit SHA and commit it back to the repo so ArgoCD syncs. I tried a marketplace action for this but it was not working reliably. Can I just do it inline with a Python script?
```
  Yes — an inline Python script is more reliable and has no external dependency. Add these steps after the image push:

```yaml
- name: Update Helm values image tag
  run: |
    python - <<'PY'
    from pathlib import Path
    import yaml

    path = Path("tldr-app-chart/values.yaml")
    data = yaml.safe_load(path.read_text())
    data["image"]["tag"] = "${{ github.sha }}"
    path.write_text(yaml.safe_dump(data, sort_keys=False))
    PY

- name: Commit and push updated values
  run: |
    git config user.name "github-actions[bot]"
    git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
    git add tldr-app-chart/values.yaml
    git commit -m "Update image tag to ${{ github.sha }}" || exit 0
    git push origin HEAD:main
``

The `|| exit 0` on the commit line is intentional — if `values.yaml` has not changed (e.g. a re-run on the same SHA), git exits with a non-zero code for "nothing to commit", which would otherwise fail the job. This makes the step idempotent.

Using `yaml.safe_load` and `yaml.safe_dump` is more robust than a `sed` substitution, which breaks if the YAML quoting or indentation changes.
```
- I want a Python script that reads both normalised scanner CSVs and fails the pipeline if any CRITICAL severity vulnerability is found. The check needs to be case-insensitive because Trivy outputs `CRITICAL` in uppercase and Grype uses title case. It should also write a CSV of all fixable findings.
```
 ```python
#!/usr/bin/env python3
import csv
import sys
from pathlib import Path

REPORTS_ROOT = Path("reports")

def read_rows(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def is_fixable(row):
    fixed_version = (row.get("fixed_version") or "").strip()
    fix_state = (row.get("fix_state") or "").strip().lower()
    return bool(fixed_version) or fix_state in {"fixed", "fix available", "available"}

def main():
    if len(sys.argv) < 3:
        print("Usage: policy.py <trivy-normalized.csv> <grype-normalized.csv>", file=sys.stderr)
        sys.exit(2)

    rows = read_rows(Path(sys.argv[1])) + read_rows(Path(sys.argv[2]))

    critical_or_high = [
        r for r in rows
        if (r.get("severity") or "").strip().lower() in {"critical", "high"}
    ]
    fixable = [r for r in rows if is_fixable(r)]

    print(f"Total findings: {len(rows)}")
    print(f"Critical or High findings: {len(critical_or_high)}")
    print(f"Fixable findings: {len(fixable)}")

    REPORTS_ROOT.mkdir(parents=True, exist_ok=True)
    out_csv = REPORTS_ROOT / "fixable-findings.csv"

    if fixable:
        fieldnames = list(fixable[0].keys())
        with out_csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(fixable)
    else:
        out_csv.write_text("no fixable findings\n", encoding="utf-8")

    print(f"Wrote fixable findings to {out_csv}")

    if critical_or_high:
        print("FAIL: at least one Critical or High vulnerability was found")
        sys.exit(1)

    print("PASS: policy satisfied")
    sys.exit(0)

if __name__ == "__main__":
    main()
``

`.strip().lower()` on the severity field handles `CRITICAL`, `Critical`, and `critical` without needing a separate normalisation pass. Reading both CSVs and combining into one list gives a single enforcement point for both scanners — rather than running the check twice with potentially different logic.

To temporarily bypass the gate for a demo run, comment out the `if critical_or_high` block and restore it afterwards.
```
- I keep getting errors in my CI workflow and I cannot track down the cause. Can you look at the structure and flag anything wrong - syntax issues, steps that could fail unexpectedly, or things that are just not best practice?
```
 The job dependency chain is correct — `test → docker-build → trivy-scan / grype-scan → normalize-reports → policy-check → publish-image` — but a few things are worth checking:

**Common YAML syntax issues:**

- YAML is indentation-sensitive. The most common silent failure is a step being at the wrong indentation level, making it part of the wrong job. Every `- name:` under `steps:` must be indented exactly two spaces more than `steps:`.
- Inline `run` blocks using `|` (block scalar) must have all lines indented consistently beneath the key.
- Environment variable references like `$IMAGE_ID` in a `run` block need to be defined in `env:` at the job level, or they will be empty at runtime.

**Structural issues:**

- The image is built separately in `docker-build`, `trivy-scan`, and `grype-scan`. Each job gets a fresh runner so the built image does not persist — this is expected behaviour, but it means you are paying for three separate build times.
- `exit-code: '0'` on Trivy and `fail-build: false` on Grype are correct for your design — severity enforcement is centralised in the policy gate, not delegated to individual scanner actions.
- Add `mkdir -p reports` before any step that writes to `reports/` — if the directory does not exist the step will fail with a misleading file-not-found error.

**For the image tag update**, avoid marketplace actions that use `sed` for YAML editing — they are fragile with different quoting styles. An inline Python script using `yaml.safe_load` and `yaml.safe_dump` is more reliable (see the values.yaml update step).
```
- I want a second GitHub Actions workflow that scans a set of base images - alpine:3.18, debian:12, python:3.14-slim - in parallel with both Trivy and Grype, then aggregates the results into a cross-image comparison CSV. How should I structure this?
```
 Use a matrix strategy to fan out the scans in parallel, with a separate `summarize` job that collects all results after the matrix completes:

```yaml
name: Scan Sample Images
on:
  workflow_dispatch:

jobs:
  scan-images:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        image:
          - alpine:3.18
          - debian:12
          - python:3.14-slim

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.13"

      - name: Prepare reports directory
        run: mkdir -p reports

      - name: Pull image
        run: docker pull ${{ matrix.image }}

      - name: Make safe image tag for filenames
        id: names
        run: |
          SAFE_NAME=$(echo "${{ matrix.image }}" | sed 's#[/:]#-#g')
          echo "safe_name=$SAFE_NAME" >> $GITHUB_OUTPUT

      - name: Run Trivy scan
        uses: aquasecurity/trivy-action@0.35.0
        with:
          image-ref: ${{ matrix.image }}
          format: json
          output: reports/trivy-${{ steps.names.outputs.safe_name }}.json
          exit-code: 0

      - name: Install Grype
        uses: anchore/scan-action/download-grype@v4

      - name: Run Grype scan
        env:
          GRYPE_DB_AUTO_UPDATE: "true"
          GRYPE_DB_MAX_ALLOWED_BUILT_AGE: "720h"
        run: |
          grype db update || true
          grype ${{ matrix.image }} -o json \
            > reports/grype-${{ steps.names.outputs.safe_name }}.json

      - name: Normalise reports
        run: |
          cp reports/trivy-${{ steps.names.outputs.safe_name }}.json reports/trivy-report.json
          cp reports/grype-${{ steps.names.outputs.safe_name }}.json reports/grype-report.json
          python scripts/normalize_trivy.py
          python scripts/normalize_grype.py
          cp reports/trivy-normalized.csv \
            reports/trivy-normalized-${{ steps.names.outputs.safe_name }}.csv
          cp reports/grype-normalized.csv \
            reports/grype-normalized-${{ steps.names.outputs.safe_name }}.csv

      - name: Upload reports
        uses: actions/upload-artifact@v4
        with:
          name: scan-${{ steps.names.outputs.safe_name }}
          path: reports/

  summarize:
    runs-on: ubuntu-latest
    needs: scan-images
    steps:
      - uses: actions/checkout@v4
      - name: Download all scan artifacts
        uses: actions/download-artifact@v4
        with:
          path: artifacts
      - name: Collect CSVs into reports directory
        run: |
          mkdir -p reports
          find artifacts -type f \
            \( -name 'trivy-normalized-*.csv' -o -name 'grype-normalized-*.csv' \) \
            -exec cp {} reports/ \;
      - name: Build cross-image summary
        run: |
          python scripts/compare_all_scans.py \
            --reports-dir reports \
            --output reports/scan-comparison-summary.csv
      - name: Upload summary
        uses: actions/upload-artifact@v4
        with:
          name: scan-summary
          path: reports/scan-comparison-summary.csv
``

`fail-fast: false` is important — if one image's scan fails (for example due to a Grype DB update issue), the other matrix jobs should still complete rather than being cancelled. The `grype db update || true` handles intermittent DB update failures by falling back to the cached database rather than failing the job.
```
- I need a Python script that reads all per-image normalised CSVs from a directory, computes the overlap between Trivy and Grype for each image, and writes a summary CSV. Files follow the naming pattern `trivy-normalized-<image>.csv` and `grype-normalized-<image>.csv`. I want to compare on `vuln_id`, `package_name`, and `installed_version` together, not just CVE ID alone.
```
```python
#!/usr/bin/env python3
import argparse
import csv
import re
import sys
from pathlib import Path

DEFAULT_FIELDS = ["vuln_id", "package_name", "installed_version"]

def normalize_value(value):
    return str(value).strip() if value is not None else ""

def load_rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def build_key(row, fields):
    return tuple(normalize_value(row.get(field, "")) for field in fields)

def unique_keys(rows, fields):
    keys = set()
    for row in rows:
        key = build_key(row, fields)
        if any(part for part in key):
            keys.add(key)
    return keys

def detect_image_name(path, prefix):
    match = re.match(rf"^{re.escape(prefix)}-(.+)$", path.stem)
    return match.group(1) if match else None

def pct(part, whole):
    return round((part / whole * 100), 2) if whole else 0.0

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", default="reports")
    parser.add_argument("--output", default="reports/scan-comparison-summary.csv")
    parser.add_argument("--fields", default=",".join(DEFAULT_FIELDS))
    args = parser.parse_args()

    reports_dir = Path(args.reports_dir)
    output_path = Path(args.output)
    fields = [f.strip() for f in args.fields.split(",") if f.strip()]

    trivy_files = {detect_image_name(p, "trivy-normalized"): p
                   for p in reports_dir.glob("trivy-normalized-*.csv")
                   if detect_image_name(p, "trivy-normalized")}
    grype_files = {detect_image_name(p, "grype-normalized"): p
                   for p in reports_dir.glob("grype-normalized-*.csv")
                   if detect_image_name(p, "grype-normalized")}

    all_images = sorted(set(trivy_files) | set(grype_files))
    if not all_images:
        print("ERROR: No normalized scan CSVs found", file=sys.stderr)
        sys.exit(1)

    summary_rows = []
    for image in all_images:
        trivy_rows = load_rows(trivy_files[image]) if image in trivy_files else []
        grype_rows = load_rows(grype_files[image]) if image in grype_files else []

        trivy_keys = unique_keys(trivy_rows, fields)
        grype_keys = unique_keys(grype_rows, fields)
        overlap    = trivy_keys & grype_keys
        only_trivy = trivy_keys - grype_keys
        only_grype = grype_keys - trivy_keys

        summary_rows.append({
            "image": image,
            "compare_fields": ",".join(fields),
            "trivy_unique": len(trivy_keys),
            "grype_unique": len(grype_keys),
            "overlap": len(overlap),
            "only_trivy": len(only_trivy),
            "only_grype": len(only_grype),
            "trivy_overlap_pct": pct(len(overlap), len(trivy_keys)),
            "grype_overlap_pct": pct(len(overlap), len(grype_keys)),
        })

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"Wrote summary: {output_path}")
    for row in summary_rows:
        print(f"  {row['image']}: overlap={row['overlap']}, "
              f"only_trivy={row['only_trivy']}, only_grype={row['only_grype']}")

if __name__ == "__main__":
    main()

Comparing on `(vuln_id, package_name, installed_version)` as a compound key is more precise than CVE ID alone — the same CVE can affect multiple packages, and two findings are only considered equivalent if all three fields match. This is a stricter definition of agreement that is more appropriate for a rigorous scanner comparison.

```
-  I want to add a simple HTML/CSS/JS front end for the TL;DR app. It should have a textarea for pasting in a policy document, a submit button, and display the five sections from the API response clearly. It should live in `tldr-app/static/` and be served by FastAPI at `/`.
```
 Here is a self-contained `index.html` to place in `tldr-app/static/`. FastAPI serves it at `/` via the `FileResponse` route in `main.py`.

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>TL;DR – Terms Long; Didn't Read</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 820px; margin: 2rem auto; padding: 0 1.25rem; color: #222; }
    h1   { font-size: 1.6rem; margin-bottom: 0.2rem; }
    p.sub { color: #666; margin-top: 0; font-size: 0.95rem; }
    textarea { width: 100%; height: 200px; padding: 0.6rem; font-size: 0.95rem; resize: vertical; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
    button   { margin-top: 0.75rem; padding: 0.5rem 1.4rem; font-size: 1rem; cursor: pointer; background: #0066cc; color: white; border: none; border-radius: 4px; }
    button:hover { background: #0052a3; }
    #results { margin-top: 1.75rem; }
    .section { margin-bottom: 1.25rem; }
    .section h2 { font-size: 1rem; font-weight: 600; margin-bottom: 0.3rem; color: #333; border-bottom: 1px solid #eee; padding-bottom: 0.2rem; }
    .section ul { margin: 0.3rem 0 0; padding-left: 1.3rem; }
    .section li { margin-bottom: 0.25rem; font-size: 0.95rem; }
    #error   { color: #c00; margin-top: 1rem; font-size: 0.95rem; }
    #loading { color: #666; margin-top: 1rem; font-style: italic; }
    .hidden  { display: none; }
  </style>
</head>
<body>
  <h1>TL;DR – Terms Long; Didn't Read</h1>
  <p class="sub">Paste a policy, terms of service, or compliance document below.</p>

  <textarea id="prompt" placeholder="Paste your document text here…"></textarea><br/>
  <button id="submit">Summarise</button>

  <div id="loading" class="hidden">Analysing document…</div>
  <div id="error"   class="hidden"></div>

  <div id="results" class="hidden">
    <div class="section"><h2>Obligations</h2><ul id="obligations"></ul></div>
    <div class="section"><h2>Required Data / Documents</h2><ul id="required_data"></ul></div>
    <div class="section"><h2>Deadlines</h2><ul id="deadlines"></ul></div>
    <div class="section"><h2>Applies To</h2><ul id="applies_to"></ul></div>
    <div class="section"><h2>Unclear Points</h2><ul id="unclear_points"></ul></div>
  </div>

  <script>
    const FIELDS = ["obligations","required_data","deadlines","applies_to","unclear_points"];

    document.getElementById("submit").addEventListener("click", async () => {
      const prompt    = document.getElementById("prompt").value.trim();
      const errorEl   = document.getElementById("error");
      const resultsEl = document.getElementById("results");
      const loadingEl = document.getElementById("loading");

      errorEl.classList.add("hidden");
      resultsEl.classList.add("hidden");
      FIELDS.forEach(f => document.getElementById(f).innerHTML = "");

      if (!prompt) {
        errorEl.textContent = "Please paste some text before submitting.";
        errorEl.classList.remove("hidden");
        return;
      }

      loadingEl.classList.remove("hidden");
      try {
        const res  = await fetch("/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt })
        });
        if (!res.ok) throw new Error(`Server returned ${res.status}`);
        const data = await res.json();

        FIELDS.forEach(f => {
          const ul = document.getElementById(f);
          (data[f] || []).forEach(item => {
            const li = document.createElement("li");
            li.textContent = item;
            ul.appendChild(li);
          });
        });
        resultsEl.classList.remove("hidden");
      } catch (err) {
        errorEl.textContent = `Error: ${err.message}`;
        errorEl.classList.remove("hidden");
      } finally {
        loadingEl.classList.add("hidden");
      }
    });
  </script>
</body>
</html>
``

The loading indicator matters here — LLM inference can take several seconds and without feedback the user has no way of knowing the request is in progress.
```
-  My `/generate` endpoint is failing inconsistently — sometimes it works, sometimes I get a 500 error. Looking at the raw model output, the LLM sometimes wraps the JSON in markdown code fences like ` ```json ... ``` ` and sometimes adds text before or after. My current regex is not catching all cases. How do I make the parsing more robust?
```
  The issue is that `re.search(r'\{.*\}', llm_output, re.DOTALL)` works when JSON is bare but fails when the model wraps it in code fences. Strip the fences first, then extract:

```python
import json
import re

def extract_json(raw: str) -> dict:
    # Strip markdown code fences if present
    cleaned = re.sub(r"```(?:json)?", "", raw).strip()

    # Find the outermost JSON object
    match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in model output")

    return json.loads(match.group())
``

Use this in your endpoint:

```python
try:
    data = extract_json(llm_output)
except (ValueError, json.JSONDecodeError) as e:
    raise HTTPException(status_code=500, detail=f"Model did not return valid JSON: {e}")
``

Also check the request timeout in `llm_client.py` — a timeout mid-response returns a truncated string that is syntactically invalid JSON even if the model was about to return something correct:

```python
resp = requests.post(OLLAMA_URL, json=payload, timeout=300)
``

Keep the `print("RAW MODEL OUTPUT:", llm_output)` line in place until the endpoint is consistently stable — it is the fastest diagnostic for unexpected model behaviour.
```
- My policy gate currently only fails on CRITICAL. I want to update it to also fail on HIGH. I also want the fixable findings output to be a CSV file rather than JSON to be consistent with the other report files. How do I implement this?
```
  The severity check is a one-line change — add `"high"` to the set:

```python
critical_or_high = [
    r for r in rows
    if (r.get("severity") or "").strip().lower() in {"critical", "high"}
]
``

For the CSV output, replace any JSON write with:

```python
out_csv = REPORTS_ROOT / "fixable-findings.csv"

if fixable:
    fieldnames = list(fixable[0].keys())
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(fixable)
else:
    out_csv.write_text("no fixable findings\n", encoding="utf-8")
``

Update the artifact upload path in `ci.yml` to `reports/fixable-findings.csv` to match.
```
- Are there any improvements worth making to my Dockerfile? Currently it just copies `requirements.txt` and runs `pip install`.
```
One straightforward improvement is to upgrade pip before installing dependencies. Older pip versions sometimes resolve packages differently or produce warnings that clutter CI output:

```dockerfile
FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip --no-cache-dir -r requirements.txt

COPY main.py llm_client.py ./
COPY static ./static

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
``

The `--no-cache-dir` flag on the `pip install` line tells pip not to write the package cache to disk inside the image layer, which reduces the final image size. The `python:3.13-slim` base image is already a good choice — it excludes the full standard library extras and development tools that the regular `python:3.13` image includes, which is particularly relevant for a project focused on minimising vulnerability surface.
```
*Note: These prompts and responses are representative reconstructions based on the project's commit history, code, and configuration files. The chronology follows the actual commit dates. The analytical decisions - including scanner selection, evaluation framework design, CVE classification, and interpretation of results - were made by the student. AI assisted with implementation speed and concept explanation; it did not make the research decisions.*
