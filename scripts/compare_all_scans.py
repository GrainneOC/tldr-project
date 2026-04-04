#!/usr/bin/env python3
import argparse
import csv
import re
import sys
from pathlib import Path


DEFAULT_FIELDS = ["vuln_id", "package_name", "installed_version"]


def normalize_value(value):
    if value is None:
        return ""
    return str(value).strip()


def load_rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_key(row, fields):
    return tuple(normalize_value(row.get(field, "")) for field in fields)


def unique_keys(rows, fields):
    keys = set()
    for row in rows:
        key = build_key(row, fields)
        if any(part for part in key):
            keys.add(key)
    return keys


def detect_image_name(path, prefix):
    name = path.stem
    pattern = rf"^{re.escape(prefix)}-(.+)$"
    match = re.match(pattern, name)
    return match.group(1) if match else None


def pct(part, whole):
    return round((part / whole * 100), 2) if whole else 0.0


def main():
    parser = argparse.ArgumentParser(
        description="Compare all normalized Trivy and Grype CSV files and write a summary CSV."
    )
    parser.add_argument(
        "--reports-dir",
        default="reports",
        help="Directory containing normalized CSV files (default: reports)",
    )
    parser.add_argument(
        "--output",
        default="reports/scan-comparison-summary.csv",
        help="Output summary CSV path (default: reports/scan-comparison-summary.csv)",
    )
    parser.add_argument(
        "--fields",
        default=",".join(DEFAULT_FIELDS),
        help="Comma-separated fields to compare on (default: vulnid,packagename,installedversion)",
    )

    args = parser.parse_args()

    reports_dir = Path(args.reports_dir)
    output_path = Path(args.output)
    fields = [field.strip() for field in args.fields.split(",") if field.strip()]

    if not reports_dir.exists():
        print(f"ERROR: Reports directory not found: {reports_dir}", file=sys.stderr)
        sys.exit(1)

    if not fields:
        print("ERROR: At least one compare field is required", file=sys.stderr)
        sys.exit(1)

    trivy_files = {}
    grype_files = {}

    for path in reports_dir.glob("trivy-normalized-*.csv"):
        image_name = detect_image_name(path, "trivy-normalized")
        if image_name:
            trivy_files[image_name] = path

    for path in reports_dir.glob("grype-normalized-*.csv"):
        image_name = detect_image_name(path, "grype-normalized")
        if image_name:
            grype_files[image_name] = path

    all_images = sorted(set(trivy_files) | set(grype_files))
    if not all_images:
        print("ERROR: No normalized scan CSVs found", file=sys.stderr)
        sys.exit(1)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    summary_rows = []

    for image in all_images:
        trivy_path = trivy_files.get(image)
        grype_path = grype_files.get(image)

        trivy_rows = load_rows(trivy_path) if trivy_path else []
        grype_rows = load_rows(grype_path) if grype_path else []

        trivy_keys = unique_keys(trivy_rows, fields)
        grype_keys = unique_keys(grype_rows, fields)

        overlap = trivy_keys & grype_keys
        only_trivy = trivy_keys - grype_keys
        only_grype = grype_keys - trivy_keys

        summary_rows.append(
            {
                "image": image,
                "compare_fields": ",".join(fields),
                "trivy_file": str(trivy_path) if trivy_path else "",
                "grype_file": str(grype_path) if grype_path else "",
                "trivy_rows": len(trivy_rows),
                "grype_rows": len(grype_rows),
                "trivy_unique": len(trivy_keys),
                "grype_unique": len(grype_keys),
                "overlap": len(overlap),
                "only_trivy": len(only_trivy),
                "only_grype": len(only_grype),
                "trivy_overlap_pct": pct(len(overlap), len(trivy_keys)),
                "grype_overlap_pct": pct(len(overlap), len(grype_keys)),
            }
        )

    fieldnames = [
        "image",
        "compare_fields",
        "trivy_file",
        "grype_file",
        "trivy_rows",
        "grype_rows",
        "trivy_unique",
        "grype_unique",
        "overlap",
        "only_trivy",
        "only_grype",
        "trivy_overlap_pct",
        "grype_overlap_pct",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"Wrote summary: {output_path}")
    for row in summary_rows:
        print(
            f"{row['image']}: "
            f"overlap={row['overlap']}, "
            f"only_trivy={row['only_trivy']}, "
            f"only_grype={row['only_grype']}"
        )


if __name__ == "__main__":
    main()
