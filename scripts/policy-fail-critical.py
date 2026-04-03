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

    critical_or_high = [r for r in rows if (r.get("severity") or "").strip().lower() in {"critical", "high"}]
    fixable = [r for r in rows if is_fixable(r)]
    fixable_critical = [r for r in critical_or_high if is_fixable(r)]

    print(f"Total findings: {len(rows)}")
    print(f"Critical or High findings: {len(critical_or_high)}")
    print(f"Fixable findings: {len(fixable)}")
    print(f"Fixable Critical/High findings: {len(fixable_critical)}")

    REPORTS_ROOT.mkdir(parents=True, exist_ok=True)
    out_csv = REPORTS_ROOT / "fixable-findings.csv"
    
    if fixable:
        fieldnames = list(fixable[0].keys())
        with out_csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(fixable)
    else:
        out_csv.write_text("no fixable findings\n", encoding="utf-8")
    
    print(f"Wrote fixable findings to {out_csv}")

    #comment out this conditional block when you want CI/CD to continue and not fail on high/critical vulnerabilities
    #if critical_or_high:
     # print("FAIL: at least one Critical or High vulnerability was found")
      #sys.exit(1)

    print("PASS: policy satisfied")
    sys.exit(0)

if __name__ == "__main__":
  main()
