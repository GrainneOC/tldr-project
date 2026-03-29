import json
import csv
from pathlib import Path

REPORTS_ROOT = Path("reports")
OUT_PATH = Path("reports/grype-normalized.csv")

def load_grype(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    matches = data.get("matches", [])
    rows = []

    artifact_name = path.parts[1] if len(path.parts) > 1 else "unknown"

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
    all_rows = []

    for path in REPORTS_ROOT.rglob("grype-report.json"):
        all_rows.extend(load_grype(path))

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

