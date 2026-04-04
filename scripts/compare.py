import csv

# File paths
trivy_file = "reports/trivy-normalized.csv"
grype_file = "reports/grype-normalized.csv"

# Read Trivy CSV and collect vuln_ids in a set
trivy_ids = set()
with open(trivy_file) as f:
    reader = csv.DictReader(f)
    for row in reader:
        vuln_id = row.get("vuln_id")
        if vuln_id:
            trivy_ids.add(vuln_id)

# Read Grype CSV and collect vuln_ids in a set
grype_ids = set()
with open(grype_file) as f:
    reader = csv.DictReader(f)
    for row in reader:
        vuln_id = row.get("vuln_id")
        if vuln_id:
            grype_ids.add(vuln_id)

# Calculate overlap and differences
both = trivy_ids.intersection(grype_ids)
only_trivy = trivy_ids.difference(grype_ids)
only_grype = grype_ids.difference(trivy_ids)

# Print counts
print("Total Trivy CVEs:", len(trivy_ids))
print("Total Grype CVEs:", len(grype_ids))
print("Overlap (in both):", len(both))
print("Only in Trivy:", len(only_trivy))
print("Only in Grype:", len(only_grype))

# Print a few example IDs
print("\nExamples only in Trivy:")
for cve in list(only_trivy)[:10]:
    print(" ", cve)

print("\nExamples only in Grype:")
for cve in list(only_grype)[:10]:
    print(" ", cve)

