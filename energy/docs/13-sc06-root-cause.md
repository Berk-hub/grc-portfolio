# SC-06 Root Cause: Resend Scheduling, Not Data Loss

## Question

Why did `LastSuccessfulResend` remain null and central backfill stay unverified in the v1.0 evidence set?

## Mechanism (from pinned source 189ac916)

The resend path lives in `io.openems.edge.controller.api.backend.ResendHistoricDataWorker`:

1. On reconnection, `OnOpen` calls `resendHistoricDataWorker.triggerNextRun()`.
2. The first `forever()` execution after the trigger is intentionally skipped (`AFTER_TRIGGER -> SKIP_FIRST_FOREVER`).
3. `getCycleTime()` then schedules the real run at `DELAY_TRIGGER_TIME + Random().nextInt(MAX_RANDOM_DELAY)` — with `DELAY_TRIGGER_TIME = 300_000 ms` and `MAX_RANDOM_DELAY = 3_600_000 ms`.

Resending therefore starts between **5 and 65 minutes after reconnection**, uniformly at random. The randomisation is a sensible upstream design: it prevents a fleet of Edges reconnecting after a Backend outage from resending simultaneously.

Once running, the worker reads gap timeranges from timedata (`getResendTimeranges` over the last-successful-send channel, with a 300 s buffer), queries at most 5-minute spans (`MAX_RESEND_TIMESPAN_SECONDS`) via `queryResendData`, and only updates `LastSuccessfulResend` after a successful send.

## Applied to the v1.0 timeline

| Event | Time (UTC) |
|---|---|
| Reconnection | 2026-09-08 21:39:26 |
| Evidence freeze | 2026-09-08 22:28:14 |
| Observation window | 48.8 minutes |
| Worst-case scheduled resend | reconnection + 65 minutes |

The observation window covered roughly 73% of the possible delay range. A delay draw in the remaining tail fully explains a null `LastSuccessfulResend` at freeze time without any data having been lost. Local RRD4J history was intact throughout, so the samples needed for backfill still existed locally.

## Secondary preconditions worth noting

- Only channels whose `remotePersistencePriority` is at least the configured `resendPriority` (HIGH in the lab) are resent.
- Gap detection depends on last-successful-send timestamps persisted in RRD4J. The lab's `rrd4j0` component was enabled at 21:26, thirteen minutes before the final run — sends before that point are invisible to gap detection.

## Consequence for the assurance result

SC-06 stays INCONCLUSIVE: the root cause explains the missing evidence but does not substitute for it. The retest protocol (EXP-02) now has a hard requirement the v1.0 run lacked: **observe for at least 66 minutes after reconnection**, monitor `LastSuccessfulResend` until it becomes non-null, then capture the central query as `evidence/backend-loss/14-influx-post-resend.txt` with distinctive marker values chosen to avoid substring collisions.

This conclusion applies to the pinned revision and laboratory configuration; it is not a statement about other OpenEMS versions or deployments.
