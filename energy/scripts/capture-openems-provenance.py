#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path


EXPECTED_COMMIT = "189ac916fd653d3496797ac20921d18a2e6237f1"

PROJECT = Path(__file__).resolve().parents[1]
UPSTREAM = PROJECT.parent / "openems-upstream"

ARTIFACTS = [
    UPSTREAM / "build/openems-edge.jar",
    UPSTREAM / "build/openems-backend.jar",
    UPSTREAM / "build/openems-backend-edge.jar",
]


def run(*args):
    return subprocess.run(
        args,
        cwd=UPSTREAM,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def sha256(path: Path):
    h = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def embedded_jars(path: Path):
    with zipfile.ZipFile(path) as archive:
        names = sorted(
            name
            for name in archive.namelist()
            if name.startswith("jar/")
            and name.endswith(".jar")
        )

    return names


def java_version():
    result = subprocess.run(
        ["java", "-version"],
        capture_output=True,
        text=True,
        check=True,
    )

    return (
        result.stderr.strip()
        or result.stdout.strip()
    )


if not UPSTREAM.exists():
    raise SystemExit(
        f"OpenEMS upstream not found: {UPSTREAM}"
    )

commit = run("git", "rev-parse", "HEAD")

if commit != EXPECTED_COMMIT:
    raise SystemExit(
        "UPSTREAM COMMIT MISMATCH\n"
        f"expected={EXPECTED_COMMIT}\n"
        f"actual={commit}"
    )

status = run("git", "status", "--porcelain")

artifacts = []

for artifact in ARTIFACTS:
    if not artifact.exists():
        raise SystemExit(
            f"Missing build artifact: {artifact}"
        )

    jars = embedded_jars(artifact)

    artifacts.append(
        {
            "name": artifact.name,
            "path": str(artifact),
            "size_bytes": artifact.stat().st_size,
            "sha256": sha256(artifact),
            "embedded_jar_count": len(jars),
            "embedded_jars": jars,
        }
    )

wrapper_jar = (
    UPSTREAM
    / "gradle/wrapper/gradle-wrapper.jar"
)

wrapper_props = (
    UPSTREAM
    / "gradle/wrapper/gradle-wrapper.properties"
)

record = {
    "captured_at_utc": (
        datetime.now(timezone.utc).isoformat()
    ),
    "upstream": {
        "repository": (
            "https://github.com/OpenEMS/openems"
        ),
        "expected_commit": EXPECTED_COMMIT,
        "observed_commit": commit,
        "working_tree_clean": status == "",
        "working_tree_status": (
            status.splitlines()
            if status
            else []
        ),
    },
    "build_environment": {
        "java": java_version(),
        "gradle_wrapper_properties": (
            wrapper_props.read_text(
                encoding="utf-8"
            ).splitlines()
            if wrapper_props.exists()
            else []
        ),
        "gradle_wrapper_jar_sha256": (
            sha256(wrapper_jar)
            if wrapper_jar.exists()
            else None
        ),
    },
    "artifacts": artifacts,
}

out = (
    PROJECT
    / "evidence/supply-chain/"
    "openems-provenance.json"
)

out.write_text(
    json.dumps(record, indent=2) + "\n",
    encoding="utf-8",
)

lock = {
    "repository": (
        "https://github.com/OpenEMS/openems"
    ),
    "commit": EXPECTED_COMMIT,
    "artifacts": {
        item["name"]: {
            "sha256": item["sha256"],
            "size_bytes": item["size_bytes"],
        }
        for item in artifacts
    },
}

(
    PROJECT
    / "config/openems-upstream-lock.json"
).write_text(
    json.dumps(lock, indent=2) + "\n",
    encoding="utf-8",
)

print("=== SUPPLY CHAIN PROVENANCE ===")
print("Commit:", commit)
print("Working tree clean:", status == "")

for artifact in artifacts:
    print()
    print(artifact["name"])
    print(
        "  size:",
        artifact["size_bytes"],
    )
    print(
        "  sha256:",
        artifact["sha256"],
    )
    print(
        "  embedded jars:",
        artifact["embedded_jar_count"],
    )

print()
print("PROVENANCE RECORDED")
