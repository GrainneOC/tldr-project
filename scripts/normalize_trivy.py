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

def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

def main():
    all_rows = []
    report_paths = sorted(REPORTS_ROOT.rglob("trivy-report.json"))

    for path in report_paths:
        artifact_name = path.parent.name if path.parent != REPORTS_ROOT else "app"
        rows = load_trivy(path, artifact_name)
        all_rows.extend(rows)

        out_path = REPORTS_ROOT / f"trivy-normalized-{artifact_name}.csv"
        write_csv(out_path, rows)
        print(f"Wrote {len(rows)} rows to {out_path}")

    stable_out = REPORTS_ROOT / "trivy-normalized.csv"
    write_csv(stable_out, all_rows)
    print(f"Wrote {len(all_rows)} total rows to {stable_out}")

if __name__ == "__main__":
    main()
