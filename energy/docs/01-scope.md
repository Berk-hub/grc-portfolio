# Project Scope

## Purpose

This project examines the operational resilience of a small cyber-physical energy-management environment built around OpenEMS.

The aim is not to assess OpenEMS for regulatory compliance or to perform a vulnerability assessment of the upstream project.

Instead, the project asks whether a defined energy-management function can continue in a controlled and observable state when one of its central dependencies becomes unavailable.

## Reference system

The reference environment represents a fictional commercial energy site with:

- solar PV generation;
- a battery energy storage system;
- a grid connection and grid meter;
- OpenEMS Edge for local measurement and control;
- OpenEMS Backend for central visibility and management;
- an operator using the central interface.

The physical assets will be represented through OpenEMS simulation components rather than real hardware.

## Function under assurance

The primary function is:

**Local energy control during temporary loss of central connectivity.**

For this project, local control means that OpenEMS Edge continues to observe the simulated site and execute the defined local control behaviour even when the connection to the central Backend is unavailable.

## Primary failure scenario

The first controlled scenario is:

**Loss of connectivity between OpenEMS Edge and OpenEMS Backend.**

The test will observe the system before, during and after the interruption.

The project will collect evidence about:

- local control behaviour;
- relevant energy measurements;
- control set-points;
- loss of central visibility;
- timestamps and event records;
- behaviour after connectivity is restored;
- any telemetry or state that cannot be reconciled after recovery.

## Primary assurance claim

The initial claim is:

> During a temporary loss of central Backend connectivity, the defined local energy-control function continues in a controlled manner and leaves sufficient evidence to understand the interruption and subsequent recovery.

This is a testable claim, not a conclusion.

The project will only mark the claim as supported if the collected evidence justifies that result.

## Result states

Each tested claim can end in one of four states:

- `SUPPORTED` — the observed evidence supports the claim within the stated test scope;
- `NOT SUPPORTED` — the observed behaviour contradicts the claim or a required condition fails;
- `INCONCLUSIVE` — the evidence is insufficient to reach a reliable conclusion;
- `NOT TESTED` — the scenario has not yet been executed.

## Out of scope

This project does not claim:

- that OpenEMS is compliant or non-compliant with any law, regulation or standard;
- that a simulated environment represents the resilience of a production energy operator;
- that an upstream design choice is a security vulnerability;
- that every UK or EU energy regulation applies to the fictional reference operator;
- that technical availability alone proves operational resilience.

Regulatory applicability will be assessed separately from technical test results.
