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

def load_grype(path, artifact_name):
    data = json.loads(path.read_text(encoding="utf-8"))
    matches = data.get("matches", [])
    rows = []

    for m in matches:
        vuln = m.get("vulnerability", {}) or {}
        art = m.get("artifact", {}) or {}
        fix = vuln.get("fix", {}) or {}
        fix_state = fix.get("state") or ""
        fixed_versions = fix.get("versions") or []

        if not isinstance(fixed_versions, list):
            fixed_versions = []

        rows.append({
            "tool": "grype",
            "artifact": artifact_name,
            "target": "",
            "vuln_id": vuln.get("id", ""),
            "severity": vuln.get("severity", ""),
            "package_name": art.get("name", ""),
            "installed_version": art.get("version", ""),
            "fix_state": fix_state,
            "fixed_version": ";".join([v for v in fixed_versions if v]),
        })

    return rows

def main():
    for path in REPORTS_ROOT.rglob("grype-report.json"):
        artifact_name = path.parent.name
        out_path = REPORTS_ROOT / f"grype-normalized-{artifact_name}.csv"
        rows = load_grype(path, artifact_name)

        with out_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)

        print(f"Wrote {len(rows)} rows to {out_path}")

if __name__ == "__main__":
    main()


