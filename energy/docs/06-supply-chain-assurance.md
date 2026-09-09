# Software Supply-Chain Assurance

## Purpose

This project uses OpenEMS as the reference energy-management system. The objective of this assurance activity is to establish traceable software provenance and to reduce ambiguity about which upstream source and executable artefacts were used during the resilience experiment.

## Source provenance

The reference OpenEMS source is pinned to:

`189ac916fd653d3496797ac20921d18a2e6237f1`

The upstream repository is maintained outside this project repository. The project therefore records the exact revision rather than copying the OpenEMS source tree into the portfolio repository.

`config/openems-upstream-lock.json` provides the machine-readable source and artefact lock.

## Build provenance

The Edge, Backend and Backend Edge applications were built from the pinned revision using the upstream Gradle build.

For each executable artefact the project records:

- SHA-256 digest;
- byte size;
- embedded JAR count;
- embedded JAR names;
- Java runtime information;
- Gradle wrapper configuration;
- Gradle wrapper JAR digest.

The evidence is stored in:

`evidence/supply-chain/openems-provenance.json`

## Dependency visibility

The executable OpenEMS applications package a large set of OSGi bundles and third-party Java libraries. The embedded-JAR inventory provides visibility of the software packaged into the exact artefacts used by the experiment.

This inventory is not presented as a complete standards-compliant SBOM. A filename-level inventory alone does not establish package provenance, licence status or vulnerability status for every dependency.

## Integrity

SHA-256 is used to detect accidental or unauthorised modification of the recorded build artefacts and evidence files.

A digest establishes byte-level identity. It does not establish that the software is secure or free from vulnerabilities.

## Reproducibility

`scripts/setup-openems.sh` reconstructs the upstream environment from the pinned OpenEMS revision and rebuilds the Edge artefact.

The pinned source revision is the primary reproducibility anchor. Java build artefacts are recorded with their observed hashes rather than assumed to be bit-for-bit reproducible across all build environments.

## Secret handling

Runtime credentials and tokens used by the laboratory are not stored in the repository.

The InfluxDB laboratory token is generated at runtime and retained only under `/tmp`.

Secrets must not be added to evidence files, source code, examples or Git history.

## Supply-chain risks addressed

This evidence contributes to the treatment of:

- R-SUP-006 — unmanaged software dependency;
- R-CFG-008 — uncontrolled configuration or software change;
- R-DAT-010 — weak evidence or operational-data lineage.

It also supports control ENG-SUP-008.

## Limitations

This project does not claim that:

- all OpenEMS dependencies have been independently security reviewed;
- the recorded artefacts are vulnerability-free;
- a filename inventory is equivalent to a full CycloneDX or SPDX SBOM;
- SHA-256 provenance constitutes software-signing or publisher attestation;
- the simulated environment represents the complete software supply chain of a production energy operator.

A production assurance programme would normally extend this work with signed releases, dependency provenance, vulnerability intelligence, licence governance, build attestations, SBOM management and defined remediation ownership.
