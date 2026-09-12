#!/usr/bin/env python3
"""Build the three OpenEMS fat jars inside the `builder` compose service.

    python scripts/lab_build.py [--openems-dir PATH] [--skip-build]

Runs `./gradlew --no-daemon buildEdge buildBackend buildBackendEdge` in
eclipse-temurin:21-jdk against the pinned upstream checkout (OPENEMS_DIR,
default ../../../openems-upstream relative to the compose file), then records
each jar's size and SHA-256 together with the upstream commit into
energy/infra/build-record.json. Evidence capture is the runner's job; this
file is a build receipt only.

Refuses to run when the upstream checkout is not at the pinned commit or has
tracked local changes: the build would then not be the documented baseline.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lab_common import (  # noqa: E402
    BUILD_RECORD, COMPOSE_FILE, Compose, JARS_DIR, LabError, OPENEMS_COMMIT,
    file_record, iso, openems_dir_from_env, utc_now, write_json,
)

JARS = ("openems-edge.jar", "openems-backend.jar", "openems-backend-edge.jar")
GRADLE_TASKS = ("buildEdge", "buildBackend", "buildBackendEdge")


def git_output(repo: Path, *args: str, runner=subprocess.run) -> str:
    result = runner(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise LabError(f"git {' '.join(args)} failed in {repo}: {result.stderr.strip()}")
    return result.stdout.strip()


def check_upstream(repo: Path, expected_commit: str = OPENEMS_COMMIT, runner=subprocess.run) -> dict:
    if not (repo / ".git").exists():
        raise LabError(f"OpenEMS checkout not found at {repo} (set OPENEMS_DIR)")
    head = git_output(repo, "rev-parse", "HEAD", runner=runner)
    if head != expected_commit:
        raise LabError(f"OpenEMS checkout is at {head}, expected pinned {expected_commit}")
    dirty = git_output(repo, "status", "--porcelain", "--untracked-files=no", runner=runner)
    if dirty:
        raise LabError("OpenEMS checkout has tracked local changes; refusing to build")
    return {"path": repo.as_posix(), "commit": head}


def build_record(jars_dir: Path, upstream: dict, compose_file: Path, started_at: str,
                 finished_at: str, skipped: bool) -> dict:
    jars = {}
    for name in JARS:
        record = file_record(jars_dir / name)
        if record.get("missing"):
            raise LabError(f"expected jar not produced: {jars_dir / name}")
        jars[name] = {k: record[k] for k in ("size", "sha256", "mtime_ns")}
    return {
        "schema": "lab-build-record/1",
        "upstream": upstream,
        "builder_image": "eclipse-temurin:21-jdk",
        "gradle_tasks": list(GRADLE_TASKS),
        "gradle_flags": ["--no-daemon", "--console=plain"],
        "compose_file": compose_file.as_posix(),
        "build_skipped": skipped,
        "started_at_utc": started_at,
        "finished_at_utc": finished_at,
        "jars": jars,
    }


def run_build(compose: Compose, openems_dir: Path, jars_dir: Path = JARS_DIR,
              record_path: Path = BUILD_RECORD, skip_build: bool = False,
              git_runner=subprocess.run) -> dict:
    upstream = check_upstream(openems_dir, runner=git_runner)
    jars_dir.mkdir(parents=True, exist_ok=True)
    started = iso(utc_now())
    if not skip_build:
        os.environ["OPENEMS_DIR"] = openems_dir.as_posix()
        compose.run_one_off("builder", profile="build")
    finished = iso(utc_now())
    record = build_record(jars_dir, upstream, compose.compose_file, started, finished, skip_build)
    write_json(record_path, record)
    return record


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--openems-dir", type=Path, default=None,
                        help="Upstream checkout (default: $OPENEMS_DIR or ../../../openems-upstream)")
    parser.add_argument("--skip-build", action="store_true",
                        help="Only (re)write build-record.json from jars already in infra/jars.")
    args = parser.parse_args(argv)
    openems_dir = args.openems_dir or openems_dir_from_env()
    try:
        record = run_build(Compose(COMPOSE_FILE), openems_dir.resolve(), skip_build=args.skip_build)
    except LabError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    for name, jar in record["jars"].items():
        print(f"{jar['sha256']}  {name}  ({jar['size']} bytes)")
    print(f"BUILD RECORD {BUILD_RECORD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
