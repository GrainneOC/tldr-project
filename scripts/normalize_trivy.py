import json
import csv
from pathlib import Path

REPORTS_ROOT = Path("reports")

FIELDNAMES = [
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

def load_trivy(path, artifact_name):
    data = json.loads(path.read_text(encoding="utf-8"))
    results = data.get("Results", [])
    rows = []

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
    for path in REPORTS_ROOT.rglob("trivy-report.json"):
        artifact_name = path.parent.name
        out_path = REPORTS_ROOT / f"trivy-normalized-{artifact_name}.csv"
        rows = load_trivy(path, artifact_name)

        with out_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)

        print(f"Wrote {len(rows)} rows to {out_path}")

if __name__ == "__main__":
    main()
