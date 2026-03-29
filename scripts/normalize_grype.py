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
            "fixed_version": ";".join(v for v in fixed_versions if v),
        })

    return rows

def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

def main():
    all_rows = []
    report_paths = sorted(REPORTS_ROOT.rglob("grype-report.json"))

    for path in report_paths:
        artifact_name = path.parent.name if path.parent != REPORTS_ROOT else "app"
        rows = load_grype(path, artifact_name)
        all_rows.extend(rows)

        out_path = REPORTS_ROOT / f"grype-normalized-{artifact_name}.csv"
        write_csv(out_path, rows)
        print(f"Wrote {len(rows)} rows to {out_path}")

    stable_out = REPORTS_ROOT / "grype-normalized.csv"
    write_csv(stable_out, all_rows)
    print(f"Wrote {len(all_rows)} total rows to {stable_out}")

if __name__ == "__main__":
    main()
