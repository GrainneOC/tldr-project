# Rego files are a more sophisticated 
# method of configuring ignore methodolody
# for Trivy scan results. In order to demonstrate
# both ways, this rego file is used only with the
# local ci scan in this repo, while .trivyignore
# is used in the CI/CD pipeline

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
