import json
import csv
from pathlib import Path

REPORTS_ROOT = Path("reports")
OUT_PATH = Path("reports/trivy-normalized.csv")

def load_trivy(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    results = data.get("Results", [])
    rows = []

    artifact_name = path.parts[1] if len(path.parts) > 1 else "unknown"

    for res in results:
        target = res.get("Target", "")
        for vuln in res.get("Vulnerabilities", []) or []:
            rows.append({
                "tool": "trivy",
                "artifact": artifact_name,
                "target": target,
                "vuln_id": vuln.get("VulnerabilityID", ""),
                "severity": vuln.get("Severity", ""),
                "package_name": vuln.get("PkgName", ""),
                "installed_version": vuln.get("InstalledVersion", ""),
                "fix_state": vuln.get("Status", ""),
                "fixed_version": vuln.get("FixedVersion", ""),
            })

    return rows

def main():
    all_rows = []

    for path in REPORTS_ROOT.glob("scan-results-*/trivy-report.json"):
        all_rows.extend(load_trivy(path))

    fieldnames = [
        "tool",
        "artifact",
        "target",
        "vuln_id",
        "severity",
        "package_name",
        "installed_version",
        "fix_state",
        "fixed_version",
    ]

    with OUT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"Wrote {len(all_rows)} rows to {OUT_PATH}")

if __name__ == "__main__":
    main()

