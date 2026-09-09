# Risk Model

## Purpose

The risk model connects the technical reference architecture to the assurance work.

It includes operational failures, cyber threats, cyber-physical control risks, physical dependencies and governance failures. These are not treated as interchangeable.

A Backend outage, for example, can create a resilience risk without being a cyber attack.

## Scoring

Likelihood and impact are scored from 1 to 5.

| Score | Likelihood | Impact |
|---|---|---|
| 1 | Rare | Limited |
| 2 | Unlikely | Minor |
| 3 | Plausible | Material |
| 4 | Likely | Major |
| 5 | Very likely | Severe |

The inherent score is:

`likelihood x impact`

Ratings used in this project:

- `LOW`: 1–4
- `MEDIUM`: 5–9
- `HIGH`: 10–16
- `CRITICAL`: 17–25

The scores are analytical values for the fictional reference environment. They are not presented as production risk measurements.

## Threat modelling

MITRE ATT&CK for ICS is used selectively where an adversarial technique or impact helps describe the threat.

It is not used as a substitute for the risk register.

The primary scenario, `SCN-BACKEND-LOSS`, is intentionally a failure-injection scenario rather than an assumed cyber attack. This allows the project to assess resilience without inventing an attacker where one is not needed.

Relevant ATT&CK for ICS concepts include:

- Loss of View;
- Manipulation of View;
- Manipulation of Control;
- Impair Process Control;
- Inhibit Response Function.

## Risk treatment rule

A risk is not considered treated because a control has been documented.

The later assurance phase distinguishes:

- control design;
- expected evidence;
- observed evidence;
- test result;
- residual gap.

The machine-readable risk register is held in `data/risks.json`.
