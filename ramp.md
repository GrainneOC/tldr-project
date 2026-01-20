Project Overview
The core focus is a hands-on assessment of how Trivy, Clair, and Grype integrate into
and influence a modern GitOps-style pipeline, including their impact on developer
workflow, security posture, and release velocity. The RAG LLM crochet-pattern API is
used to represent a typical containerized ML service, ensuring the scanner evaluation
reflects real-world dependency graphs, base images, and runtime concerns common in
AI workloads.​
Goals
●​ Design a robust CI/CD pipeline for containerized applications using Ansible for
configuration, Argo CD for GitOps delivery, and Kubernetes for orchestration.​
●​ Integrate and benchmark Trivy, Clair, and Grype for container image vulnerability
scanning, treating scanner behaviour and results as the primary evaluation
subject.​
●​ Compare usability, detection coverage, false-positive/false-negative behavior,
policy enforcement, and performance of each scanner in a live pipeline.​
●​ Showcase a repeatable, open-source pipeline for secure ML/LLM pattern
deployment that can be adapted to other domains beyond the crochet RAG
example.​
Reference Architecture
●​ Ansible: Automates cluster setup, configuration management, and templating of
Kubernetes manifests, including installing and wiring up Argo CD and
scanner-related configuration.​
●​ Argo CD: Implements declarative GitOps continuous delivery, watching the
manifests repository and reconciling desired and actual state across one or more
Kubernetes clusters.​
●​ Kubernetes: Hosts the RAG LLM crochet-pattern API and supporting services,
providing the runtime context in which scanner-gated images are ultimately
deployed.​
●​ Image scanners (Trivy, Clair, Grype): Run as automated CI steps and/or
cluster-adjacent jobs that scan built images and feed results into pipeline
policies and reporting.
​
Key Pipeline Steps​​

1.​ Developers commit code and Kubernetes manifest changes to Git, including
updates to the RAG LLM service and scanner configuration.​
2.​ The CI system builds container images for each update and pushes them to a
registry.​
3.​ Trivy, Clair, and Grype scan the images; their outputs are normalized for reporting
and used to drive security gates or advisories.​
4.​ Ansible playbooks generate or update Kubernetes manifests and push them to a
Git repository managed as the source of truth.​
5.​ Argo CD detects manifest changes and synchronizes them to the target
Kubernetes cluster, rolling out deployments when security policies are satisfied.​
6.​ Scan results, severity thresholds, and allow/deny policies determine whether
images are promoted, held for manual review, or rejected entirely.

​
Impact and Deliverables
●​ A public GitHub repository containing example manifests, Ansible playbooks, and
end-to-end integrations for Trivy, Clair, and Grype, enabling others to reproduce
the scanner-focused pipeline.​
●​ Documentation and benchmarks comparing scanner performance, integration
complexity, result quality, and developer experience when used in a Cloud ML
Ops context.

Personas
Funtional Requirements
Non-Functional Requirements
Scope​
●​ A step-by-step guide showing how to adapt this architecture to deploy and secure
other ML/LLM services, highlighting patterns for image scanning, GitOps delivery,
and policy-driven promotion.​
