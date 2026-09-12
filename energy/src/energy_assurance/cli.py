from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime
from pathlib import Path


ALLOWED_RESULTS = {
    "SUPPORTED",
    "NOT SUPPORTED",
    "INCONCLUSIVE",
    "NOT TESTED",
}


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def records(document, key):
    if isinstance(document, list):
        return document

    if isinstance(document, dict):
        value = document.get(key, [])
        if isinstance(value, list):
            return value

    return []


def identifier(record):
    if not isinstance(record, dict):
        return None

    return (
        record.get("id")
        or record.get("control_id")
        or record.get("risk_id")
        or record.get("source_id")
        or record.get("asset_id")
    )


def rating_for_score(score):
    if 1 <= score <= 4:
        return "LOW"
    if 5 <= score <= 9:
        return "MEDIUM"
    if 10 <= score <= 16:
        return "HIGH"
    if 17 <= score <= 25:
        return "CRITICAL"
    return None


def duplicate_ids(items):
    seen = set()
    duplicates = set()

    for item in items:
        item_id = identifier(item)
        if not item_id:
            continue

        if item_id in seen:
            duplicates.add(item_id)

        seen.add(item_id)

    return sorted(duplicates)


def extract_refs(value):
    result = []

    if isinstance(value, str):
        result.append(value)

    elif isinstance(value, list):
        for item in value:
            result.extend(extract_refs(item))

    elif isinstance(value, dict):
        for key in (
            "id",
            "risk_id",
            "source_id",
            "asset_id",
            "control_id",
            "source",
            "risk",
        ):
            candidate = value.get(key)
            if isinstance(candidate, str):
                result.append(candidate)

    return result


def validate_repository(root: Path):
    errors = []
    warnings = []

    paths = {
        "assets": root / "data/assets.json",
        "risks": root / "data/risks.json",
        "sources": root / "data/regulatory-register.json",
        "controls": root / "data/controls.json",
        "scenario": root / "config/scenario-backend-loss.json",
    }

    documents = {}

    for name, path in paths.items():
        if not path.exists():
            errors.append(f"Missing required file: {path}")
            continue

        try:
            documents[name] = load_json(path)
        except Exception as exc:
            errors.append(f"Invalid JSON in {path}: {exc}")

    if errors:
        return {
            "status": "INVALID",
            "errors": errors,
            "warnings": warnings,
        }

    assets = records(documents["assets"], "assets")
    risks = records(documents["risks"], "risks")
    sources = records(documents["sources"], "sources")
    controls = records(documents["controls"], "controls")

    collections = {
        "asset": assets,
        "risk": risks,
        "regulatory source": sources,
        "control": controls,
    }

    for label, items in collections.items():
        duplicates = duplicate_ids(items)

        for item_id in duplicates:
            errors.append(f"Duplicate {label} ID: {item_id}")

    asset_ids = {
        identifier(item)
        for item in assets
        if identifier(item)
    }

    risk_ids = {
        identifier(item)
        for item in risks
        if identifier(item)
    }

    source_ids = {
        identifier(item)
        for item in sources
        if identifier(item)
    }

    for risk in risks:
        risk_id = identifier(risk) or "<unknown>"

        likelihood = risk.get("likelihood")
        impact = risk.get("impact")
        score = risk.get("score", risk.get("inherent_score"))

        if all(
            isinstance(value, int)
            for value in (likelihood, impact, score)
        ):
            expected = likelihood * impact

            if score != expected:
                errors.append(
                    f"{risk_id}: score={score}, expected={expected}"
                )

            rating = (
                risk.get("rating")
                or risk.get("risk_rating")
                or risk.get("level")
            )

            expected_rating = rating_for_score(score)

            if (
                rating is not None
                and expected_rating is not None
                and str(rating).upper() != expected_rating
            ):
                errors.append(
                    f"{risk_id}: rating={rating}, "
                    f"expected={expected_rating}"
                )
        else:
            warnings.append(
                f"{risk_id}: likelihood/impact/score "
                "could not all be validated as integers"
            )

    for control in controls:
        control_id = identifier(control) or "<unknown>"

        risk_refs = []

        for key in (
            "risk_ids",
            "risk_refs",
            "risks",
        ):
            risk_refs.extend(
                extract_refs(control.get(key))
            )

        for ref in risk_refs:
            if ref.startswith("R-") and ref not in risk_ids:
                errors.append(
                    f"{control_id}: unknown risk reference {ref}"
                )

        source_refs = []

        for key in (
            "source_ids",
            "source_refs",
            "source_mappings",
        ):
            source_refs.extend(
                extract_refs(control.get(key))
            )

        for ref in source_refs:
            if (
                (
                    ref.startswith("GB-")
                    or ref.startswith("EU-")
                    or ref.startswith("GLOBAL-")
                )
                and ref not in source_ids
            ):
                errors.append(
                    f"{control_id}: unknown regulatory source {ref}"
                )

        conclusion = control.get("conclusion")

        if (
            conclusion is not None
            and conclusion not in ALLOWED_RESULTS
        ):
            errors.append(
                f"{control_id}: invalid conclusion {conclusion}"
            )

    dependencies = records(
        documents["assets"],
        "dependencies",
    )

    if not dependencies:
        dependencies = records(
            documents["assets"],
            "critical_dependencies",
        )

    for dependency in dependencies:
        dep_id = identifier(dependency) or "<dependency>"

        for key in (
            "source_asset_id",
            "target_asset_id",
            "from_asset_id",
            "to_asset_id",
            "source",
            "target",
            "from",
            "to",
        ):
            ref = dependency.get(key)

            if (
                isinstance(ref, str)
                and ref.startswith("A-")
                and ref not in asset_ids
            ):
                errors.append(
                    f"{dep_id}: unknown asset reference {ref}"
                )

    scenario = documents["scenario"]

    current_result = scenario.get("current_result")

    if (
        current_result is not None
        and current_result not in ALLOWED_RESULTS
    ):
        errors.append(
            f"Scenario has invalid current_result: {current_result}"
        )

    return {
        "status": "VALID" if not errors else "INVALID",
        "counts": {
            "assets": len(assets),
            "risks": len(risks),
            "regulatory_sources": len(sources),
            "controls": len(controls),
            "dependencies": len(dependencies),
        },
        "errors": errors,
        "warnings": warnings,
    }



# ---------------------------------------------------------------------------
# Measurement dictionary: the single source of limits, tolerances and time rules
# ---------------------------------------------------------------------------

DICTIONARY_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "measurement-dictionary.json"
)

_DICTIONARY_CACHE = None


class EvidenceError(Exception):
    """Evidence could not be evaluated (schema, format or integrity problem).

    Raised instead of producing a criterion result so that malformed evidence
    can never be reported as SUPPORTED, NOT SUPPORTED or INCONCLUSIVE.
    """


def measurement_dictionary():
    """Load data/measurement-dictionary.json once and cache it."""
    global _DICTIONARY_CACHE
    if _DICTIONARY_CACHE is None:
        _DICTIONARY_CACHE = load_json(DICTIONARY_PATH)
    return _DICTIONARY_CACHE


def channel_limits():
    """Map snapshot field name -> channel entry (unit, min, max, finite, ...)."""
    return {
        channel["field"]: channel
        for channel in measurement_dictionary()["channels"]
        if "field" in channel
    }


def required_fields():
    return tuple(channel_limits())


def balance_tolerance_w():
    return measurement_dictionary()["balance_tolerance_w"]


def validation_rules():
    return measurement_dictionary()["validation"]


def operating_limits():
    return measurement_dictionary()["operating_limits"]


def time_rules():
    return measurement_dictionary()["time_semantics"]


# ---------------------------------------------------------------------------
# Time handling
# ---------------------------------------------------------------------------

def parse_timestamp(raw):
    """Return an aware datetime, or None if raw is not an aware ISO-8601 string."""
    if not isinstance(raw, str):
        return None
    try:
        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if value.utcoffset() is None:
        return None
    return value


def ordered_timestamps(snapshots):
    values = []
    for snapshot in snapshots:
        value = parse_timestamp(snapshot.get("captured_at_utc"))
        if value is None:
            return False
        values.append(value)
    return len(values) >= 2 and all(
        earlier < later for earlier, later in zip(values, values[1:])
    )


def record_time(record):
    """Ordering time of a record: source_timestamp if present, else captured_at_utc.

    Format 1 snapshots only carry captured_at_utc. No time is invented when a
    field is absent; the caller decides whether that is acceptable.
    """
    if "source_timestamp" in record:
        return parse_timestamp(record.get("source_timestamp"))
    return parse_timestamp(record.get("captured_at_utc"))


def freshness_error(record):
    """Return a reason string when a record violates the dictionary freshness rule.

    The rule applies only when both source_timestamp and captured_at_utc are
    present. Clock uncertainty comes from the dictionary; null means 0 s.
    """
    if "source_timestamp" not in record or "captured_at_utc" not in record:
        return None
    source = parse_timestamp(record.get("source_timestamp"))
    captured = parse_timestamp(record.get("captured_at_utc"))
    if source is None or captured is None:
        return "source_timestamp and captured_at_utc must be aware ISO-8601 strings"
    uncertainty = time_rules().get("clock_uncertainty_s") or 0
    age_s = (captured - source).total_seconds()
    if age_s < -uncertainty:
        return (
            f"source_timestamp is {-age_s:.3f} s later than captured_at_utc "
            f"(clock uncertainty {uncertainty} s)"
        )
    stale_after_s = min(
        channel["stale_after_s"] for channel in channel_limits().values()
    )
    if age_s > stale_after_s + uncertainty:
        return f"sample was {age_s:.3f} s old at capture; stale after {stale_after_s} s"
    return None


# ---------------------------------------------------------------------------
# Measurement validation
# ---------------------------------------------------------------------------

def finite_number(value):
    # bool is an int subclass, but is not a power or SOC measurement.
    return type(value) in (int, float) and (
        not isinstance(value, float) or math.isfinite(value)
    )


def measurement_problems(snapshot):
    """List the dictionary limits a snapshot violates (empty list = valid)."""
    problems = []
    if not isinstance(snapshot, dict):
        return ["record is not an object"]
    for field, channel in channel_limits().items():
        value = snapshot.get(field)
        if channel.get("finite", True) and not finite_number(value):
            problems.append(f"{field} is not a finite number: {value!r}")
            continue
        low = channel.get("min")
        high = channel.get("max")
        if low is not None and value < low:
            problems.append(f"{field}={value} below documented minimum {low}")
        if high is not None and value > high:
            problems.append(f"{field}={value} above documented maximum {high}")
    return problems


def required_measurements(snapshot):
    return not measurement_problems(snapshot)


def residual_w(snapshot):
    """production + ess + grid - consumption (dictionary sign convention)."""
    return (
        snapshot["production_w"] + snapshot["ess_w"]
        + snapshot["grid_w"] - snapshot["consumption_w"]
    )


def balanced(snapshot, tolerance=None):
    if tolerance is None:
        tolerance = balance_tolerance_w()
    if not required_measurements(snapshot):
        return False
    if not finite_number(tolerance) or tolerance < 0:
        return False
    # Grid import and ESS discharge supply the load. Do not trust the stored
    # residual: it can stay zero even when an input channel has been altered.
    return (
        abs(snapshot["grid_w"]) <= tolerance
        and abs(residual_w(snapshot)) <= tolerance
    )


def explained_by_limit(sample):
    """True when a non-zero grid exchange is explained by an ESS operating limit.

    At the SOC floor the ESS cannot discharge, at the ceiling it cannot charge,
    and at rated power it cannot follow a larger step. In those states the
    grid takes the difference; the dictionary records this as correct
    behaviour. The sample must still satisfy power balance.
    """
    if not required_measurements(sample):
        return False
    tolerance = balance_tolerance_w()
    if abs(residual_w(sample)) > tolerance:
        return False
    limits = operating_limits()
    soc = sample["ess_soc_pct"]
    ess = sample["ess_w"]
    at_floor = soc <= limits["soc_floor_pct"] and ess <= tolerance
    at_ceiling = soc >= limits["soc_ceiling_pct"] and ess >= -tolerance
    at_discharge_limit = ess >= limits["ess_max_discharge_w"] - tolerance
    at_charge_limit = ess <= -(limits["ess_max_charge_w"] - tolerance)
    return at_floor or at_ceiling or at_discharge_limit or at_charge_limit


# ---------------------------------------------------------------------------
# Evidence loading and schema validation
# ---------------------------------------------------------------------------

def _reject_constant(name):
    raise ValueError(f"non-finite JSON constant {name} is not allowed")


def load_strict_json(path: Path):
    """Parse JSON, rejecting NaN/Infinity, and raise EvidenceError on failure."""
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle, parse_constant=_reject_constant)
    except (ValueError, OSError) as exc:
        raise EvidenceError(f"{path.name}: {exc}") from exc


def load_jsonl(path: Path):
    """Parse a JSONL file into a list of objects; any broken line is an error."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise EvidenceError(f"{path.name}: {exc}") from exc
    records_out = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            raise EvidenceError(f"{path.name} line {number}: empty line")
        try:
            record = json.loads(line, parse_constant=_reject_constant)
        except ValueError as exc:
            raise EvidenceError(f"{path.name} line {number}: {exc}") from exc
        if not isinstance(record, dict):
            raise EvidenceError(f"{path.name} line {number}: not a JSON object")
        records_out.append(record)
    return records_out


def latest_resend_value(path: Path):
    if not path.exists():
        return None

    latest = None

    for line in path.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue

        value = record.get("last_successful_resend")

        if value is not None:
            latest = value

    return latest


def reconciliation_evidence(root: Path):
    monitor = (
        root
        / "evidence/backend-loss/"
        "13-historic-resend-monitor.jsonl"
    )

    post_resend = (
        root
        / "evidence/backend-loss/"
        "14-influx-post-resend.txt"
    )

    resend_value = latest_resend_value(monitor)

    if resend_value is None or not post_resend.exists():
        return {
            "status": "INCONCLUSIVE",
            "last_successful_resend": resend_value,
            "central_backfill_verified": False,
            "reason": "No structured post-resend sample comparison is available.",
        }

    # Legacy query text has no validated run, channel or sample-window binding.
    # Marker presence (even exact numbers) cannot establish complete backfill.
    # Keep this gate closed until EXP-02 supplies structured local/central samples
    # and a comparator checks missing, duplicate and out-of-order observations.
    return {
        "status": "INCONCLUSIVE",
        "last_successful_resend": resend_value,
        "central_backfill_verified": False,
        "reason": "Unstructured query text cannot establish historical reconciliation; "
        "structured sample comparison is required.",
    }


def load_backend_loss_run(root: Path):
    final_run = (
        root
        / "evidence/backend-loss/"
        "11-final-reconciliation-run.json"
    )

    earlier_run = (
        root
        / "evidence/backend-loss/"
        "02-backend-loss-run.json"
    )

    if final_run.exists():
        return final_run, load_strict_json(final_run)

    if earlier_run.exists():
        return earlier_run, load_strict_json(earlier_run)

    raise EvidenceError("No backend-loss evidence run found")


PHASE_NAMES = ("pre_failure", "outage_discharge", "outage_charge", "recovery")


def normalize_phases(run):
    if not isinstance(run, dict):
        raise EvidenceError("evidence run must be a JSON object")

    source = run.get("phases", run)
    if not isinstance(source, dict):
        raise EvidenceError("phases must be a JSON object")

    phases = {}
    for name in PHASE_NAMES:
        phase = source.get(name)
        if not isinstance(phase, dict):
            raise EvidenceError(f"phase {name} is missing or not an object")
        for field in required_fields():
            if field not in phase:
                raise EvidenceError(f"phase {name} is missing field {field}")
            if not finite_number(phase[field]):
                raise EvidenceError(
                    f"phase {name}: {field} is not a finite number: {phase[field]!r}"
                )
        phases[name] = phase

    return {
        "pre": phases["pre_failure"],
        "discharge": phases["outage_discharge"],
        "charge": phases["outage_charge"],
        "recovery": phases["recovery"],
    }


def evidence_format(run):
    """1 = four snapshots only; 2 = snapshots plus a continuous state trace."""
    declared = run.get("evidence_format")
    if declared is None:
        return 2 if ("state_trace" in run or "state_trace_file" in run) else 1
    if declared in (1, 2):
        return declared
    raise EvidenceError(f"unknown evidence_format {declared!r}")


def load_state_trace(evidence_path: Path, run):
    """Return the raw sample list from an inline trace or a sibling JSONL file."""
    if "state_trace" in run and "state_trace_file" in run:
        raise EvidenceError("state_trace and state_trace_file are both present")
    if "state_trace" in run:
        return run["state_trace"]
    if "state_trace_file" in run:
        name = run["state_trace_file"]
        if not isinstance(name, str) or not name:
            raise EvidenceError("state_trace_file must be a file name")
        directory = evidence_path.parent.resolve()
        path = (directory / name).resolve()
        if path.parent != directory:
            raise EvidenceError("state_trace_file must sit next to the run file")
        if not path.is_file():
            raise EvidenceError(f"state_trace_file not found: {name}")
        return load_jsonl(path)
    raise EvidenceError("evidence_format 2 requires state_trace or state_trace_file")


def validate_state_trace(samples):
    """Schema-check a state trace; return [(time, monotonic_s, sample), ...].

    Errors: not a list, fewer than two samples, non-object sample, missing
    channel field, non-finite or boolean value, missing or naive time,
    duplicate sample time, non-increasing time or monotonic counter, and
    freshness violations where both timestamps are present.
    """
    if not isinstance(samples, list):
        raise EvidenceError("state_trace must be a list of sample objects")
    if len(samples) < 2:
        raise EvidenceError("state_trace must contain at least two samples")

    parsed = []
    seen_times = set()
    uses_monotonic = None

    for index, sample in enumerate(samples):
        label = f"state_trace[{index}]"
        if not isinstance(sample, dict):
            raise EvidenceError(f"{label} is not an object")
        for field in required_fields():
            if field not in sample:
                raise EvidenceError(f"{label} is missing field {field}")
            if not finite_number(sample[field]):
                raise EvidenceError(
                    f"{label}: {field} is not a finite number: {sample[field]!r}"
                )
        if "grid_setpoint_w" in sample and not finite_number(sample["grid_setpoint_w"]):
            raise EvidenceError(f"{label}: grid_setpoint_w is not a finite number")

        moment = record_time(sample)
        if moment is None:
            raise EvidenceError(
                f"{label} has no aware ISO-8601 source_timestamp or captured_at_utc"
            )

        monotonic = sample.get("monotonic_s")
        has_monotonic = monotonic is not None
        if uses_monotonic is None:
            uses_monotonic = has_monotonic
        elif uses_monotonic != has_monotonic:
            raise EvidenceError("monotonic_s is present on only some samples")
        if has_monotonic and not finite_number(monotonic):
            raise EvidenceError(f"{label}: monotonic_s is not a finite number")

        if moment in seen_times:
            raise EvidenceError(f"{label}: duplicate sample time {moment.isoformat()}")
        seen_times.add(moment)
        if parsed:
            previous_time, previous_monotonic, _ = parsed[-1]
            if moment <= previous_time:
                raise EvidenceError(
                    f"{label}: time {moment.isoformat()} is not after the previous sample"
                )
            if has_monotonic and monotonic <= previous_monotonic:
                raise EvidenceError(f"{label}: monotonic_s did not increase")

        stale = freshness_error(sample)
        if stale:
            raise EvidenceError(f"{label}: {stale}")

        parsed.append((moment, monotonic, sample))

    return parsed


# ---------------------------------------------------------------------------
# Scenario assessment
# ---------------------------------------------------------------------------

def link_value(snapshot):
    if "backend_link_18081" in snapshot:
        return snapshot["backend_link_18081"]

    return snapshot.get(
        "backend_link_18081_established"
    )


def central_value(snapshot):
    if "central_backend_8083" in snapshot:
        return snapshot["central_backend_8083"]

    return snapshot.get(
        "central_backend_8083_established"
    )


def outage_window(run, parsed):
    """Select trace samples that belong to the outage.

    Preference: the run's failure_injected_at_utc / reconnected_at_utc window;
    otherwise samples whose backend_link_18081 is False; otherwise all samples.
    """
    start = parse_timestamp(run.get("failure_injected_at_utc"))
    end = parse_timestamp(run.get("reconnected_at_utc"))
    if start is not None and end is not None:
        return [item for item in parsed if start <= item[0] <= end], "run outage window"
    if all("backend_link_18081" in item[2] for item in parsed):
        return [item for item in parsed if item[2]["backend_link_18081"] is False], "backend_link_18081 false"
    return list(parsed), "whole trace"


def evaluate_state_trace(run, samples):
    """SC-03 over a continuous trace.

    SUPPORTED: every adjacent change in ess_w is explained by the adjacent
    change in (consumption - production) within transition_tolerance_w, or by
    an ESS operating limit; every sample balances and reaches its set-point
    (or is limit-explained); no sampling gap exceeds max_gap_s.
    NOT SUPPORTED: an unexplained transition, residual or set-point miss.
    INCONCLUSIVE: too few samples in the outage window, or a gap that could
    hide a transition.
    """
    parsed = validate_state_trace(samples)
    selected, selection = outage_window(run, parsed)
    rules = validation_rules()
    tolerance = balance_tolerance_w()
    transition_tolerance = rules["transition_tolerance_w"]
    max_gap_s = rules["max_gap_s"]

    details = {
        "samples_total": len(parsed),
        "samples_in_window": len(selected),
        "window_selection": selection,
        "limit_explained_transitions": 0,
        "gaps": [],
        "problems": [],
    }

    if len(selected) < 2:
        return (
            "INCONCLUSIVE",
            "fewer than two state-trace samples fall inside the outage window",
            details,
        )

    problems = details["problems"]

    for moment, _, sample in selected:
        stamp = moment.isoformat()
        for problem in measurement_problems(sample):
            problems.append(f"{stamp}: {problem}")
        if measurement_problems(sample):
            continue
        if abs(residual_w(sample)) > tolerance:
            problems.append(
                f"{stamp}: power balance residual {residual_w(sample):+} W exceeds {tolerance} W"
            )
        setpoint = sample.get("grid_setpoint_w")
        if setpoint is not None and abs(sample["grid_w"] - setpoint) > tolerance:
            if explained_by_limit(sample):
                details["limit_explained_transitions"] += 1
            else:
                problems.append(
                    f"{stamp}: grid_w {sample['grid_w']:+} W missed set-point {setpoint:+} W"
                )

    for (t0, m0, a), (t1, m1, b) in zip(selected, selected[1:]):
        gap_s = (m1 - m0) if m0 is not None else (t1 - t0).total_seconds()
        if gap_s > max_gap_s:
            details["gaps"].append(f"{t1.isoformat()}: gap of {gap_s:.3f} s exceeds {max_gap_s} s")
        if measurement_problems(a) or measurement_problems(b):
            continue
        d_ess = b["ess_w"] - a["ess_w"]
        d_load = (b["consumption_w"] - b["production_w"]) - (a["consumption_w"] - a["production_w"])
        if abs(d_ess - d_load) > transition_tolerance:
            if explained_by_limit(a) or explained_by_limit(b):
                details["limit_explained_transitions"] += 1
            else:
                problems.append(
                    f"{t1.isoformat()}: ess_w changed {d_ess:+} W while "
                    f"consumption-production changed {d_load:+} W"
                )

    if problems:
        return "NOT SUPPORTED", "; ".join(problems[:5]), details
    if details["gaps"]:
        return "INCONCLUSIVE", "; ".join(details["gaps"][:5]), details
    return (
        "SUPPORTED",
        f"{len(selected)} samples ({selection}); every ess_w change explained",
        details,
    )


def overall_from_criteria(criteria):
    if any(value == "NOT SUPPORTED" for value in criteria.values()):
        return "NOT SUPPORTED"
    if any(value == "INCONCLUSIVE" for value in criteria.values()):
        return "INCONCLUSIVE"
    return "SUPPORTED"


EVALUATOR_VERSIONS = ("v1", "v2")


def assess_backend_loss(root: Path, evaluator="v2"):
    """Assess SCN-BACKEND-LOSS with the chosen evaluator version.

    v1 reproduces the originally recorded assessment: SC-03 is SUPPORTED when
    the two outage snapshots balance. v2 requires a continuous state trace for
    SC-03; four snapshots give INCONCLUSIVE. Both versions raise EvidenceError
    on malformed evidence rather than returning a result.
    """
    if evaluator not in EVALUATOR_VERSIONS:
        raise ValueError(f"unknown evaluator {evaluator!r}")

    evidence_path, run = load_backend_loss_run(root)
    phases = normalize_phases(run)
    fmt = evidence_format(run)

    pre = phases["pre"]
    discharge = phases["discharge"]
    charge = phases["charge"]
    recovery = phases["recovery"]

    reasons = {}

    if evaluator == "v2":
        for name, phase in zip(PHASE_NAMES, (pre, discharge, charge, recovery)):
            stale = freshness_error(phase)
            if stale:
                raise EvidenceError(f"phase {name}: {stale}")

    sc01 = required_measurements(discharge) and required_measurements(charge)
    if not sc01:
        reasons["SC-01"] = "; ".join(
            measurement_problems(discharge) + measurement_problems(charge)
        )

    sc02 = (
        sc01
        and discharge["ess_w"] > 0
        and charge["ess_w"] < 0
        and balanced(discharge)
        and balanced(charge)
    )

    if evaluator == "v1":
        sc03 = "SUPPORTED" if balanced(discharge) and balanced(charge) else "NOT SUPPORTED"
        trace_details = None
    elif fmt == 1:
        sc03 = "INCONCLUSIVE"
        reasons["SC-03"] = (
            "format 1 evidence holds four snapshots and no continuous state "
            "trace; two balanced snapshots cannot show that no unexplained "
            "transition occurred between them"
        )
        trace_details = None
    else:
        sc03, reasons["SC-03"], trace_details = evaluate_state_trace(
            run, load_state_trace(evidence_path, run)
        )

    sc04 = (
        link_value(pre) is True
        and link_value(discharge) is False
        and link_value(charge) is False
        and link_value(recovery) is True
        and central_value(discharge) is True
        and central_value(charge) is True
    )

    sc05 = ordered_timestamps([pre, discharge, charge, recovery])

    reconciliation = reconciliation_evidence(root)
    if "reason" in reconciliation:
        reasons["SC-06"] = reconciliation["reason"]

    criteria = {
        "SC-01": "SUPPORTED" if sc01 else "NOT SUPPORTED",
        "SC-02": "SUPPORTED" if sc02 else "NOT SUPPORTED",
        "SC-03": sc03,
        "SC-04": "SUPPORTED" if sc04 else "NOT SUPPORTED",
        "SC-05": "SUPPORTED" if sc05 else "NOT SUPPORTED",
        "SC-06": reconciliation["status"],
    }

    return {
        "scenario": "SCN-BACKEND-LOSS",
        "evaluator_version": evaluator,
        "evidence_format": fmt,
        "evidence_file": evidence_path.relative_to(root).as_posix(),
        "criteria": criteria,
        "reasons": reasons,
        "overall_result": overall_from_criteria(criteria),
        "reconciliation": reconciliation,
        "state_trace": trace_details,
        "observations": {
            "pre_failure": pre,
            "outage_discharge": discharge,
            "outage_charge": charge,
            "recovery": recovery,
        },
    }


# ---------------------------------------------------------------------------
# Evidence manifest
# ---------------------------------------------------------------------------

def sha256_file(path: Path):
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for block in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def _within(path: Path, directory: Path):
    try:
        path.relative_to(directory)
    except ValueError:
        return False
    return True


def regular_evidence_files(evidence_dir: Path):
    """Regular files under evidence_dir. Symlinks and escaping paths are errors."""
    files = []
    for path in sorted(evidence_dir.rglob("*")):
        if path.is_symlink():
            raise EvidenceError(f"Symbolic link in evidence directory: {path}")
        if not path.is_file():
            continue
        resolved = path.resolve()
        if not _within(resolved, evidence_dir):
            raise EvidenceError(f"Path escapes evidence directory: {path}")
        files.append(resolved)
    return files


def create_manifest(
    root: Path,
    evidence_dir: Path,
    output: Path,
):
    root = root.resolve()
    evidence_dir = evidence_dir if evidence_dir.is_absolute() else root / evidence_dir
    output = output if output.is_absolute() else root / output
    evidence_dir = evidence_dir.resolve()
    output = output.resolve()

    if not _within(evidence_dir, root):
        raise EvidenceError(f"Evidence directory is outside the repository: {evidence_dir}")

    # Generate manifests only after capture has stopped. JSONL is evidence,
    # including the monitor consumed by the reconciliation assessor.
    files = [
        path for path in regular_evidence_files(evidence_dir)
        if path != output
    ]

    lines = []

    for path in files:
        relative = path.relative_to(root).as_posix()
        lines.append(
            f"{sha256_file(path)}  {relative}"
        )

    output.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    return len(files)


def verify_manifest(root: Path, manifest: Path, evidence_dir: Path = None):
    """Check every manifest entry and report evidence files the manifest omits.

    evidence_dir defaults to the manifest's own directory. Entries that are
    absolute or contain '..' are rejected before any file is read.
    """
    errors = []
    checked = 0

    root = root.resolve()
    manifest = manifest if manifest.is_absolute() else root / manifest
    manifest = manifest.resolve()

    if not manifest.exists():
        return {
            "status": "INVALID",
            "checked": 0,
            "errors": [
                f"Manifest not found: {manifest}"
            ],
        }

    if evidence_dir is None:
        evidence_dir = manifest.parent
    evidence_dir = evidence_dir if evidence_dir.is_absolute() else root / evidence_dir
    evidence_dir = evidence_dir.resolve()

    listed = set()

    for line in manifest.read_text(
        encoding="utf-8"
    ).splitlines():

        if not line.strip():
            continue

        try:
            expected, raw_path = line.split(
                None,
                1,
            )
        except ValueError:
            errors.append(
                f"Malformed manifest line: {line}"
            )
            continue

        raw_path = raw_path.strip()
        relative = Path(raw_path)

        if relative.is_absolute() or ".." in relative.parts:
            errors.append(f"Manifest path escapes repository: {raw_path}")
            continue

        path = root / relative

        if path.is_symlink():
            errors.append(f"Manifest entry is a symbolic link: {raw_path}")
            continue

        if not path.is_file():
            errors.append(
                f"Missing evidence file: {raw_path}"
            )
            continue

        resolved = path.resolve()
        if not _within(resolved, root):
            errors.append(f"Manifest path escapes repository: {raw_path}")
            continue

        listed.add(resolved)
        actual = sha256_file(resolved)
        checked += 1

        if actual != expected:
            errors.append(
                f"Hash mismatch: {raw_path}"
            )

    try:
        present = regular_evidence_files(evidence_dir)
    except EvidenceError as exc:
        present = []
        errors.append(str(exc))

    for path in present:
        if path == manifest or path in listed:
            continue
        errors.append(
            f"Unlisted evidence file: {path.relative_to(root).as_posix()}"
        )

    return {
        "status": (
            "VALID"
            if not errors
            else "INVALID"
        ),
        "checked": checked,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

def print_validation(result):
    print(
        "MODEL VALIDATION:",
        result["status"],
    )

    for key, value in result.get(
        "counts",
        {},
    ).items():
        print(f"  {key}: {value}")

    for warning in result.get(
        "warnings",
        [],
    ):
        print(
            f"WARNING: {warning}",
            file=sys.stderr,
        )

    for error in result.get(
        "errors",
        [],
    ):
        print(
            f"ERROR: {error}",
            file=sys.stderr,
        )


def print_assessment(result):
    print(
        "SCENARIO:",
        result["scenario"],
    )
    print(
        "EVIDENCE:",
        result["evidence_file"],
    )
    print(
        "EVALUATOR:",
        result["evaluator_version"],
        f"(evidence format {result['evidence_format']})",
    )

    reasons = result.get("reasons", {})

    for criterion, status in result[
        "criteria"
    ].items():
        reason = reasons.get(criterion)
        if reason:
            print(f"{criterion}: {status} ({reason})")
        else:
            print(f"{criterion}: {status}")

    print(
        "OVERALL:",
        result["overall_result"],
    )

    print(
        "LAST SUCCESSFUL RESEND:",
        result["reconciliation"][
            "last_successful_resend"
        ],
    )

    print(
        "CENTRAL BACKFILL VERIFIED:",
        result["reconciliation"][
            "central_backfill_verified"
        ],
    )


def print_manifest_result(result):
    print(
        "EVIDENCE INTEGRITY:",
        result["status"],
    )
    print(
        "FILES CHECKED:",
        result["checked"],
    )

    for error in result["errors"]:
        print(
            f"ERROR: {error}",
            file=sys.stderr,
        )


EXIT_OK = 0
EXIT_UNEXPECTED_RESULT = 1
EXIT_EVIDENCE_ERROR = 2


def assess_exit_code(result, expect):
    """Exit-code policy for `assess`.

    0: the assessment ran. With --expect RESULT the overall result must equal
       RESULT; without --expect the run itself is the success condition and
       the result (including a known INCONCLUSIVE) is reported as data.
    1: --expect was given and the overall result differs from it.
    2: (raised before this point) the evidence could not be evaluated: missing
       or malformed file, schema violation, NaN or boolean measurement,
       duplicate or non-monotonic samples, stale samples, escaping paths.

    The scenario configuration carries no expected result; CI states its
    expectation on the command line so that a changed outcome fails the job.
    """
    if expect is None or result["overall_result"] == expect:
        return EXIT_OK
    return EXIT_UNEXPECTED_RESULT


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="energy-assurance",
        description=(
            "Evidence-led assurance tooling for "
            "the OpenEMS resilience lab."
        ),
    )

    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )

    sub.add_parser(
        "validate",
        help="Validate model consistency.",
    )

    assess_parser = sub.add_parser(
        "assess",
        help="Assess the backend-loss scenario.",
        description=(
            "Assess the backend-loss scenario. Exit 0 when the assessment "
            "ran (and, with --expect, matched the expected overall result); "
            "exit 1 when --expect does not match; exit 2 when the evidence "
            "cannot be evaluated."
        ),
    )

    assess_parser.add_argument(
        "--write",
        type=Path,
        help="Write assessment JSON.",
    )

    assess_parser.add_argument(
        "--evaluator",
        choices=EVALUATOR_VERSIONS,
        default="v2",
        help=(
            "Evaluator version. v2 (default) needs a continuous state trace "
            "for SC-03 and reports INCONCLUSIVE for four-snapshot evidence. "
            "v1 reproduces the originally recorded assessment, where SC-03 "
            "was SUPPORTED by two balanced snapshots."
        ),
    )

    assess_parser.add_argument(
        "--expect",
        choices=sorted(ALLOWED_RESULTS),
        default=None,
        help=(
            "Overall result CI expects. Exit 1 if the assessment differs. "
            "Default: none (any completed assessment exits 0)."
        ),
    )

    manifest_parser = sub.add_parser(
        "manifest",
        help="Create evidence SHA-256 manifest.",
    )

    manifest_parser.add_argument(
        "--directory",
        type=Path,
        default=Path("evidence/backend-loss"),
    )

    manifest_parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "evidence/backend-loss/SHA256SUMS"
        ),
    )

    verify_parser = sub.add_parser(
        "verify-manifest",
        help="Verify evidence integrity.",
    )

    verify_parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(
            "evidence/backend-loss/SHA256SUMS"
        ),
    )

    sub.add_parser(
        "all",
        help=(
            "Validate models, assess scenario "
            "and verify evidence."
        ),
    )

    args = parser.parse_args(argv)

    root = Path.cwd()

    try:
        return run_command(args, root)
    except EvidenceError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_EVIDENCE_ERROR


def run_command(args, root: Path):
    if args.command == "validate":
        result = validate_repository(root)
        print_validation(result)

        return (
            0
            if result["status"] == "VALID"
            else 1
        )

    if args.command == "assess":
        result = assess_backend_loss(root, evaluator=args.evaluator)
        print_assessment(result)

        if args.write:
            args.write.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            args.write.write_text(
                json.dumps(
                    result,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

        return assess_exit_code(result, args.expect)

    if args.command == "manifest":
        args.output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        count = create_manifest(
            root,
            args.directory,
            args.output,
        )

        print(
            f"EVIDENCE MANIFEST: "
            f"{count} files"
        )
        print(args.output)

        return 0

    if args.command == "verify-manifest":
        result = verify_manifest(
            root,
            args.manifest,
        )

        print_manifest_result(result)

        return (
            0
            if result["status"] == "VALID"
            else 1
        )

    if args.command == "all":
        validation = validate_repository(root)
        print_validation(validation)

        print()

        assessment = assess_backend_loss(root)
        print_assessment(assessment)

        print()

        manifest = verify_manifest(
            root,
            root
            / "evidence/backend-loss/SHA256SUMS",
        )

        print_manifest_result(manifest)

        return (
            0
            if (
                validation["status"] == "VALID"
                and manifest["status"] == "VALID"
            )
            else 1
        )

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
