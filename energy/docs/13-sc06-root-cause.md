# SC-06 Investigation: Resend Scheduling and an Unconfirmed Cause

## Question

Why did `LastSuccessfulResend` remain null and central backfill stay unverified in the v1.0 evidence set?

## Mechanism (from pinned source 189ac916)

The resend path lives in `io.openems.edge.controller.api.backend.ResendHistoricDataWorker`:

1. On reconnection, `OnOpen` calls `resendHistoricDataWorker.triggerNextRun()`.
2. The first `forever()` execution after the trigger is intentionally skipped (`AFTER_TRIGGER -> SKIP_FIRST_FOREVER`).
3. `getCycleTime()` then schedules the real run at `DELAY_TRIGGER_TIME + Random().nextInt(MAX_RANDOM_DELAY)` — with `DELAY_TRIGGER_TIME = 300_000 ms` and `MAX_RANDOM_DELAY = 3_600_000 ms`.

The nominal scheduling delay is therefore **5 to just under 65 minutes**, with a uniformly distributed random component. This describes scheduling, not a guaranteed transfer start or completion time. The randomisation is a sensible upstream design: it prevents a fleet of Edges reconnecting after a Backend outage from resending simultaneously.

Once running, the worker reads gap timeranges from timedata (`getResendTimeranges` over the last-successful-send channel, with a 300 s buffer), queries at most 5-minute spans (`MAX_RESEND_TIMESPAN_SECONDS`) via `queryResendData`, and only updates `LastSuccessfulResend` after a successful send.

## Applied to the v1.0 timeline

| Event | Time (UTC) |
|---|---|
| Reconnection | 2026-09-08 21:39:26 |
| Evidence freeze | 2026-09-08 22:28:14 |
| Observation window | 48.8 minutes |
| Worst-case scheduled resend | reconnection + 65 minutes |

The observation window covered roughly 73% of the possible delay range. A delay draw in the remaining tail could explain a null `LastSuccessfulResend` at freeze time without data loss. The actual delay selected in this run was not captured, so this is a plausible explanation, not a confirmed root cause. Local RRD4J history was intact throughout, so the samples needed for backfill still existed locally.

## Secondary preconditions worth noting

- Only channels whose `remotePersistencePriority` is at least the configured `resendPriority` (HIGH in the lab) are resent.
- Gap detection depends on last-successful-send timestamps persisted in RRD4J. The lab's `rrd4j0` component was enabled at 21:26, thirteen minutes before the final run — sends before that point are invisible to gap detection.

## Consequence for the assurance result

SC-06 stays INCONCLUSIVE: the source identifies a possible explanation but does not establish the cause of this run's missing evidence. The retest protocol (EXP-02) now has a hard requirement the v1.0 run lacked: **observe for at least 66 minutes after reconnection**, monitor `LastSuccessfulResend` until it becomes non-null, then capture the central query as `evidence/backend-loss/14-influx-post-resend.txt` with distinctive marker values and structured field matching. The 66-minute minimum covers the nominal scheduling delay; it does not guarantee completion. Record a separate transfer timeout and retain an INCONCLUSIVE result if successful reconciliation is not verified.

This conclusion applies to the pinned revision and laboratory configuration; it is not a statement about other OpenEMS versions or deployments.
