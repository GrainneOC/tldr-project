package trivy

import rego.v1

default ignore = false

# Ignore this specific CVE 
ignore if {
  input.VulnerabilityID == "CVE-2026-1703"
  input.VulnerabilityID == "CVE-2019-1010022"
}

