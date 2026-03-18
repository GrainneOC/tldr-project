# scripts/normalize_grype.py
import json
import csv
from pathlib import Path

GRYPE_PATH = Path("reports/grype-report.json")
OUT_PATH = Path("reports/grype-normalized.csv")

def load_grype(path):
    data = json.loads(path.read_text())
    matches = data.get("matches", [])
    rows = []

    for m in matches:
        vuln = m.get("vulnerability", {}) or {}
        art = m.get("artifact", {}) or {}

        rows.append({
            "tool": "grype",
            "target": "",  # fill with image name if you have it elsewhere
            "vuln_id": vuln.get("id"),
            "severity": vuln.get("severity"),
            "package_name": art.get("name"),
        })

    return rows

def main():
    rows = load_grype(GRYPE_PATH)
    fieldnames = ["tool", "target", "vuln_id", "severity", "package_name"]

    with OUT_PATH.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"Wrote {len(rows)} rows to {OUT_PATH}")

if __name__ == "__main__":
    main()

