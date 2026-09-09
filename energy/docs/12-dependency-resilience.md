# Dependency and Common-Cause Analysis

## Purpose

The backend-loss experiment exercised one dependency. This analysis records what the other dependencies would do to the service, which of them the laboratory can realistically test, and where the laboratory itself creates common-cause weaknesses that limit generalisation.

This is desk-based analysis. Rows are only marked tested where run evidence exists.

## Dependency propagation

| Dependency | Failure effect on SVC-ENERGY-001 | Laboratory method | Generalisation limit | Status |
|---|---|---|---|---|
| Backend connectivity (D-001) | Central visibility and transfer lost; local control unaffected | TCP relay interruption | Not a physical energy outage | Tested (SCN-BACKEND-LOSS) |
| Meter input (D-002) | Stale or missing control input; controller may act on wrong state | Freeze/drop simulated datasource | Not real sensor electronics | Planned (EXP-05) |
| ESS control path (D-003) | Balancing output has no effect | Disable simulated ESS | Not real power electronics | Planned |
| Local disk | Evidence buffer or RRD4J loss | Isolated quota/directory fault | Not field storage endurance | Planned (EXP-08) |
| Edge process | Control stops until restart | Controlled restart | Not power-electronics behaviour | Planned (EXP-07) |
| Shared host | Edge, Backend and database fail together | Analysis only | No inter-site resilience claim possible | Analysed below |
| Power, cooling, site access | Multiple physical effects | Tabletop only | No physical test evidence | Open (TTX-01, GAP-INCIDENT-TTX) |

## Common-cause limitation of this laboratory

Edge, Backend Edge, Central Backend, InfluxDB and the failure-injection relay all run on one Codespace host. Consequences:

- The experiment can only isolate failures that are injectable above the shared host: network paths and individual processes.
- A host failure would take down the service, its management plane and the evidence pipeline simultaneously. The local RRD4J buffer would be lost with the host, so the "local evidence survives" property holds only against connectivity loss, not against host loss.
- The TCP relay demonstrates communication-path isolation. It does not demonstrate physical or administrative independence between Edge and Backend, and no such claim is made anywhere in this repository.

## Recovery expectations

Per-service targets (impact tolerance, recovery-time objective, data-loss tolerance) are deliberately not filled with invented numbers. They require either a real operator context or an explicitly labelled worked example, and the backend telemetry data-loss question is exactly the open finding `FND-REC-001`. These fields stay open until EXP-02 produces measured gap data to anchor them.
