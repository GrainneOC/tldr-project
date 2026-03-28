#!/usr/bin/env python3
import csv
import json
import sys
from pathlib import Path

def read_rows(path: Path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def is_fixable(row):
    fixed_version = (row.get("fixed_version") or "").strip()
    fix_state = (row.get("fix_state") or "").strip().lower()
    return bool(fixed_version) or fix_state in {"fixed", "fix available", "available"}

def main():
    if len(sys.argv) < 2:
        print("Usage: policy.py <normalized-vulnerabilities.csv>", file=sys.stderr)
        sys.exit(2)

    input_csv = Path(sys.argv[1])
    rows = read_rows(input_csv)

    critical = [r for r in rows if (r.get("severity") or "").strip() == "Critical"]
    fixable = [r for r in rows if is_fixable(r)]
    fixable_critical = [r for r in critical if is_fixable(r)]

    print(f"Critical findings: {len(critical)}")
    print(f"Fixable findings: {len(fixable)}")
    print(f"Fixable Critical findings: {len(fixable_critical)}")

    if critical:
        print("FAIL: at least one Critical vulnerability was found")
        sys.exit(1)

    out_json = input_csv.with_name(input_csv.stem + "-fixable.json")
    with out_json.open("w", encoding="utf-8") as f:
        json.dump(fixable, f, indent=2)

    print(f"Wrote fixable vulnerabilities to {out_json}")
    print("PASS: policy satisfied")
    sys.exit(0)

if __name__ == "__main__":
    main()

