# Data Governance and Telemetry Lineage

## Purpose

Operational resilience depends on both control continuity and trustworthy data.

A local energy-control function may remain operational while central visibility is unavailable. This project therefore distinguishes operational behaviour from telemetry delivery, persistence and assurance evidence.

## Data lineage

The tested data path is:

Simulated field assets → OpenEMS Edge → local balancing control and RRD4J local persistence → Controller.Api.Backend → Backend Edge Application → Central Backend → InfluxDB → assurance evidence.

The Edge-to-Backend communication path is the failure boundary exercised by `SCN-BACKEND-LOSS`.

## Operational telemetry

The principal channels used by the experiment are:

- `_sum/ConsumptionActivePower`
- `_sum/ProductionActivePower`
- `_sum/EssActivePower`
- `_sum/GridActivePower`
- `_sum/EssSoc`

These values are simulated and are not presented as production energy data.

## Cyber-physical control data

Control information is treated separately from ordinary monitoring data because incorrect control behaviour can affect the physical process.

The project distinguishes measurement, controller response, historical persistence, central visibility and exported assurance evidence.

Loss of central visibility is not treated as proof that local control failed.

## Local persistence

`Timedata.Rrd4j` provides local historical persistence.

The laboratory directly observed:

- `rrd4j0/State = 0`;
- channel-specific RRD files;
- persisted consumption, production, grid, ESS and SOC channels.

The runtime RRD database is not committed to Git.

## Central persistence

A laboratory InfluxDB instance is connected to the OpenEMS Backend.

Central queries confirmed timestamped OpenEMS telemetry being persisted.

This allows the assurance analysis to distinguish between:

1. what the Edge observed;
2. what the Edge retained locally;
3. what reached the central system;
4. what was exported into assurance evidence.

## Data quality

The governance model considers:

- provenance;
- integrity;
- timeliness;
- completeness;
- consistency;
- recoverability.

Power-balance calculations provide a consistency check.

UTC timestamps establish ordering of failure and recovery events.

SHA-256 manifests provide tamper-evidence for exported assurance files.

Missing central telemetry is treated as a data gap rather than silently interpreted as a zero measurement.

## Secrets

Authentication material is not assurance evidence.

Runtime credentials, Backend API keys and database tokens must not be stored in Git or published evidence.

## Retention

RRD4J and InfluxDB are laboratory runtime stores in this project.

No production retention period is claimed.

Selected assurance artefacts are retained through version control.

## Privacy boundary

The current test dataset does not intentionally contain personal data.

A production deployment could change this assessment through operator identities, customer records, device ownership or sufficiently granular consumption information.

## EU Data Act

The EU Data Act is maintained as a conditionally relevant source.

The existence of energy telemetry alone is not treated as evidence that every Data Act obligation applies to this simulated laboratory.

## Assurance position

Telemetry lineage now covers field simulation, Edge processing, local persistence, Backend transport, central persistence and exported assurance evidence.

Historic recovery and reconciliation remain independently evidence-driven under `SC-06`.
