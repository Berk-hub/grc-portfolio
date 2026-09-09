# Energy Resilience Assurance Report

## Executive summary

This project evaluates a defined operational-resilience claim in an OpenEMS-based energy-management reference environment.

The principal experiment interrupted the communication path between OpenEMS Edge and the central Backend while preserving the local energy-control process and the remaining Backend services.

**Current scenario result: INCONCLUSIVE**

The experiment supports the conclusion that the tested local battery-balancing function continued to respond to changing simulated energy conditions during loss of central Backend connectivity.

The result is deliberately limited to the tested simulated configuration. It does not establish production resilience, OpenEMS security as a whole, or regulatory compliance.

## Assurance claim

> During a temporary loss of central Backend connectivity, the defined local energy-control function continues in a controlled manner and leaves sufficient evidence to understand the interruption and subsequent recovery.

## Reference environment

The laboratory models a commercial energy site containing solar PV generation, battery energy storage, a grid meter, OpenEMS Edge local control, central Backend services and operator-facing management capability.

OpenEMS source was pinned to commit:

`189ac916fd653d3496797ac20921d18a2e6237f1`

The Edge, Backend and Backend Edge applications were built from this pinned source and recorded with SHA-256 provenance.

## Failure boundary

The tested failure is loss of the Edge-to-Backend communication path.

A controlled TCP relay was inserted into that path. Stopping the relay removed central connectivity without terminating the OpenEMS Edge process, Backend Edge application or central Backend.

This distinguishes communication loss from a full Backend process crash.

## Observed experiment

| Phase | Backend link | Consumption W | Production W | ESS W | Grid W | Residual W |
|---|---:|---:|---:|---:|---:|---:|
| Connected baseline | True | 4100 | 1100 | 3000 | 0 | 0 |
| Outage — discharge | False | 5200 | 700 | 4500 | 0 | 0 |
| Outage — charge | False | 1800 | 4300 | -2500 | 0 | 0 |
| Recovery | True | 4100 | 1100 | 3000 | 0 | 0 |

During the interruption the operating point was changed in both directions.

In the discharge case, consumption exceeded production and the ESS responded with positive active power. In the charge case, production exceeded consumption and the ESS response became negative. Grid active power remained at the tested balancing target.

This provides stronger evidence than observing a controller process remain alive: the local control function reacted to new physical-state inputs while central communication was unavailable.

## Success criteria

- **SC-01: SUPPORTED**
- **SC-02: SUPPORTED**
- **SC-03: SUPPORTED**
- **SC-04: SUPPORTED**
- **SC-05: SUPPORTED**
- **SC-06: INCONCLUSIVE**

SC-06 is treated separately from simple reconnection. Connectivity restoration alone does not establish that historical telemetry generated during the outage was reconciled centrally.

## Evidence architecture

The project uses multiple evidence layers:

- runtime channel observations;
- TCP connection-state observations;
- local RRD4J historical persistence;
- central InfluxDB persistence;
- raw JSON experiment records;
- UTC timestamps;
- SHA-256 evidence manifests;
- Git history;
- automated assessment logic.

## Cyber and operational risk

The risk model covers operational resilience, control manipulation, telemetry integrity, remote access, monitoring, software supply chain, physical dependency, configuration change, recovery, data lineage and governance.

MITRE ATT&CK for ICS mappings are used selectively as adversarial analogues where relevant. The Backend-loss experiment itself is a controlled failure injection and is not represented as a cyberattack.

## Assurance-control coverage

| Control | Coverage |
|---|---|
| `ENG-GOV-001` | EVIDENCED |
| `ENG-ARC-002` | EVIDENCED |
| `ENG-IAM-003` | NOT_TESTED |
| `ENG-CTL-004` | EVIDENCED |
| `ENG-TEL-005` | PARTIAL |
| `ENG-MON-006` | PARTIAL |
| `ENG-REC-007` | INCONCLUSIVE |
| `ENG-SUP-008` | EVIDENCED |
| `ENG-PHY-009` | NOT_TESTED |
| `ENG-CFG-010` | PARTIAL |
| `ENG-DAT-011` | EVIDENCED |

Coverage status is not a compliance status. `EVIDENCED` means that scoped project evidence exists for the stated assurance activity; it does not mean that an organisation-wide control has been certified effective.

## Regulatory applicability

The project separates binding law, regulator guidance, assessment frameworks and proposed legislation.

The regulatory register considers the UK NIS Regulations, Ofgem NIS guidance, the NCSC Cyber Assessment Framework, relevant Ofgem resilience material, EU NIS2, the Critical Entities Resilience Directive, the electricity-sector cybersecurity delegated regulation, the EU Data Act and the EU AI Act.

Applicability is treated as conditional where entity classification, jurisdiction, role, system function or implementation context would need to be established.

A technical control mapping is not treated as proof of legal compliance.

## Software supply chain

The exact upstream OpenEMS revision is pinned and the experiment records hashes for the built Edge, Backend and Backend Edge executables.

The project also records embedded JAR inventory and build-environment information.

This provides software provenance but is not represented as a complete CycloneDX/SPDX SBOM, vulnerability assessment, publisher signature or build attestation.

## Data governance

Operational telemetry, cyber-physical control data, configuration, secrets, assurance evidence and software provenance are treated as separate data classes.

The data lineage distinguishes what was observed locally, what was persisted locally, what reached the central Backend and what was exported as assurance evidence.

The current dataset is simulated and does not intentionally contain personal data. That statement is limited to the laboratory dataset and is not generalised to production energy-management deployments.

## AI governance

No AI or machine-learning system is present in the tested configuration.

The project therefore does not manufacture an AI control test or claim AI Act high-risk compliance.

A conditional governance model is provided for future forecasting, operator decision-support and closed-loop AI control use cases, including intended purpose, human oversight, data governance, safe fallback, cybersecurity, logging, monitoring and rollback.

## Principal findings

**F-01 — Local control continuity:** the tested balancing function continued to react during central communication loss.

**F-02 — Failure observability:** communication loss was observable through connection state and the Backend controller's inability-to-send state.

**F-03 — Local historical persistence:** RRD4J remained healthy and persisted operational channels locally.

**F-04 — Recovery evidence:** connectivity recovery was observed; historical central reconciliation remains dependent on direct resend/backfill evidence.

**F-05 — Untested security domains:** IAM effectiveness and physical/environmental resilience were modelled but not independently exercised.

**F-06 — Supply-chain boundary:** build provenance is evidenced, while full vulnerability, licence, signing and attestation governance remain outside the implemented laboratory evidence.

## Limitations

- The physical energy assets are simulated.
- The experiment represents one defined failure scenario.
- No claim is made that OpenEMS is secure or insecure as a product.
- No penetration test or vulnerability assessment was performed.
- Physical resilience was not tested.
- IAM effectiveness was not tested.
- Regulatory applicability depends on the real operator, entity classification, jurisdiction and system role.
- Simulation evidence does not establish production operational resilience.

## Conclusion

**SCN-BACKEND-LOSS: INCONCLUSIVE**

The evidence supports continuation of the tested local balancing behaviour during temporary loss of central Backend connectivity.

The final scenario classification remains evidence-driven. Any unresolved historical telemetry reconciliation criterion is retained as inconclusive rather than inferred from connectivity recovery alone.
