#!/usr/bin/env python3
import csv
import json
import sys
from pathlib import Path

REPORTS_ROOT = Path("reports")

def read_rows(path: Path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def is_fixable(row):
    fixed_version = (row.get("fixed_version") or "").strip()
    fix_state = (row.get("fix_state") or "").strip().lower()
    return bool(fixed_version) or fix_state in {"fixed", "fix available", "available"}

def main():
    if len(sys.argv) < 3:
        print("Usage: policy.py <trivy-normalized.csv> <grype-normalized.csv>", file=sys.stderr)
        sys.exit(2)

    trivy_csv = Path(sys.argv[1])
    grype_csv = Path(sys.argv[2])

    rows = read_rows(trivy_csv) + read_rows(grype_csv)

    critical = [r for r in rows if (r.get("severity") or "").strip().lower() == "critical"]
    fixable = [r for r in rows if is_fixable(r)]
    fixable_critical = [r for r in critical if is_fixable(r)]

    print(f"Total findings: {len(rows)}")
    print(f"Critical findings: {len(critical)}")
    print(f"Fixable findings: {len(fixable)}")
    print(f"Fixable Critical findings: {len(fixable_critical)}")

    REPORTS_ROOT.mkdir(parents=True, exist_ok=True)
    out_json = REPORTS_ROOT / "fixable-findings.json"
    with out_json.open("w", encoding="utf-8") as f:
        json.dump(fixable, f, indent=2)

    print(f"Wrote fixable findings to {out_json}")

    if critical:
        print("FAIL: at least one Critical vulnerability was found")
        sys.exit(1)

    print("PASS: policy satisfied")
    sys.exit(0)

if __name__ == "__main__":
    main()
