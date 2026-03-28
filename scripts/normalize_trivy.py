import json
import csv
from pathlib import Path

TRIVY_PATH = Path("reports/trivy-report.json")
OUT_PATH = Path("reports/trivy-normalized.csv")

def load_trivy(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    results = data.get("Results", [])
    rows = []

    for res in results:
        target = res.get("Target", "")
        for vuln in res.get("Vulnerabilities", []) or []:
            rows.append({
                "tool": "trivy",
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
    rows = load_trivy(TRIVY_PATH)
    fieldnames = [
        "tool",
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
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {OUT_PATH}")

if __name__ == "__main__":
    main()

