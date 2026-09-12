# Energy Resilience Assurance Lab

[![Assurance Validation](https://github.com/Berk-hub/grc-portfolio/actions/workflows/assurance.yml/badge.svg)](https://github.com/Berk-hub/grc-portfolio/actions/workflows/assurance.yml)

An evidence-led operational resilience and cyber-assurance project built around OpenEMS.

The project examines a specific question:

> Can a local energy-control function continue in a controlled manner when connectivity to the central management environment is temporarily lost, and can the resulting behaviour be reconstructed from evidence?

## What was tested

The reference environment contains simulated solar PV generation, consumption, battery energy storage and grid measurement connected to OpenEMS Edge.

The tested central path is:

Simulated Energy Assets -> OpenEMS Edge -> Controlled Failure Boundary -> Backend Edge Application -> Central OpenEMS Backend -> InfluxDB

A controlled TCP relay was inserted between OpenEMS Edge and the Backend Edge application. The relay was stopped while the Edge, Backend Edge application and Central Backend remained running.

During the communication outage the operating point was changed in both directions: first to require battery discharge, then to require battery charging. The local balancing controller responded to both changes while central communication was unavailable.

## Recorded assurance result

| Criterion | Current result |
|---|---|
| SC-01 — required local measurements remain available | SUPPORTED |
| SC-02 — local control continues | SUPPORTED |
| SC-03 — no unexplained observed control transition | SUPPORTED |
| SC-04 — interruption and restoration are observable | SUPPORTED |
| SC-05 — evidence remains time-orderable | SUPPORTED |
| SC-06 — recovery and historical reconciliation | INCONCLUSIVE |

SC-06 is intentionally separate from simple reconnection. A restored WebSocket connection is not treated as proof that historical telemetry was successfully reconciled centrally.

## Assurance approach

This repository connects technical experimentation with architecture and trust-boundary analysis, asset and dependency modelling, cyber and operational risk, machine-readable controls, UK and EU regulatory applicability, controlled failure injection, local and central telemetry persistence, evidence integrity, software supply-chain provenance, data governance, conditional AI governance and automated assurance assessment.

The objective is not to classify OpenEMS as secure, insecure, compliant or non-compliant. The objective is to define a narrow claim, test it and preserve evidence supporting both positive conclusions and remaining uncertainty.

## Evidence architecture

Failure injection -> runtime observations -> local RRD4J history / central InfluxDB history -> machine-readable JSON evidence -> SHA-256 integrity records -> Python assurance assessment -> GitHub Actions validation.

## Assurance CLI

The repository includes a dependency-free Python assurance tool:

- `./scripts/assure validate`
- `./scripts/assure assess`
- `./scripts/assure verify-manifest`

`validate` checks consistency of the machine-readable assurance models. `assess` evaluates the Backend-connectivity-loss experiment against the defined success criteria. `verify-manifest` checks evidence-file integrity against SHA-256 records.

## Reproducible OpenEMS baseline

The reference OpenEMS source is pinned to commit:

`189ac916fd653d3496797ac20921d18a2e6237f1`

The upstream source tree is intentionally maintained outside this repository. The baseline can be reconstructed with:

`./scripts/setup-openems.sh`

Build provenance and executable hashes are recorded under `evidence/supply-chain/`.

## Repository structure

- `config/` — scenario definitions and upstream source locks
- `data/` — assets, risks, controls and governance models
- `docs/` — architecture and assurance analysis
- `evidence/` — test and provenance evidence
- `scripts/` — environment and assurance tooling
- `src/energy_assurance/` — Python assurance CLI
- `tests/` — automated model and evidence tests
- `../.github/workflows/assurance.yml` — continuous assurance validation

## Key documents

- `docs/01-scope.md` — scope and assurance claim
- `docs/02-success-criteria.md` — test criteria and conclusion rules
- `docs/03-architecture.md` — architecture and trust boundaries
- `docs/04-risk-model.md` — cyber and operational risk model
- `docs/05-regulatory-applicability.md` — UK/EU applicability analysis
- `docs/06-supply-chain-assurance.md` — software provenance
- `docs/07-data-governance.md` — telemetry lineage and data governance
- `docs/08-ai-governance.md` — conditional AI governance
- `docs/09-assurance-report.md` — consolidated assurance report
- [Project report](docs/16-project-report.md) — experiment narrative and limitations
- [Integrated assurance review](docs/17-integrated-assurance-review.md) — findings and control assessment
- Published baseline PDFs: [project report](../reports/Energy-Project-Report.pdf) and [assurance review](../reports/Integrated-Assurance-Review-Energy.pdf). These snapshots predate the reporting corrections in the Markdown sources above; use those sources for the corrected wording.

## Regulatory context

The regulatory register considers relevant UK and EU sources including the UK NIS Regulations, Ofgem guidance, the NCSC Cyber Assessment Framework, NIS2, the Critical Entities Resilience Directive, electricity-sector cybersecurity requirements, the EU Data Act and the EU AI Act.

Law, regulator guidance, assessment frameworks and proposed legislation are kept distinct. Applicability remains conditional where jurisdiction, entity classification, role or deployment context must first be established. Technical control mapping is not treated as evidence of legal compliance.

## Software supply chain

The exact OpenEMS source revision and generated executable artefacts are recorded with SHA-256 hashes. The project also records embedded-JAR inventory and build-environment information.

This provides provenance and dependency visibility. It is not represented as a complete CycloneDX/SPDX SBOM, vulnerability assessment, software-signing scheme or build attestation.

## Data governance

The project distinguishes operational telemetry, cyber-physical control data, configuration and topology, authentication secrets, assurance evidence and software provenance.

Local RRD4J and central InfluxDB persistence distinguish what the Edge observed from what became centrally available.

## Conditional AI governance

No AI or machine-learning system exists in the tested operational control path.

AI governance is therefore treated conditionally rather than added artificially. The repository defines governance gates for possible future forecasting, decision-support and closed-loop AI use, including intended purpose, classification, data provenance, human oversight, deterministic fallback, cybersecurity, logging, monitoring and rollback.

## Limitations

This is a simulated reference environment. The project does not establish production operational resilience, legal or regulatory compliance, that OpenEMS is secure or insecure as a product, absence of software vulnerabilities, physical-site resilience, IAM effectiveness or complete software-supply-chain assurance.

These boundaries are recorded rather than converted into unsupported positive conclusions.

## Current status

The primary Backend-connectivity-loss experiment has been executed and its evidence is machine-readable. Five of the six defined success criteria are currently supported by direct test evidence.

Historical telemetry reconciliation was not verified in the v1.0 evidence set. SC-06 therefore remains INCONCLUSIVE, and the overall scenario result remains INCONCLUSIVE.

The current assessment can be reproduced with:

`./scripts/assure assess`

## Assurance depth (v2)

A second layer was added on top of the v1.0 evidence without changing it:

- provision-level obligation records against explicit entity profiles (`data/obligations.json`, `data/entity-profiles.json`)
- an internal audit program separating design, implementation and operating effectiveness for all eleven controls (`data/audit-program.json`)
- a residual-risk view for all twelve risks with no unevidenced reductions (`data/risk-treatments.json`)
- open findings with owners and closure criteria (`data/findings.json`)
- measurement semantics and operating limits (`data/measurement-dictionary.json`)
- operating model, dependency and common-cause analysis, and the SC-06 scheduling mechanism and unconfirmed cause (`docs/11` to `docs/14`)

Cross-references between these models are enforced by automated tests.

## License and upstream attribution

Original scripts, assurance models and documentation in this repository are released under the MIT License unless otherwise noted.

OpenEMS is an independent upstream project and is not redistributed as part of this repository. OpenEMS remains subject to its own upstream licensing and project terms.
