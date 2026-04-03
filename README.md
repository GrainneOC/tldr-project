# TL;DR - Terms Long; Didn't Read

> **Final Year Project — Higher Diploma in Computer Science, SETU Waterford**
>
> A comparison of container image vulnerability scanners (Trivy vs Grype) in a CI/CD pipeline, deploying an AI-powered risk assistant for online agreements.

---

## About the Project

This project investigates container image vulnerability scanning within a GitOps-based deployment workflow, comparing two open-source static scanners: **Trivy** (Aqua Security) and **Grype** (Anchore). A small FastAPI application was containerised, stored in GitHub Container Registry (GHCR), and deployed to a local Kubernetes cluster using Helm and ArgoCD. Both scanners were run in GitHub Actions across a sample set of container images, and their results were normalised, compared, and evaluated across detection quality, actionability, and developer experience.

**Research Question:** How do Trivy and Grype compare in detection quality, noise, and developer experience when integrated into a CI/CD pipeline?

---

## Architecture Overview

```
Developer Push to GitHub
        │
        ▼
GitHub Actions CI Pipeline
┌─────────────────────────────────────────┐
│  1. Test (pytest)                       │
│  2. Build Docker image                  │
│  3. Trivy scan      → trivy-report.json │
│  4. Grype scan      → grype-report.json │
│  5. Normalise & Compare (Python)        │
│  6. Policy gate (fail on CRITICAL/HIGH) │
│  7. Push to GHCR (on main, if passes)  │
│  8. Update image tag in values.yaml    │
└─────────────────────────────────────────┘
        │
        ▼
Git (source of truth for manifests)
        │
        ▼
ArgoCD auto-sync
        │
        ▼
Kubernetes cluster (kind)
```

ArgoCD continuously reconciles the live cluster state with the desired state in Git. `selfHeal: true` ensures any manual drift is automatically corrected.

---

## Tech Stack

| Category | Technology |
|---|---|
| Application framework | FastAPI + Uvicorn |
| LLM integration | Ollama (Llama3) |
| Containerisation | Docker (`python:3.13-slim`) |
| Container registry | GitHub Container Registry (GHCR) |
| CI/CD | GitHub Actions |
| Vulnerability scanners | Trivy (Aqua Security), Grype (Anchore) |
| Kubernetes (local) | kind |
| Package management | Helm |
| GitOps | ArgoCD |
| Report normalisation | Python (custom scripts) |

---

## Repository Structure

### tldr-app

This folder contains the application code. The app is called **Terms Long; Didn't Read** - a FastAPI web service that wraps the Llama3 LLM via Ollama to summarise long policy or compliance documents in plain English. It is built on `python:3.13-slim` to keep the container image lightweight, exposes a web UI on port 8000, and is the primary image target for the vulnerability scanning pipeline. The Dockerfile follows container security best practices by using a minimal base image and installing only the dependencies required to run the service.

**Deployment note:** The application connects to Ollama via host.docker.internal, which resolves to the host machine on Docker Desktop. This means the LLM feature works locally but Ollama is not deployed inside the Kubernetes cluster. A full in-cluster deployment would require an Ollama Deployment and Service added to the Helm chart, an init container to pull the Llama3 model, an Ingress controller to expose the app externally, and sufficient GPU resources for the model to run at a practical speed. Due to hardware constraints and project scope, this was a conscious decision. The project demonstrates the full CI/CD and GitOps pipeline with the application running correctly in the local environment, and a full cluster deployment is identified as future work.

```
tldr-app/
├── main.py           # FastAPI application and API endpoints
├── llm_client.py     # Ollama/Llama3 HTTP wrapper
├── static/           # Frontend HTML, CSS, JS
├── Dockerfile        # Container image definition
└── requirements.txt  # Python dependencies (fastapi, uvicorn, requests)
```

### tldr-app-chart

This folder contains the Helm chart used to deploy the application to the Kubernetes cluster. Helm packages the Kubernetes resources into a reusable, parameterised chart, allowing configuration such as the image tag, replica count, and service settings to be managed through `values.yaml`. The CI pipeline automatically updates the `image.tag` field in `values.yaml` with the latest commit SHA after a successful build and scan, which is what triggers ArgoCD to detect a change and deploy the new image. Ingress and HTTPRoute are present in the chart templates but disabled by default, as external exposure of the service was outside the scope of this project.

```
tldr-app-chart/
├── Chart.yaml        # Chart metadata
├── values.yaml       # Configuration values (image tag updated by CI)
└── templates/        # Kubernetes Deployment, Service, Ingress templates
```

### tldr-manifests

This folder contains the ArgoCD Application manifest, which defines how ArgoCD connects to this repository and manages the deployment. It specifies the source repository URL, the branch to track (`main`), and the path to the Helm chart (`tldr-app-chart/`). It also configures the destination namespace (`tldr`) and enables automated sync with `selfHeal: true` and `prune: true`, meaning ArgoCD will automatically apply changes when Git is updated and will remove any resources that are no longer defined in the chart.

```
tldr-manifests/
└── application.yaml  # ArgoCD Application manifest
```

### scripts

This folder contains the Python scripts that form the data processing layer of the pipeline. After Trivy and Grype produce their JSON scan reports, these scripts normalise both outputs into a common CSV format so they can be compared on equal terms. A comparison script computes the overlap between the two scanners - how many vulnerabilities both tools agreed on versus those flagged by only one. A cross-image summary script aggregates results across all scanned images into a single CSV. The policy gate script reads the normalised CSVs and fails the pipeline if any Critical or High vulnerability is found, acting as the single centralised enforcement point for both scanners.

```
scripts/
├── normalize_trivy.py        # Parses Trivy JSON → normalised CSV
├── normalize_grype.py        # Parses Grype JSON → normalised CSV
├── compare.py                # Computes overlap between scanner results per image
├── compare_all_scans.py      # Cross-image comparison summary
├── policy-fail-critical.py   # Policy gate — fails on CRITICAL or HIGH findings
└── local_test_scan.sh        # Local scan script for running pipeline before pushing
```

> **Note for demo purposes:** The policy gate will fail the pipeline if any Critical or High vulnerability is found. To demonstrate a full end-to-end CI/CD run, comment out the `if critical_or_high` block in `scripts/policy-fail-critical.py` before pushing. Remember to uncomment it again afterwards to restore real policy enforcement.

### security

This folder contains the configuration files for both vulnerability scanners. Trivy is configured via `trivy.yml`, which sets the exit code, severity levels, and vulnerability types to scan. Grype is configured via `grype.yml`, which intentionally leaves `fail-on-severity` empty - severity-based failure is handled centrally by the policy gate script rather than by the scanner directly, allowing both scanners' outputs to be evaluated together. Both config files include ignore lists to suppress known false positives. A Rego policy file (`trivy-ignore.rego`) is also provided as a more advanced policy-as-code approach to ignoring specific CVEs, used locally via `local_test_scan.sh`. The `.trivyignore` file in the repo root is used by Trivy in the CI workflow.

```
security/
├── trivy.yml             # Trivy scanner configuration
├── grype.yml             # Grype scanner configuration
└── trivy-ignore.rego     # Rego policy for local Trivy runs (via scan.sh)
```

### reports

This folder stores the scan output artifacts generated by the CI pipeline. Raw JSON reports from Trivy and Grype are produced per run, then normalised into CSV files for analysis and comparison. The policy gate script writes a `fixable-findings.csv` listing all vulnerabilities for which a fix is available. These files are uploaded as GitHub Actions artifacts on each workflow run and are available in the Actions tab for download and inspection.

```
reports/
├── trivy-report.json              # Raw Trivy scan output
├── grype-report.json              # Raw Grype scan output
├── trivy-normalized.csv           # Normalised Trivy findings
├── grype-normalized.csv           # Normalised Grype findings
├── trivy-normalized-<image>.csv   # Per-image Trivy results (sample scans)
├── grype-normalized-<image>.csv   # Per-image Grype results (sample scans)
├── scan-comparison-summary.csv    # Cross-image summary
└── fixable-findings.csv           # Policy gate output
```

### docs

This folder contains the source files for the project's GitHub Pages landing page, built using Jekyll with the minimal theme. The landing page is available at [https://bit.ly/tldr-project](https://bit.ly/tldr-project) and includes a project poster and showcase photo. Links to the video demonstration and presentation slides will be added on completion.

```
docs/
├── index.md      # Landing page content
└── _config.yml   # Jekyll configuration (theme, title, description)
```

### .github/workflows

This folder contains the two GitHub Actions workflow files that automate the CI/CD pipeline. The main workflow (`ci.yml`) triggers on every push or pull request to `main` and runs the full pipeline: tests, Docker build, Trivy scan, Grype scan, normalisation, policy check, image push to GHCR, and manifest update to trigger ArgoCD deployment. The second workflow (`scan-sample-images.yml`) runs manually via `workflow_dispatch` and uses a matrix strategy to pull and scan three Docker Hub base images — `alpine:3.18`, `debian:12`, and `python:3.14-slim` — in parallel, producing per-image results and a cross-image comparison summary.

```
.github/workflows/
├── ci.yml                  # Main CI/CD pipeline
└── scan-sample-images.yml  # Matrix scan of Docker Hub base images
```

---

## Prerequisites

Ensure the following are installed before getting started:

| Tool | Purpose | Install |
|---|---|---|
| Docker | Build and run container images | [docs.docker.com](https://docs.docker.com/get-docker/) |
| Python 3.13 | Run the app and scripts locally | [python.org](https://www.python.org/downloads/) |
| kind | Local Kubernetes cluster | [kind.sigs.k8s.io](https://kind.sigs.k8s.io/) |
| kubectl | Interact with the cluster | [kubernetes.io](https://kubernetes.io/docs/tasks/tools/) |
| Helm | Deploy the app chart | [helm.sh](https://helm.sh/docs/intro/install/) |
| ArgoCD CLI (optional) | Manage ArgoCD from terminal | [argo-cd.readthedocs.io](https://argo-cd.readthedocs.io/en/stable/cli_installation/) |
| Ollama | Run the Llama3 model locally | [ollama.com](https://ollama.com/) |

---

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/GrainneOC/tldr-project.git
cd tldr-project
```

### 2. Run the Application Locally

Pull the Llama3 model (required for the LLM summarisation feature):

```bash
ollama pull llama3
```

Install Python dependencies and start the app:

```bash
cd tldr-app
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The app will be available at [http://localhost:8000](http://localhost:8000).

To build and run via Docker instead:

```bash
cd tldr-app
docker build -t tldr-app:local .
docker run -p 8000:8000 tldr-app:local
```

### 3. Set Up the Local Kubernetes Cluster

```bash
kind create cluster --name tldr-cluster
kubectl cluster-info --context kind-tldr-cluster
```

### 4. Deploy with Helm

```bash
helm install tldr-app ./tldr-app-chart \
  --namespace tldr \
  --create-namespace
```

To upgrade after a values change:

```bash
helm upgrade tldr-app ./tldr-app-chart --namespace tldr
```

To check the deployment:

```bash
kubectl get pods -n tldr
kubectl get svc -n tldr
```

> **Note:** The service is configured as `ClusterIP` (internal only). Ingress and HTTPRoute are disabled by default in `values.yaml`. Port-forward to access locally:
> ```bash
> kubectl port-forward svc/tldr-app 8080:80 -n tldr
> ```

### 5. Set Up ArgoCD

Install ArgoCD into the cluster:

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

Access the ArgoCD UI:

```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

Retrieve the initial admin password:

```bash
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d
```

Apply the ArgoCD Application manifest from `tldr-manifests/`:

```bash
kubectl apply -f tldr-manifests/application.yaml
```

With `selfHeal: true` and automated sync enabled, ArgoCD will automatically deploy any image tag updates committed to `values.yaml` by the CI pipeline.

---

## CI/CD Pipeline

The main CI pipeline (`.github/workflows/ci.yml`) runs on every push or pull request to `main` and consists of the following jobs:

| Job | Description |
|---|---|
| `test` | Sets up Python 3.13, installs dependencies, runs pytest |
| `docker-build` | Builds the `tldr-app:ci-build` Docker image |
| `trivy-scan` | Runs Trivy against the image, outputs `trivy-report.json` |
| `grype-scan` | Runs Grype against the image, outputs `grype-report.json` |
| `normalize-reports` | Normalises both reports to CSV and computes overlap |
| `policy-check` | Fails the pipeline if any CRITICAL or HIGH vulnerability is found |
| `publish-image` | Pushes image to GHCR tagged with `github.sha`, updates `values.yaml` |

On a successful run, the updated `values.yaml` is committed back to the repository, triggering an ArgoCD auto-sync and deployment to the cluster.

---

## Running Scans Locally

Before pushing to GitHub, you can run the full scan pipeline locally using the provided bash script. This builds the image, runs both Trivy and Grype using the config files in `security/`, and normalises the outputs to CSV:

```bash
bash scripts/scan.sh
```

Trivy and Grype must be installed locally for this to work. Results will be written to `reports/trivy-normalized.csv` and `reports/grype-normalized.csv`.

---

## Project Landing Page

A GitHub Pages site for this project is available at [https://bit.ly/tldr-project](https://bit.ly/tldr-project).

It includes a project poster and showcase photo. Links to the video demonstration and presentation slides will be added on completion.

---

## Author

**Gráinne O'Connor**
Higher Diploma in Computer Science
South East Technological University, Waterford
Student Number: 11402918
Supervisor: Peter Windle
Submission: March 2026
