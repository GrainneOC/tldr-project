#!/usr/bin/env bash
set -e

# 1) Build image
cd tldr-app
docker build -t tldr-app:ci-build .
cd ..

# 2) Run Trivy scan 
trivy image --format json -o reports/trivy-report.json tldr-app:ci-build

# 3) Run Grype scan
grype tldr-app:ci-build -o json > reports/grype-report.json

# 4) Normalise both reports
python scripts/normalize_trivy.py
python scripts/normalize_grype.py

echo "Done. Check reports/trivy-normalized.csv and reports/grype-normalized.csv"

