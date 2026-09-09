# TTX-01: Incident-Notification Tabletop

Desk-based walkthrough of the recorded backend-loss event against the notification expectations in the obligations register. Performed by the project author; independence is SELF_REVIEW. No real notification was made and none was required — the laboratory is not a regulated entity.

## Scenario walked through

The recorded run of 2026-09-08: Edge-to-Backend communication lost at 21:38:53 UTC, restored at 21:39:26 UTC (33 seconds), local control unaffected, central historical backfill unverified at freeze time (FND-REC-001).

## Trigger analysis

| Question | Assessment for the reference profiles |
|---|---|
| Is there a service impact? | Local energy control continued; the impact was loss of central visibility and unverified telemetry backfill. |
| NIS2 Art. 23 "significant incident"? | On the recorded facts, a 33-second monitoring-path interruption with no service disruption would not obviously meet the significance threshold. This cannot be concluded firmly: thresholds are set in national implementation and the member state is unselected (UNDETERMINED facts in OBL-NIS2-ART23). |
| GB NIS incident reporting? | Same structure: an OES would assess against competent-authority thresholds. The recorded event would plausibly be handled as an internal event record rather than a notification, subject to the unresolved telemetry-gap question. |
| What would change the answer? | A longer outage, evidence of lost (not merely unverified) telemetry, recurrence, or any effect on the control function itself. |

## Decision log

1. Event classified as an internal operational event for both reference profiles; no notification triggered on the recorded facts.
2. The unverified backfill (FND-REC-001) is the deciding uncertainty: if EXP-02 showed permanent telemetry loss, the classification would be reassessed.
3. Timer discipline noted: under NIS2 the 24-hour early-warning clock starts at awareness of a significant incident, so the classification decision itself must be logged with a timestamp — this tabletop records that practice.

## Unknowns identified

- National significance thresholds (member state unselected).
- Real competent-authority reporting channels and formats.
- Whether a production monitoring gap of this shape would be detected promptly without the laboratory's instrumentation.

## Outcome

GAP-INCIDENT-TTX closure criteria are met: trigger analysis, scope decision and unknowns are recorded. The exercise does not demonstrate real incident-response capability and is not evidence of operating effectiveness for any control.
