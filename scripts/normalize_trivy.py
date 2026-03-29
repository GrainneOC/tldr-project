import json
import csv
from pathlib import Path

TRIVY_PATH = Path("reports/trivy-report.json")
OUT_PATH = Path("reports/trivy-normalized.csv")

def load_trivy(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    results = data.get("Results") or []
    if not isinstance(results, list):
        results = []

    rows = []

    for res in results:
        if not isinstance(res, dict):
            continue

        target = res.get("Target", "")
        vulns = res.get("Vulnerabilities") or []
        if not isinstance(vulns, list):
            continue

        for vuln in vulns:
            if not isinstance(vuln, dict):
                continue

            rows.append({
                "tool": "trivy",
                "target": target,
                "vuln_id": vuln.get("VulnerabilityID", ""),
                "severity": vuln.get("Severity", ""),
                "package_name": vuln.get("PkgName", ""),
            })

    return rows

def main():
    rows = load_trivy(TRIVY_PATH)
    fieldnames = ["tool", "target", "vuln_id", "severity", "package_name"]

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {OUT_PATH}")

if __name__ == "__main__":
    main()
