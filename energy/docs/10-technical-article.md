# Testing Local Energy-Control Resilience During Loss of Central Connectivity

## Overview

This project examines one specific operational-resilience question in an OpenEMS-based energy-management environment:

> Can a local battery-balancing function continue to respond correctly when connectivity to central management is temporarily unavailable?

The work combines a real OpenEMS Edge and Backend stack, simulated photovoltaic generation, consumption, battery storage and grid measurement, controlled failure injection, local and central persistence, evidence hashing, automated assurance logic and governance analysis.

The objective is deliberately narrower than asking whether OpenEMS is “resilient” or “secure”. A useful assurance claim needs a defined system boundary, a defined failure, observable success criteria and evidence that can support uncertainty as well as positive conclusions.

## Reference environment

The laboratory contains simulated PV generation, consumption, battery energy storage and grid measurement connected to OpenEMS Edge.

The central path is:

```text
Simulated energy assets
        |
        v
OpenEMS Edge
        |
        | WebSocket
        v
Controlled TCP relay
        |
        v
Backend Edge Application
        |
        v
Central OpenEMS Backend
        |
        v
InfluxDB
```

OpenEMS source was pinned to commit `189ac916fd653d3496797ac20921d18a2e6237f1`. The Edge, Backend and Backend Edge executables were built from that revision and recorded with SHA-256 hashes.

The Edge also uses RRD4J for local historical persistence, allowing local observations to be distinguished from centrally available data.

## Defining the assurance claim

The scoped claim is:

> During a temporary loss of central Backend connectivity, the defined local energy-control function continues in a controlled manner and leaves sufficient evidence to understand the interruption and subsequent recovery.

Six success criteria were defined:

- SC-01: required local measurements remain available;
- SC-02: local control continues;
- SC-03: no unexplained control transition is observed;
- SC-04: interruption and restoration are observable;
- SC-05: evidence remains time-orderable;
- SC-06: recovery is understandable, including historical telemetry reconciliation.

Allowed conclusions are `SUPPORTED`, `NOT SUPPORTED`, `INCONCLUSIVE` and `NOT TESTED`.

This prevents a missing observation from being silently converted into a positive result.

## Establishing the local-control baseline

Before testing resilience, the balancing function was verified under normal conditions.

The simulation used a grid meter, consumption meter, PV production meter, symmetric battery and OpenEMS symmetric balancing controller.

When consumption exceeded PV production, the ESS discharged to cover the difference. When PV exceeded consumption, ESS active power became negative and the battery charged. Grid active power remained at the balancing target.

That established a working local-control baseline before introducing a communication failure.

## Building a real Backend connection

A Backend-loss test requires a real Backend connection first.

The laboratory therefore ran three OpenEMS Java processes:

- OpenEMS Edge;
- Backend Edge Application;
- Central OpenEMS Backend.

The Edge connected through `Controller.Api.Backend`, and established TCP state confirmed the live path.

This distinction matters. Demonstrating that an Edge can operate when it was never connected to a Backend is not equivalent to demonstrating behaviour after connectivity is lost.

## Isolating the failure

Stopping the entire Backend would combine several failure modes.

Instead, a small TCP relay was inserted into the Edge-to-Backend path:

```text
Edge -> controlled relay -> Backend Edge -> Central Backend
```

Failure injection terminated only the relay.

OpenEMS Edge, the local simulation, the balancing controller, Backend Edge and Central Backend all remained running. Only the Edge-to-Backend communication path was interrupted.

This allowed the experiment to test communication loss rather than a complete server shutdown.

## Final experiment

The final run began with an established Backend connection.

### Connected baseline

| Variable | Value |
|---|---:|
| Consumption | 4100 W |
| Production | 1100 W |
| ESS | +3000 W |
| Grid | 0 W |
| Power-balance residual | 0 W |
| Backend link | Connected |
| RRD4J state | OK |

### Outage phase A — discharge

The relay was stopped and the Edge-to-Backend connection disappeared while the Central Backend remained operational.

The operating point was changed:

| Variable | Value |
|---|---:|
| Consumption | 5200 W |
| Production | 700 W |
| ESS | +4500 W |
| Grid | 0 W |
| Power-balance residual | 0 W |
| Edge-to-Backend link | Disconnected |
| Central Backend path | Connected |
| `UnableToSend` | 1 |
| RRD4J state | OK |

The important observation is not simply that the Edge process stayed alive. The physical inputs changed during the outage and the battery response changed with them.

### Outage phase B — charge

The condition was then reversed:

| Variable | Value |
|---|---:|
| Consumption | 1800 W |
| Production | 4300 W |
| ESS | -2500 W |
| Grid | 0 W |
| Power-balance residual | 0 W |
| Edge-to-Backend link | Disconnected |
| Central Backend path | Connected |
| `UnableToSend` | 1 |
| RRD4J state | OK |

The ESS changed from discharge to charge while central communication remained unavailable.

That shows the local controller was responding to new conditions rather than merely holding a previous set-point.

### Recovery

The relay was restarted and the Backend connection returned. RRD4J remained healthy and the local operating point returned to the expected balance.

Connectivity recovery was therefore directly observed.

Historical reconciliation was deliberately treated as a separate question.

## Evidence and telemetry lineage

Operational continuity is only part of resilience. An organisation may also need evidence explaining what occurred during an outage.

The project therefore separates four layers:

1. what OpenEMS Edge observed;
2. what Edge persisted locally;
3. what reached central storage;
4. what was exported as assurance evidence.

A `Timedata.Rrd4j` instance was configured on Edge. Its state was healthy and channel-specific files were created for grid, ESS, production, consumption and SOC data.

A laboratory InfluxDB instance was connected to the central Backend, where timestamped OpenEMS telemetry was observed.

The Edge Backend controller also exposes `UnableToSend` and `LastSuccessfulResend`. During the failure, `UnableToSend` changed as expected. After reconnection, `LastSuccessfulResend` remained subject to separate observation.

This is why SC-06 is not automatically marked supported. Reconnection is not equivalent to proof that every historical sample was reconciled centrally.

## Current result

The machine-readable assessment currently records:

| Criterion | Result |
|---|---|
| SC-01 | SUPPORTED |
| SC-02 | SUPPORTED |
| SC-03 | SUPPORTED |
| SC-04 | SUPPORTED |
| SC-05 | SUPPORTED |
| SC-06 | INCONCLUSIVE |

The overall scenario result is therefore `INCONCLUSIVE`.

That result does not erase the supported local-control findings. It identifies the remaining uncertainty precisely: historical telemetry reconciliation.

## Turning evidence into an executable assurance case

The evidence is not stored only as screenshots.

The repository contains raw JSON experiment records, UTC timestamps, connection-state evidence, local-persistence observations, central-query evidence and SHA-256 manifests.

A small dependency-free Python CLI provides:

```bash
./scripts/assure validate
./scripts/assure assess
./scripts/assure verify-manifest
```

The validator checks consistency across assets, risks, controls and regulatory references. The assessment command evaluates the recorded experiment against the success criteria. The manifest verifier detects changes to recorded evidence.

Automated unit tests and GitHub Actions run these checks continuously.

This makes the repository partly executable: changes to evidence or assurance models can break tests rather than silently changing the conclusion.

## Risk, regulation and governance

The broader risk model covers central connectivity, control integrity, telemetry, privileged access, monitoring, recovery, software supply chain, configuration change, physical dependency, data lineage and governance ownership.

MITRE ATT&CK for ICS is used only where it provides a useful adversarial analogue. The Backend-loss experiment itself is a controlled failure, not an asserted cyberattack.

The regulatory register considers UK NIS requirements, Ofgem guidance, the NCSC Cyber Assessment Framework, EU NIS2, the Critical Entities Resilience Directive, electricity-sector cybersecurity requirements, the EU Data Act and the EU AI Act.

Binding law, guidance, assessment frameworks and conditional future requirements are kept distinct. Technical mapping is not treated as proof of legal compliance.

## Software supply chain

The OpenEMS revision is pinned and the built executables are hashed. The project also records Java and Gradle information and an embedded-JAR inventory.

This improves source and build provenance, but it is not described as a complete SBOM, vulnerability assessment, licence review, software signature or build attestation.

Those would be separate supply-chain assurance activities.

## Data and AI governance

The data-governance model distinguishes operational telemetry, cyber-physical control data, configuration, secrets, assurance evidence and software provenance.

Secrets are excluded from version control. The current dataset is simulated and does not intentionally contain personal data, without generalising that statement to production energy-management systems.

No AI or machine-learning component exists in the tested control path. AI controls are therefore not falsely marked as tested.

Instead, the project defines conditional governance gates for future forecasting, decision-support or closed-loop AI use: intended purpose, classification, data provenance, human oversight, deterministic fallback, cybersecurity, logging, monitoring, change control and rollback.

## Limitations

The energy assets are simulated.

Only one principal connectivity-loss scenario is executed.

The work is not a penetration test and does not classify OpenEMS as secure or insecure.

IAM effectiveness and physical resilience are modelled but not independently exercised.

Build provenance does not establish that every dependency is vulnerability-free.

Regulatory analysis is an applicability and control-mapping exercise rather than a legal opinion or compliance certification.

These boundaries are part of the assurance result.

## Conclusion

The strongest finding is not that an Edge process remained online.

It is that the tested local energy-control function continued to react to materially different operating conditions while the central communication path was unavailable.

The battery moved from discharge to charge as the simulated physical state changed, while grid active power remained at the tested balancing target.

At the same time, the project preserved enough technical evidence to distinguish local control continuity, communication failure, local persistence, central availability and recovery.

The remaining uncertainty is explicit rather than hidden: historical central telemetry reconciliation still requires direct evidence before SC-06 can be upgraded.

That combination of testable claims, controlled failure injection, machine-readable evidence and bounded conclusions is the core of the assurance approach.
