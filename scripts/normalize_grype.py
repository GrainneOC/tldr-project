import json
import csv
from pathlib import Path

GRYPE_PATH = Path("reports/grype-report.json")
OUT_PATH = Path("reports/grype-normalized.csv")

def load_grype(path):
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
    rows = load_grype(GRYPE_PATH)
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

