# Operating Model and Decision Records

## Purpose

The technical models describe what is controlled. This document records who decides, who is accountable and how honest the review process can be in a single-author laboratory.

## Roles

The project defines role models, not staffed positions. One person currently performs all of them.

| Decision | Prepared by | Accountable role | Required record |
|---|---|---|---|
| Service boundary and impact tolerance | Energy/system engineer | Service owner | Rationale, assumptions, date |
| Risk treatment and exceptions | Risk owner | Risk-acceptance authority | Options, residual risk, duration, triggers |
| Control changes | Control owner | Change authority | Impact analysis, test, rollback reference |
| Evidence evaluation | Assessor | Reviewer | Evidence selection and decision rationale |
| Incident-notification assessment | Incident coordinator | Management/legal role | Applicable regime and threshold analysis |

## Review independence

Every review in this repository is recorded as `SELF_REVIEW`. Using different role labels for the same person does not create independent assurance, and no management approval is simulated. This constraint is tracked as `GAP-GOV-OVERSIGHT` in `data/findings.json`.

## Risk appetite statements

- A violation of a defined control-safety limit in simulation fails the affected scenario.
- Unverified recovery blocks any end-to-end recovery claim; a scoped laboratory release remains possible.
- Insufficient evidence is never a justification for a "low risk" rating.
- A risk acceptance records scope, rationale, accountable role, start and end dates, compensating controls and a review trigger. No acceptance exists yet (`data/risk-treatments.json`).
- An accepted risk does not convert an assurance result to SUPPORTED.

## Service definition

`SVC-ENERGY-001`: maintain the defined battery balancing function under simulated consumption and PV conditions. This service is not equated with uninterrupted physical energy supply, grid-loss ride-through or islanding, none of which are demonstrated by the v1.0 evidence.
