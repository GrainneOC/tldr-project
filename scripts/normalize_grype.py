import json
import csv
from pathlib import Path

GRYPE_PATH = Path("reports/grype-report.json")
OUT_PATH = Path("reports/grype-normalized.csv")

def load_grype(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    matches = data.get("matches") or []
    if not isinstance(matches, list):
        matches = []

    source = data.get("source", {}) or {}
    target = source.get("target", "") or ""

    rows = []

    for m in matches:
        if not isinstance(m, dict):
            continue

        vuln = m.get("vulnerability") or {}
        art = m.get("artifact") or {}

        rows.append({
            "tool": "grype",
            "target": target,
            "vuln_id": vuln.get("id", ""),
            "severity": vuln.get("severity", ""),
            "package_name": art.get("name", ""),
        })

    return rows

def main():
    rows = load_grype(GRYPE_PATH)
    fieldnames = ["tool", "target", "vuln_id", "severity", "package_name"]

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {OUT_PATH}")

if __name__ == "__main__":
    main()
