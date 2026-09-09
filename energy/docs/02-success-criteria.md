# Success Criteria

## Claim under test

> During a temporary loss of central Backend connectivity, the defined local energy-control function continues in a controlled manner and leaves sufficient evidence to understand the interruption and subsequent recovery.

The Edge process remaining alive is not, by itself, evidence of resilience.

## Required observations

A `SUPPORTED` conclusion requires all six conditions below.

### SC-01 — Local measurements remain available
The Edge retains the measurements required by the selected local control function.

### SC-02 — Local control continues
The relevant local control output or set-point remains observable during Backend unavailability.

### SC-03 — No unexplained control transition occurs
Loss of Backend connectivity does not produce an unexplained control-state change.

### SC-04 — The interruption is observable
The evidence identifies when central connectivity was lost and restored.

### SC-05 — Evidence remains time-orderable
Measurements, control outputs and connectivity events can be placed into a reliable sequence.

### SC-06 — Recovery is understandable
The state after reconnection can be compared with the state before and during the interruption, including any telemetry gap.

## Conclusion rules

- `SUPPORTED` — all required observations are evidenced and no material failure indicator is present.
- `NOT SUPPORTED` — collected evidence demonstrates that one or more required conditions failed.
- `INCONCLUSIVE` — the evidence is insufficient to distinguish correct behaviour from failure.
- `NOT TESTED` — the scenario has not yet been executed.

The conclusion applies only to the recorded OpenEMS revision, configuration and test scenario. It does not demonstrate regulatory compliance or production resilience.
