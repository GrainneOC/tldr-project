package trivy

import rego.v1

default ignore = false

allowed_ids := {
  "CVE-2026-1703",
  "CVE-2019-1010022",
}

ignore if {
  input.VulnerabilityID in allowed_ids
}
