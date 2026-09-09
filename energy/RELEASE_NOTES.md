# v1.1.0 — Assurance deepening

Release date: 2026-09-09

This release adds the governance, obligation, audit and residual-risk layer around the unchanged v1.0 evidence, and identifies the SC-06 root cause from the pinned OpenEMS source: historical resend is scheduled 5-65 minutes after reconnection, while the v1.0 observation window was 48.8 minutes (docs/13-sc06-root-cause.md).

SC-06 and the overall scenario result remain INCONCLUSIVE. The retest protocol (EXP-02) requires an observation window of at least 66 minutes after reconnection and is defined but not yet executed.

New machine-readable models: obligations, entity profiles, findings, risk treatments, audit program, measurement dictionary. New analysis: operating model, dependency and common-cause review, SC-06 root cause, v2 summary. Ten new automated tests enforce cross-references and evidence-tamper detection.

# v1.0.0 — Energy Resilience Assurance Lab

Release date: 2026-09-08

## Assurance result

Primary scenario: SCN-BACKEND-LOSS

SC-01 through SC-05 are SUPPORTED by the recorded laboratory evidence.

SC-06 is INCONCLUSIVE because historical central telemetry reconciliation was not verified in the release evidence set.

Overall scenario result: INCONCLUSIVE.

This classification does not invalidate the supported local-control findings. It preserves the remaining uncertainty instead of inferring successful telemetry reconciliation from connectivity recovery alone.

## Included assurance areas

The release includes system architecture and trust boundaries, asset and dependency modelling, cyber and operational risk, machine-readable controls, UK and EU regulatory applicability, controlled Backend connectivity failure injection, local RRD4J persistence, central InfluxDB evidence, SHA-256 evidence integrity, automated Python assessment, GitHub Actions validation, software provenance, telemetry lineage, data governance and conditional AI governance.

## Key observed behaviour

During Backend communication loss, the local balancing controller responded to both discharge and charge conditions.

The recorded outage operating points included 5200 W consumption with 700 W production and +4500 W ESS response, followed by 1800 W consumption with 4300 W production and -2500 W ESS response.

Grid active power remained at the tested balancing target.

## Boundaries

This release does not claim production operational resilience, legal compliance, penetration-test coverage, IAM effectiveness, physical resilience, vulnerability-free software, a complete CycloneDX or SPDX SBOM, software signing or build attestation.

## Reproduce the assessment

./scripts/assure validate
./scripts/assure assess
./scripts/assure verify-manifest

Pinned OpenEMS source revision:

189ac916fd653d3496797ac20921d18a2e6237f1
