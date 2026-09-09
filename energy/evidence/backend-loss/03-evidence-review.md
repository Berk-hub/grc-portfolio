# Backend Connectivity Loss — Evidence Review

## Scenario

`SCN-BACKEND-LOSS`

A controlled TCP relay was placed between OpenEMS Edge and the Backend Edge application. The relay was stopped to interrupt only the Edge-to-Backend communication path while the Edge, Backend Edge application and central Backend remained running.

## Observed states

| Phase | Backend link | Consumption W | Production W | ESS W | Grid W | SOC % | Residual W |
|---|---:|---:|---:|---:|---:|---:|---:|
| Pre-failure | True | 4000 | 1000 | 3000 | 0 | 46 | 0 |
| Outage — discharge | False | 5000 | 500 | 4500 | 0 | 46 | 0 |
| Outage — charge | False | 2000 | 4500 | -2500 | 0 | 46 | 0 |
| Recovery | True | 4000 | 1000 | 3000 | 0 | 46 | 0 |

## Success-criteria assessment

- **SC-01 — SUPPORTED:** Required local measurements remained available during the interruption.
- **SC-02 — SUPPORTED:** Local battery control responded to changed operating conditions during the interruption.
- **SC-03 — SUPPORTED:** No unexplained control transition was observed in the captured outage states.
- **SC-04 — SUPPORTED:** Loss and restoration of the central communication path were observable.
- **SC-05 — SUPPORTED:** Evidence contains ordered UTC timestamps.
- **SC-06 — INCONCLUSIVE:** Connectivity recovery was observed, but Backend-side telemetry gap handling and reconciliation have not yet been directly evidenced.

## Current scenario conclusion

**INCONCLUSIVE**

The experiment provides evidence that the tested local balancing function continued to respond while the Edge-to-Backend communication path was unavailable. The result is not yet classified as fully SUPPORTED because recovery evidence does not yet establish how Backend-side telemetry gaps are reconciled.

This conclusion is limited to the simulated reference configuration and does not establish production resilience or regulatory compliance.

