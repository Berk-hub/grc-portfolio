# Service and Critical-Infrastructure Model

## Purpose

`docs/12-dependency-resilience.md` left the per-service targets empty because no operator context existed. This document fills them with an explicitly labelled worked example. The machine-readable form is `data/service-model.json` (`SVC-MODEL-001`). Every number there is tagged `simulator_config`, `assumption` or `derived`. No physical test was performed for this model. Anything marked simulation-only cannot become a physical claim by further simulation.

## Example context

The site is fictional: a commercial microgrid with PV, one battery energy storage system (ESS), a grid connection, one critical load and one deferrable load. It is not a customer or a real site, and its numbers are not vendor limits.

The recorded simulator has one aggregate consumption channel. The load split below is an assumption; implementing it needs two simulated consumption meters, which no recorded configuration has.

| Item | Value | Source |
|---|---:|---|
| ESS capacity | 10200 Wh | simulator config `ess0.capacity` |
| ESS charge / discharge limit | 10000 W each | simulator config |
| Initial SoC | 50 % | simulator config |
| Grid setpoint | 0 W | simulator config `ctrlBalancing0` |
| Controller cycle | 1 s | simulator config `_cycle` |
| Balance tolerance | 50 W | measurement dictionary |
| Critical load `LOAD-CRIT-001` | 2000 W | assumption (about half of the 4100 W baseline) |
| Deferrable load `LOAD-DEF-001` | up to 3000 W | assumption |

## Services, tiers and targets

| Service | Tier | Minimum service level | Outage tolerance | Source |
|---|---|---|---|---|
| `SVC-CRIT-001` critical load | T1 | fulfilment ratio 1.00 over any 60 s | 0 min while reserve remains | assumption |
| `SVC-ENERGY-001` balancing | T2 | grid within 50 W of 0 W each cycle | limited at floor or ceiling | simulator config |
| `SVC-DEF-001` deferrable load | T3 | none; may be set to 0 W | 240 min | assumption |
| `SVC-VIS-001` central visibility | T3 | local record continuous at 1 s; central history complete after backfill | 66 min | derived from `docs/13-sc06-root-cause.md` |

Battery reserve floor, derived: the critical load must run for 2 h with no grid and no PV (assumption). 2000 W x 2 h = 4000 Wh. 4000 / 10200 = 39.2 %, rounded up to 40 % (`LIM-SOC-FLOOR`). Exit hysteresis is 2 % (assumption; the SoC channel is an integer). The simulator enforces a 0 % floor, not 40 %. The 40 % floor is therefore a classification rule applied to evidence, not a simulator behaviour.

Usable balancing energy above the floor, derived: 10200 x (1 - 0.40) = 6120 Wh. At the recorded 3000 W discharge that lasts 2.04 h; at the 10000 W limit, 36.7 min.

Grid import limit, derived: the recorded fuse config value is 32 A. Assuming three phases at 230 V gives 22080 W (`LIM-GRID-IMPORT`). No recorded controller enforces it.

Data-loss and recovery objectives: local record gap tolerance 60 s (assumption); central backfill window 66 min (derived); permanent central loss tolerance 0 Wh after that window (assumption, open as `FND-REC-001`); control reaction 2 s, two cycles (assumption); link-loss detection 60 s (assumption; the v1 evidence bounds it at 12 s).

## Energy equations

Signs follow `data/measurement-dictionary.json`: ESS positive means discharge to the site, grid positive means import.

Power balance per cycle: `P_prod + P_ess + P_grid - P_cons = residual`, with `|residual| <= 50 W`.

SoC evolution, with `P_ess` in W, `dt` in s, `C = 10200 Wh`:

`SoC(t + dt) = SoC(t) - 100 * (P_ess * dt / 3600) / C`

Check against evidence: 3000 W for 41 s is 34.2 Wh, or 0.335 % of capacity. The integer SoC channel staying at 28 % across the 41 s v1 run is consistent with this.

Energy not supplied: `ENS = sum(max(0, P_crit_demand - P_crit_served) * dt / 3600)` in Wh. Fulfilment ratio: `CSF = 1 - ENS / (P_crit_demand * T / 3600)` over a window of `T` s.

Not modelled: charge and discharge efficiency (treated as 100 %), inverter ramp rate, BMS protection and temperature limits, reactive power, grid loss, islanding and protection. These equations describe the simulator. They say nothing about the safety of real equipment.

## Operating states

| State | Priority | Entry | Exit |
|---|---:|---|---|
| `ST-SAFE-CURTAIL` | 1 | at floor with no grid supply, or measurement unreliable for more than 30 s | condition cleared and operator acknowledgement recorded, to recovery |
| `ST-MEAS-UNRELIABLE` | 2 | a required channel older than its stale limit (5 s power, 10 s SoC), residual above 50 W, or a value outside physical bounds | two consecutive fresh, consistent cycles |
| `ST-CAP-LIMIT` | 3 | SoC at or below 40 % with a discharge request, at 100 % with a charge request, or a request above 10000 W | SoC past the 2 % hysteresis band or request within limits |
| `ST-CENTRAL-LOST` | 4 | backend link down (relay port 18081 closed, `UnableToSend` above 0) with fresh local channels | link up, to recovery |
| `ST-RECOVERY` | 5 | a lost dependency returned | `LastSuccessfulResend` non-null and central record matches local, or timeout recorded with a finding |
| `ST-NORMAL` | 6 | all channels fresh, link up, grid within 50 W, SoC inside the band | any other entry condition |

When two entry conditions hold, the lower priority number is reported and the other is kept as a concurrent flag. Example: floor reached while the link is down is `ST-CAP-LIMIT` with a central-lost flag (`TR-11`). Non-zero grid exchange inside `ST-CAP-LIMIT` is expected, not a violation.

Evidence today covers `ST-NORMAL`, `ST-CENTRAL-LOST` and the entry to `ST-RECOVERY` (`SCN-BACKEND-LOSS`). The exit from recovery was never observed (SC-06 INCONCLUSIVE). `ST-MEAS-UNRELIABLE` needs EXP-05; `ST-CAP-LIMIT` needs EXP-06. `ST-SAFE-CURTAIL` and `TR-08` to `TR-10` are simulation-only: no recorded configuration contains grid loss or a curtailment controller. The 30 s and two-cycle thresholds are assumptions. Transitions `TR-01` to `TR-11` in the JSON name the trigger, evidence channel and KPI for each.

## Dependencies and common causes

| Dependency | Failure effect | Cascades to | Group |
|---|---|---|---|
| `DEP-ELEC` grid supply | balancing cannot hold 0 W; ESS alone serves load until the floor | critical and deferrable load | none |
| `DEP-NET` (D-001) | central visibility and transfer lost; local control unaffected | visibility, operator | `CCG-HOST` |
| `DEP-TIME` | evidence cannot be ordered; transition latency unmeasurable | visibility | `CCG-CLOCK` |
| `DEP-DNS-ID` | Edge cannot reach or authenticate to Backend; operator cannot log in | visibility, operator | `CCG-HOST` |
| `DEP-STORE` RRD4J, InfluxDB | local gap or central loss; recovery cannot exit cleanly | visibility | `CCG-HOST` |
| `DEP-HOST` single Codespace | control, management and evidence fail together | every other dependency | `CCG-HOST` |
| `DEP-OPER` | no acknowledgement for curtailment exit | recovery | none |
| `DEP-SUPPLY` OpenEMS build | behaviour changes with revision | balancing, visibility | `CCG-BUILD` |

`CCG-HOST` is the laboratory's own limit: one host failure removes service, management plane and evidence at once. `CCG-CLOCK`: every channel and timestamp shares one host clock, so the residual check is a consistency check, not an independent measurement. `CCG-BUILD`: a defect in the pinned revision affects both ends of D-001. Only `DEP-NET` has been exercised. DNS is never exercised because the Backend URI is `localhost`.

## KPIs

| KPI | Unit | Method | Status | Supplied by |
|---|---|---|---|---|
| `KPI-CSF-001` critical fulfilment ratio | ratio | `1 - ENS / demand energy` over window | NEEDS_EXPERIMENT | second consumption meter, EXP-05 extension |
| `KPI-ENS-001` energy not supplied | Wh | sum of shortfall at 1 s | SIMULATION_ONLY | `gridMode OFF_GRID` run, EXP-06 extension |
| `KPI-LIM-001` limit violations | count | samples breaching grid, power or floor rules | MEASURABLE_NOW | `11-final-reconciliation-run.json` |
| `KPI-LIM-002` violation duration | s | sample intervals in violation | MEASURABLE_NOW | same; resolution 12 s |
| `KPI-SOC-001` reserve margin | Wh | `(SoC - 40) / 100 x 10200` | MEASURABLE_NOW | `_sum/EssSoc` |
| `KPI-TRL-001` transition latency | s | trigger sample to first sample in new state | NEEDS_EXPERIMENT | 1 s log, EXP-05 and EXP-07 |
| `KPI-LINK-001` link-loss detection | s | relay stop to `UnableToSend` above 0 | NEEDS_EXPERIMENT | EXP-02 rerun at 1 s |
| `KPI-REC-001` recovery time | s | link up to verified central history | NEEDS_EXPERIMENT | EXP-02, `14-influx-post-resend.txt` |

Values from the v1 run: `KPI-LIM-001` is 0 for grid and power in 4 snapshots. SoC is 28 % in all 4, 12 points below the example floor, so `KPI-SOC-001` is -1224 Wh. This is not a simulator fault; the simulator enforces 0 %. Under the example floor the whole run would sit in `ST-CAP-LIMIT` with a central-lost flag. `KPI-LIM-002` resolution is about 12 s (4 snapshots over 41 s).

## Limits of this model

- No physical test was performed. Every state, limit and KPI is a rule for classifying simulator output.
- Simulation-only items: `ST-SAFE-CURTAIL`, `TR-08` to `TR-10`, `KPI-ENS-001`, the grid-loss dependency effect and the load split.
- Assumptions can be replaced by an operator's own figures without changing the structure. The JSON marks each one.
- Each state, transition, dependency and KPI links to at least one existing risk (`R-*`) and control (`ENG-*`). Coverage of those controls stays NOT TESTED until the named experiments run.
