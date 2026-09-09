from __future__ import annotations

import argparse
import hashlib
import json
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


def ordered_timestamps(snapshots):
    values = []

    for snapshot in snapshots:
        raw = snapshot.get("captured_at_utc")

        if not raw:
            return False

        try:
            values.append(
                datetime.fromisoformat(
                    raw.replace("Z", "+00:00")
                )
            )
        except ValueError:
            return False

    return values == sorted(values)


def balanced(snapshot, tolerance=50):
    try:
        return (
            abs(snapshot["grid_w"]) <= tolerance
            and
            abs(
                snapshot["power_balance_residual_w"]
            ) <= tolerance
        )
    except (KeyError, TypeError):
        return False


def required_measurements(snapshot):
    names = (
        "consumption_w",
        "production_w",
        "ess_w",
        "grid_w",
        "ess_soc_pct",
    )

    return all(
        snapshot.get(name) is not None
        for name in names
    )


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
        }

    text = post_resend.read_text(
        encoding="utf-8",
        errors="replace",
    )

    expected_markers = (
        "5200",
        "700",
        "4500",
        "1800",
        "4300",
        "-2500",
    )

    backfill = all(
        marker in text
        for marker in expected_markers
    )

    return {
        "status": (
            "SUPPORTED"
            if backfill
            else "INCONCLUSIVE"
        ),
        "last_successful_resend": resend_value,
        "central_backfill_verified": backfill,
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
        return final_run, load_json(final_run)

    if earlier_run.exists():
        return earlier_run, load_json(earlier_run)

    raise FileNotFoundError(
        "No backend-loss evidence run found"
    )


def normalize_phases(run):
    if "phases" in run:
        phases = run["phases"]

        return {
            "pre": phases["pre_failure"],
            "discharge": phases["outage_discharge"],
            "charge": phases["outage_charge"],
            "recovery": phases["recovery"],
        }

    return {
        "pre": run["pre_failure"],
        "discharge": run["outage_discharge"],
        "charge": run["outage_charge"],
        "recovery": run["recovery"],
    }


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


def assess_backend_loss(root: Path):
    evidence_path, run = load_backend_loss_run(root)
    phases = normalize_phases(run)

    pre = phases["pre"]
    discharge = phases["discharge"]
    charge = phases["charge"]
    recovery = phases["recovery"]

    sc01 = (
        required_measurements(discharge)
        and required_measurements(charge)
    )

    sc02 = (
        discharge.get("ess_w", 0) > 0
        and charge.get("ess_w", 0) < 0
        and balanced(discharge)
        and balanced(charge)
    )

    sc03 = (
        balanced(discharge)
        and balanced(charge)
    )

    sc04 = (
        link_value(pre) is True
        and link_value(discharge) is False
        and link_value(charge) is False
        and link_value(recovery) is True
        and central_value(discharge) is True
        and central_value(charge) is True
    )

    sc05 = ordered_timestamps(
        [
            pre,
            discharge,
            charge,
            recovery,
        ]
    )

    reconciliation = reconciliation_evidence(root)

    criteria = {
        "SC-01": (
            "SUPPORTED"
            if sc01
            else "NOT SUPPORTED"
        ),
        "SC-02": (
            "SUPPORTED"
            if sc02
            else "NOT SUPPORTED"
        ),
        "SC-03": (
            "SUPPORTED"
            if sc03
            else "NOT SUPPORTED"
        ),
        "SC-04": (
            "SUPPORTED"
            if sc04
            else "NOT SUPPORTED"
        ),
        "SC-05": (
            "SUPPORTED"
            if sc05
            else "NOT SUPPORTED"
        ),
        "SC-06": reconciliation["status"],
    }

    if any(
        value == "NOT SUPPORTED"
        for value in criteria.values()
    ):
        overall = "NOT SUPPORTED"

    elif any(
        value == "INCONCLUSIVE"
        for value in criteria.values()
    ):
        overall = "INCONCLUSIVE"

    else:
        overall = "SUPPORTED"

    return {
        "scenario": "SCN-BACKEND-LOSS",
        "evidence_file": str(
            evidence_path.relative_to(root)
        ),
        "criteria": criteria,
        "overall_result": overall,
        "reconciliation": reconciliation,
        "observations": {
            "pre_failure": pre,
            "outage_discharge": discharge,
            "outage_charge": charge,
            "recovery": recovery,
        },
    }


def sha256_file(path: Path):
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for block in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


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

    files = []

    for path in sorted(evidence_dir.rglob("*")):
        if not path.is_file():
            continue

        if path.resolve() == output.resolve():
            continue

        # This file can still be changing while the
        # OpenEMS resend worker is under observation.
        if (
            path.name
            == "13-historic-resend-monitor.jsonl"
        ):
            continue

        files.append(path)

    lines = []

    for path in files:
        relative = path.relative_to(root)
        lines.append(
            f"{sha256_file(path)}  {relative}"
        )

    output.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    return len(files)


def verify_manifest(root: Path, manifest: Path):
    errors = []
    checked = 0

    if not manifest.exists():
        return {
            "status": "INVALID",
            "checked": 0,
            "errors": [
                f"Manifest not found: {manifest}"
            ],
        }

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

        path = root / raw_path.strip()

        if not path.exists():
            errors.append(
                f"Missing evidence file: {raw_path}"
            )
            continue

        actual = sha256_file(path)
        checked += 1

        if actual != expected:
            errors.append(
                f"Hash mismatch: {raw_path}"
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

    for criterion, status in result[
        "criteria"
    ].items():
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
    )

    assess_parser.add_argument(
        "--write",
        type=Path,
        help="Write assessment JSON.",
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

    if args.command == "validate":
        result = validate_repository(root)
        print_validation(result)

        return (
            0
            if result["status"] == "VALID"
            else 1
        )

    if args.command == "assess":
        result = assess_backend_loss(root)
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

        return 0

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

        print(
            "EVIDENCE INTEGRITY:",
            manifest["status"],
        )
        print(
            "FILES CHECKED:",
            manifest["checked"],
        )

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
