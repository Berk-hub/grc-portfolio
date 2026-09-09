# OpenEMS Simulation Smoke Test

## Purpose

Verify that the reference OpenEMS simulation can execute a local battery-balancing control loop before resilience failure injection.

## Result

**SUPPORTED**

- Samples collected: `9`
- Maximum absolute grid active power: `0 W`
- Initial ESS state of charge: `50%`
- Final ESS state of charge: `24%`

## Observation

The balancing controller adjusted ESS active power in response to the simulated consumption and PV profiles. Grid active power remained at 0 W across the recorded samples.

The ESS state-of-charge movement was consistent with the observed charge and discharge direction.

This result establishes a working local-control baseline. It does not yet test resilience to Backend connectivity loss.

## Evidence

- `config/simulator-smoke.json`
- `evidence/simulation/smoke-result.json`
- `evidence/simulation/smoke-result.sha256`
