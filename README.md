# TL;DR - Terms Long; Didn't Read

> **Final Year Project - Higher Diploma in Computer Science, SETU Waterford**
>
> A comparison of container image vulnerability scanners (Trivy vs Grype) in a CI/CD pipeline, deploying an AI-powered risk assistant for online agreements.

---

## About the Project

This project investigates container image vulnerability scanning within a GitOps-based deployment workflow, comparing two open-source static scanners: **Trivy** (Aqua Security) and **Grype** (Anchore). A small FastAPI application was containerised, stored in GitHub Container Registry (GHCR), and deployed to a local Kubernetes cluster using Helm and ArgoCD. Both scanners were run in GitHub Actions across a sample set of container images, and their results were normalised, compared, and evaluated across detection quality, actionability, and developer experience.

**Research Question:** How do Trivy and Grype compare in detection quality, noise, and developer experience when integrated into a CI/CD pipeline?

---

## Live Deployment
The application is publicly accessible at:
http://18.201.115.12.nip.io
It is deployed on an AWS EC2 instance (eu-west-1) running a kind Kubernetes cluster, with ArgoCD managing continuous deployment from this repository. LLM inference is provided by the Groq API (Llama3), replacing the original local Ollama dependency.

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
Kubernetes cluster (kind on AWS EC2 t3.large, eu-west-1)
        │
        ▼
nginx ingress → FastAPI pod → Groq API (Llama3)
```

ArgoCD continuously reconciles the live cluster state with the desired state in Git. `selfHeal: true` ensures any manual drift is automatically corrected.

---

## Tech Stack

| Category | Technology |
|---|---|
| Application framework | FastAPI + Uvicorn |
| LLM integration | Llama3 via Groq API (cloud deployment) / Ollama (Local development) |
| Containerisation | Docker (`python:3.13-slim`) |
| Container registry | GitHub Container Registry (GHCR) |
| CI/CD | GitHub Actions |
| Vulnerability scanners | Trivy (Aqua Security), Grype (Anchore) |
| Kubernetes | kind (local and AWS EC2) |
| Package management | Helm |
| GitOps | ArgoCD |
| Ingress | nginx ingress controller |
| Cloud deployment | AWS EC2 t3.large, eu-west-1 |
| Report normalisation | Python (custom scripts) |

---

## Repository Structure

### tldr-app

This folder contains the application code. The app is called Terms Long; Didn't Read — a FastAPI web service that uses the Llama3 LLM to summarise long policy or compliance documents in plain English. It is built on python:3.13-slim to keep the container image lightweight, exposes a web UI on port 8000, and is the primary image target for the vulnerability scanning pipeline. The Dockerfile follows container security best practices by using a minimal base image and installing only the dependencies required to run the service.
LLM integration: The application supports two modes:

Cloud deployment (default): Calls the Groq API using GROQ_API_KEY, which runs Llama3 on Groq's LPU hardware and responds in approximately 2 seconds. No GPU required.
Local development: Calls a locally running Ollama instance via host.docker.internal:11434. Requires Ollama installed and llama3 pulled. Response times depend on local hardware.

The active mode is determined by llm_client.py. For cloud deployment the Groq API key is stored as a Kubernetes secret and injected as an environment variable at runtime.

```
tldr-app/
├── main.py           # FastAPI application and API endpoints
├── llm_client.py     # Groq API / Llama3 client
├── static/           # Frontend HTML, CSS, JS
├── Dockerfile        # Container image definition
└── requirements.txt  # Python dependencies (fastapi, uvicorn, requests, groq, python-dotenv)
```

### tldr-app-chart

This folder contains the Helm chart used to deploy the application to the Kubernetes cluster. Helm packages the Kubernetes resources into a reusable, parameterised chart, allowing configuration such as the image tag, replica count, and service settings to be managed through values.yaml. The CI pipeline automatically updates the image.tag field in values.yaml with the latest commit SHA after a successful build and scan, which is what triggers ArgoCD to detect a change and deploy the new image.

```
tldr-app-chart/
├── Chart.yaml        # Chart metadata
├── values.yaml       # Configuration values (image tag updated by CI)
└── templates/        # Kubernetes Deployment, Service, Ingress templates
    ├── deployment.yaml
    ├── service.yaml
    └── ingress.yaml  # nginx ingress — enabled for cloud deployment
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
| Groq API | Run Llama3 via Groq API by creating GROQ_API_KEY | [console.groq.com](https://console.groq.com/keys) |

---

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/GrainneOC/tldr-project.git
cd tldr-project
```

### 2. Run the Application Locally

#### Option A — Using Groq API (recommended, fast)
Create a .env file in tldr-app/:
```
GROQ_API_KEY=your_key_here
```
Install dependencies and start the app:
```

cd tldr-app
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
#### Option B — Using Ollama (local LLM, slower)
Pull the Llama3 model:
```

ollama pull llama3
```
Update `MODEL_NAME` in `llm_client.py` to point at your local Ollama instance, then start the app as above.
The app will be available at http://localhost:8000.
To build and run via Docker:
```

cd tldr-app
docker build -t tldr-app:local .
docker run -p 8000:8000 -e GROQ_API_KEY=your_key_here tldr-app:local
```
### 3. Set Up the Local Kubernetes Cluster
For local use, create a standard kind cluster: 
```

kind create cluster --name tldr-cluster
kubectl cluster-info --context kind-tldr-cluster
```
For a cluster with ingress support (required for public access), create with port mappings:
```
cat <<EOF | kind create cluster --name tldr-cluster --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  kubeadmConfigPatches:
  - |
    kind: InitConfiguration
    nodeRegistration:
      kubeletExtraArgs:
        node-labels: "ingress-ready=true"
  extraPortMappings:
  - containerPort: 80
    hostPort: 80
    protocol: TCP
  - containerPort: 443
    hostPort: 443
    protocol: TCP
EOF
```
### 4. Create Secrets
Create the namespace and required secrets before deploying:
```
kubectl create namespace tldr

# GHCR image pull secret
kubectl create secret docker-registry ghcr-secret \
  --docker-server=ghcr.io \
  --docker-username=GrainneOC \
  --docker-password=YOUR_GHCR_TOKEN \
  --namespace tldr

# Groq API key
kubectl create secret generic groq-secret \
  --from-literal=GROQ_API_KEY=your_groq_key_here \
  --namespace tldr
```
### 5. Deploy with Helm
```
helm install tldr-app ./tldr-app-chart \
  --namespace tldr \
  --values ./tldr-app-chart/values.yaml
```
To upgrade after a values change:

```
helm upgrade tldr-app ./tldr-app-chart \
  --namespace tldr \
  --values ./tldr-app-chart/values.yaml
```

To check the deployment:

```
kubectl get pods -n tldr
kubectl get svc -n tldr
kubectl get ingress -n tldr
```

> **Note:** The service is configured as `ClusterIP` (internal only). Ingress and HTTPRoute are disabled by default in `values.yaml`. Port-forward to access locally:
> ```bash
> kubectl port-forward svc/tldr-app 8080:80 -n tldr
> ```

### 6. Install nginx Ingress Controller
For ingress to work with kind, use the kind-specific manifest:
```
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml

kubectl wait --namespace ingress-nginx \
  --for=condition=ready pod \
  --selector=app.kubernetes.io/component=controller \
  --timeout=90s
```
### 7. Set Up ArgoCD
Install ArgoCD into the cluster:

```
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

Access the ArgoCD UI:

```

kubectl port-forward svc/argocd-server -n argocd 8080:443
```

Retrieve the initial admin password:

```

kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d
```

Apply the ArgoCD Application manifest:

```
kubectl apply -f tldr-manifests/application.yaml
```

With `selfHeal: true` and automated sync enabled, ArgoCD will automatically deploy any image tag updates committed to `values.yaml` by the CI pipeline.

---
## Cloud Deployment (AWS EC2)
The application is deployed to an AWS EC2 instance running a kind Kubernetes cluster. The setup mirrors the local Kubernetes deployment with the following differences:
| Aspect | Local | AWS EC2 |
|---|---|---|
| Cluster | kind (laptop) | kind (t3.large, eu-west-1) |
| LLM | Ollama or Groq | Groq API only |
| App access | port-forward | nginx ingress + nip.io |
| ArgoCD | local sync | syncs from GitHub |
| Public URL | none | http://18.201.115.12.nip.io |

The EC2 instance requires port 80 and port 443 open in the security group inbound rules. The kind cluster must be created with `extraPortMappings` (see step 3 above) for the nginx ingress controller to bind to the host network.
The `GROQ_API_KEY` is stored as a Kubernetes secret (`groq-secret`) and injected into the FastAPI pod at runtime via the deployment template environment variable configuration.
Note on kind and cloud providers: A production deployment would use a managed Kubernetes service such as GKE or EKS, which provides a real cloud load balancer, automatic external IP assignment, and cluster resilience across node failures. kind on EC2 is used here to demonstrate the full GitOps pipeline within the project scope. The kind cluster does not survive an EC2 instance reboot - it would need to be recreated.

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

It includes links to the video demonstration, presentation slides and final report.

---

## Author

**Gráinne O'Connor**
Higher Diploma in Computer Science
South East Technological University, Waterford
Student Number: 11402918
Supervisor: Peter Windle
Submission: March 2026
