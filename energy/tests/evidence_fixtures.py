"""Helpers that build synthetic evidence trees for the evaluator tests.

Not a test module (no test_ prefix). The synthetic run is derived from the
recorded 11-final-reconciliation-run.json so that phase snapshots, link
states and timestamps match real evidence; only the state trace is invented.
"""
import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from energy_assurance.cli import load_backend_loss_run

ROOT = Path(__file__).resolve().parents[1]

# Steady operating points used by the recorded run (consumption, production).
BASELINE = (4100, 1100)
DISCHARGE = (5200, 700)
CHARGE = (1800, 4300)


def recorded_run():
    _, run = load_backend_loss_run(ROOT)
    return copy.deepcopy(run)


def sample(moment, consumption, production, ess=None, grid=0, soc=28, **extra):
    """One trace sample. By default the ESS covers consumption - production."""
    if ess is None:
        ess = consumption - production - grid
    record = {
        "captured_at_utc": moment.isoformat(),
        "consumption_w": consumption,
        "production_w": production,
        "ess_w": ess,
        "grid_w": grid,
        "ess_soc_pct": soc,
    }
    record.update(extra)
    return record


def consistent_trace(run, step_s=1.0, setpoint=None):
    """A 1 Hz trace over the recorded outage window with explained transitions."""
    start = datetime.fromisoformat(run["failure_injected_at_utc"])
    end = datetime.fromisoformat(run["reconnected_at_utc"])
    samples = []
    moment = start + timedelta(seconds=1)
    index = 0
    while moment < end:
        if index < 10:
            point = BASELINE
        elif index < 20:
            point = DISCHARGE
        else:
            point = CHARGE
        extra = {} if setpoint is None else {"grid_setpoint_w": setpoint}
        samples.append(sample(moment, *point, **extra))
        moment += timedelta(seconds=step_s)
        index += 1
    return samples


def v2_run(trace=None, **overrides):
    run = recorded_run()
    run["evidence_format"] = 2
    run["state_trace"] = consistent_trace(run) if trace is None else trace
    run.update(overrides)
    return run


def write_evidence(root: Path, run, trace_lines=None, name="11-final-reconciliation-run.json"):
    """Write a run (and optionally a JSONL trace file) under root/evidence/backend-loss."""
    evidence = root / "evidence/backend-loss"
    evidence.mkdir(parents=True, exist_ok=True)
    if trace_lines is not None:
        (evidence / "state-trace.jsonl").write_text(
            "\n".join(trace_lines) + "\n", encoding="utf-8"
        )
    (evidence / name).write_text(json.dumps(run, indent=1), encoding="utf-8")
    return evidence


def utc(seconds, base="2026-09-08T21:39:00+00:00"):
    return datetime.fromisoformat(base).astimezone(timezone.utc) + timedelta(seconds=seconds)
