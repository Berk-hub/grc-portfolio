# Energy Lab — working status

Branch: `energy-v2` (work branch; `main` untouched until a package is VERIFIED and reviewed)
Plan: ENERGY_LAB_UYGULAMA_VE_DEVIR_PLANI.md (kept outside the repo) merged with the 12 Sep review-panel findings.
Rule of thumb: a package is VERIFIED only when its acceptance check ran and the output is recorded here.

## Package state

| Pkg | Scope | State | Evidence |
|---|---|---|---|
| P00 | Environment, Appendix A patch, baseline checks | VERIFIED | commit b1f2f12; validate VALID; manifest VALID (24); 29 tests OK; assess INCONCLUSIVE (expected) |
| P01 | Evaluator hardening: limits from dictionary, schema checks, SC-03 trace semantics, manifest scope, CI exit policy | IN_PROGRESS | owner: implementer agent — files: src/energy_assurance/cli.py, tests/, data/measurement-dictionary.json |
| P02 | Clean install + experiment runner (OpenEMS) | TODO | needs Codespace with pinned upstream build |
| P03 | SC-06 real reconciliation (EXP-02) | TODO | depends on P02 |
| P04 | Service and critical-infrastructure model | VERIFIED | commit 4a14c52; data/service-model.json (6 states, 11 transitions, 8 KPIs), docs/18; 28 cross-refs resolve; v1 run sits below example 40% reserve floor — classification note, not a fault |
| P05 | Multi-site, distributed, network experiments | TODO | depends on P02, P04 |
| P06 | Parallel Monte Carlo + scaling measurement | TODO | depends on P04; multi-node HPC stays NOT TESTED unless real nodes exist |
| P07 | Probability, statistics, quantitative risk | TODO | depends on P04, P06 |
| P08 | Cloud/IaC (needs Berk budget approval) | TODO | depends on P02, P05 |
| P09 | Governance/audit/compliance/risk integrity | TODO | after P04 design; effectiveness after P03/P05/P07/P08 |
| P10 | Final delivery, reports regenerated, clean rerun | TODO | last |

## Known limits carried forward (from 12 Sep panel)
- Original run evidence: 4 snapshots over 41 s, single host, simulator-derived channels. Kept as v1 evidence; never edited.
- SC-06 root cause is a candidate (P≈0.27 that resend was still pending); monitor was stopped 19 min before its own budget.
- RRD4J "intact" claim unsupported (5-minute flush cadence); withdrawn until re-measured.
- Experiment runner that produced the v1 evidence is not in the repository.

## Next single step
P01 and P04 agents report; then P02 runner design on the Codespace that still holds the pinned OpenEMS build.

## Berk needed for
Codespace access for P02/P03; budget decision before P08.
