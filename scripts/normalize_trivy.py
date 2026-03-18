# scripts/normalize_trivy.py
import json
import csv
from pathlib import Path

TRIVY_PATH = Path("reports/trivy-report.json")
OUT_PATH = Path("reports/trivy-normalized.csv")

def load_trivy(path):
    data = json.loads(path.read_text())
    results = data.get("Results", [])
    rows = []

    for res in results:
        target = res.get("Target")
        for vuln in res.get("Vulnerabilities", []) or []:
            rows.append({
                "tool": "trivy",
                "target": target,
                "vuln_id": vuln.get("VulnerabilityID"),
                "severity": vuln.get("Severity"),
                "package_name": vuln.get("PkgName"),
            })

    return rows

def main():
    rows = load_trivy(TRIVY_PATH)
    fieldnames = ["tool", "target", "vuln_id", "severity", "package_name"]

    with OUT_PATH.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"Wrote {len(rows)} rows to {OUT_PATH}")

if __name__ == "__main__":
    main()

