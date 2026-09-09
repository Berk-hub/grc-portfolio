# Regulatory Applicability

## Principle

The reference architecture is not treated as a regulated entity.

Regulation applies to an organisation, activity and jurisdiction in context. OpenEMS is the technical reference system used by this project; it is not described as an Operator of Essential Services, essential entity, important entity or critical entity.

For that reason, every regulatory source has an explicit applicability status.

## Great Britain

### Network and Information Systems Regulations 2018

**Project status: `CONDITIONAL`**

The Regulations form the current statutory baseline for the GB profile where the fictional operator is assumed to fall within the relevant OES regime.

The project does not claim that an arbitrary commercial battery-and-solar site would automatically qualify.

### Ofgem NIS Guidance v3.0

**Project status: `CONDITIONAL`**

The January 2026 guidance is the main regulatory-assurance reference for the GB downstream gas and electricity profile.

The project uses its emphasis on risk management, CAF assessment, improvement planning and assurance to structure evidence and testing.

### NCSC CAF v4.0

**Project status: `REFERENCE_FRAMEWORK`**

CAF is used as an outcome-based assessment framework.

It is not represented as legislation.

The core objectives used by this project are:

- Objective A — Managing security risk;
- Objective B — Protecting against cyber attack;
- Objective C — Detecting cyber security events;
- Objective D — Minimising the impact of cyber security incidents.

Ofgem's sector overlay is kept separately because it adds energy-sector context.

### Ofgem Objective E

**Project status: `CONDITIONAL`**

The downstream gas and electricity overlay extends the assurance view into physical security and broader resilience concerns.

The simulation cannot prove physical security effectiveness. Physical and environmental dependencies are therefore assessed analytically and clearly marked as not physically tested.

### Cyber Security and Resilience Bill

**Project status: `CHANGE_WATCH_ONLY`**

As of 8 September 2026 this remains proposed legislation and is not treated as current law.

It is deliberately excluded from current-law control conclusions.

## European Union

### NIS2

**Project status: `CONDITIONAL`**

Energy appears in Annex I as a sector of high criticality, but scope still depends on the type of entity, size and other Article 2 criteria, together with national implementation.

Article 20 is relevant to governance.

Article 21 requires appropriate and proportionate technical, operational and organisational cybersecurity risk-management measures and uses an all-hazards approach. Relevant themes include:

- risk analysis;
- incident handling;
- business continuity and recovery;
- supply-chain security;
- acquisition, development and maintenance;
- effectiveness assessment;
- access control and asset management.

The project maps to these themes without claiming that the fictional operator has been legally classified.

### Critical Entities Resilience Directive

**Project status: `CONDITIONAL`**

CER is used where the hypothetical operator is assumed to have been identified as a critical entity by a Member State.

Its value to this project is broader than cyber security. Article 13 includes prevention, physical protection, response, mitigation and recovery measures.

### Electricity cybersecurity network code — Regulation 2024/1366

**Project status: `NARROW_CONDITIONAL`**

This Regulation is not used as a generic energy-cybersecurity checklist.

Its scope concerns cybersecurity aspects of cross-border electricity flows and applies to defined entities when identified as high-impact or critical-impact.

Where that condition is assumed, the project uses:

- entity-level cybersecurity risk management under Article 26;
- minimum and advanced cybersecurity control context under Article 29;
- supply-chain control context under Article 33.

### Data Act

**Project status: `CONDITIONAL`**

The Data Act is not used simply because the system produces telemetry.

A later data-governance assessment will first identify whether the reference scenario actually creates the relevant connected-product, related-service, user and data-holder roles.

### AI Act

**Project status: `DORMANT_CONDITIONAL`**

The initial system does not require AI.

No AI control is claimed to be implemented.

The AI Act profile is activated only if a later controller or optimisation component creates a legally relevant AI-system use case.

## Mapping rule

A control-to-regulation mapping means that the source explains why the assurance objective is relevant.

It does not mean:

`control test passed = legal compliance proven`

That shortcut is not used anywhere in this repository.

The machine-readable source register is held in `data/regulatory-register.json`.
