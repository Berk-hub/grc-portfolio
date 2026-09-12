# V2 Assurance Summary

This summary reports the deepening layer added after the v1.0 release. The v1.0 experiment evidence and its INCONCLUSIVE result are unchanged; v2 adds the governance, obligation, audit and risk structure around that evidence and identifies a scheduling mechanism that could explain SC-06; the cause of the recorded run remains unconfirmed.

## Service outcome

`SVC-ENERGY-001` — the defined battery balancing function — continued and responded in both directions during the recorded Backend communication loss. This holds for the tested simulated scope only (docs/11-operating-model.md).

## Measured impact

During the outage the controller followed operating-point changes from +4500 W discharge to -2500 W charge with grid power at the 0 W target and zero balance residual within the 50 W tolerance recorded in data/measurement-dictionary.json.

## Evidence confidence

- Evidence integrity: SHA-256 manifests verified on every push; tamper behaviour covered by negative tests (tests/test_evidence_tamper.py), including a documented boundary: a rewritten manifest passes local verification, so the integrity anchor for the manifest itself is git history and CI.
- All model cross-references (obligations, findings, treatments, workpapers) are enforced by tests.
- Review independence is SELF_REVIEW throughout; no simulated approvals exist.

## Open findings

- `FND-REC-001` (HIGH): central backfill unverified. Root cause identified in the pinned source: resend is scheduled 5-65 minutes after reconnection while the v1.0 observation window was 48.8 minutes (docs/13-sc06-root-cause.md). Retest protocol EXP-02 requires a 66+ minute observation window. SC-06 stays INCONCLUSIVE until the retest runs.
- `GAP-GOV-OVERSIGHT` (MEDIUM): single-author project; no independent review exists.
- `GAP-INCIDENT-TTX` (MEDIUM): incident-notification tabletop not yet performed.

## Risk decisions

All twelve risks carry a residual view in data/risk-treatments.json. Residual risk is only reduced where run evidence exists (R-RES-001, R-DAT-010, both scoped); risks without effectiveness evidence stay UNASSESSED or PARTIALLY_ASSESSED. No risk has been accepted.

## Obligation mapping

data/obligations.json records provision-level applicability for NIS2 Articles 20/21/23, UK NIS Regulation 10 and CAF v4.0 principles B5/C1/D1 against two explicit reference entity profiles. EU records stay CONDITIONAL because no member state is selected; mapping is never treated as compliance.

## Limits

Single scenario, simulated assets, shared-host common cause (docs/12-dependency-resilience.md), no IAM or physical testing, no legal opinion. The audit program conclusion pattern is deliberately honest: most controls are "design adequate, operating effectiveness not tested".
