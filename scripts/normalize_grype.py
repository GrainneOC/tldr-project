import json
import csv
from pathlib import Path

GRYPE_PATH = Path("reports/grype-report.json")
OUT_PATH = Path("reports/grype-normalized.csv")


def get_target_string(source):
    if not isinstance(source, dict):
        return ""

    target = source.get("target", "")
    if isinstance(target, str):
        return target

    if isinstance(target, dict):
        for key in ("userInput", "imageID", "manifestDigest"):
            value = target.get(key, "")
            if isinstance(value, str) and value:
                return value

    return ""


def load_grype(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))

    matches = data.get("matches") or []
    if not isinstance(matches, list):
        matches = []

    source = data.get("source", {}) or {}
    target = get_target_string(source)
    image = target.split(" (", 1)[0] if " (" in target else target

    rows = []

    for m in matches:
        if not isinstance(m, dict):
            continue

        vuln = m.get("vulnerability") or {}
        art = m.get("artifact") or {}

        fixed_version = ""
        fix = vuln.get("fix") or {}
        if isinstance(fix, dict):
            versions = fix.get("versions") or []
            if isinstance(versions, list) and versions:
                fixed_version = str(versions[0] or "")

        rows.append({
            "tool": "grype",
            "image": image,
            "target": target,
            "vuln_id": vuln.get("id", "") or "",
            "severity": (vuln.get("severity") or "").upper(),
            "package_name": art.get("name", "") or "",
            "installed_version": art.get("version", "") or "",
            "fixed_version": fixed_version,
            "status": "fixed" if fixed_version else "affected",
        })

    return rows


def main():
    rows = load_grype(GRYPE_PATH)
    fieldnames = [
        "tool",
        "image",
        "target",
        "vuln_id",
        "severity",
        "package_name",
        "installed_version",
        "fixed_version",
        "status",
    ]

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {OUT_PATH}")


if __name__ == "__main__":
    main()
