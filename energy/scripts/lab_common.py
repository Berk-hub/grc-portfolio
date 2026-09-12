"""Shared pieces of the OpenEMS lab tooling (P02).

Everything here is pure Python with no third-party dependencies. The classes
that touch the outside world (Docker, the edge REST API, InfluxDB, TCP ports)
are thin so that tests can replace them with fakes.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
import subprocess
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
ENERGY_DIR = SCRIPTS_DIR.parent
INFRA_DIR = ENERGY_DIR / "infra"
COMPOSE_FILE = INFRA_DIR / "docker-compose.yml"
ENV_FILE = INFRA_DIR / ".env"
RUNTIME_DIR = INFRA_DIR / "runtime"
JARS_DIR = INFRA_DIR / "jars"
BUILD_RECORD = INFRA_DIR / "build-record.json"
EXPERIMENTS_DIR = ENERGY_DIR / "experiments"
RUNS_DIR = ENERGY_DIR / "evidence" / "runs"

# Pinned upstream commit (docs/00-upstream-baseline.md, scripts/setup-openems.sh).
OPENEMS_COMMIT = "189ac916fd653d3496797ac20921d18a2e6237f1"


class LabError(Exception):
    """Any condition that must stop the lab tooling loudly."""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(moment: datetime) -> str:
    return moment.isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_record(path: Path) -> dict:
    """Size, mtime and SHA-256 of a file, or a 'missing' record."""
    if not path.is_file():
        return {"path": path.as_posix(), "missing": True}
    stat = path.stat()
    return {
        "path": path.as_posix(),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "sha256": sha256_file(path),
    }


def write_json(path: Path, payload) -> None:
    """Write pretty JSON with LF line endings (never CRLF, even on Windows)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=False, allow_nan=False) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, allow_nan=False, separators=(",", ":"))
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(line + "\n")


def read_env_file(path: Path) -> dict:
    """Parse a KEY=VALUE env file (no quoting rules beyond stripping)."""
    values = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


# ---------------------------------------------------------------------------
# Docker Compose
# ---------------------------------------------------------------------------

class Compose:
    """Thin wrapper around `docker compose` so tests can substitute a fake.

    Every call is a subprocess; nothing is cached. A non-zero exit raises
    LabError with the captured stderr.
    """

    def __init__(self, compose_file: Path = COMPOSE_FILE, env_file: Path = ENV_FILE,
                 project: str = "openems-lab", runner=subprocess.run):
        self.compose_file = Path(compose_file)
        self.env_file = Path(env_file)
        self.project = project
        self._run = runner

    def _base(self):
        cmd = ["docker", "compose", "-f", str(self.compose_file), "-p", self.project]
        if self.env_file.is_file():
            cmd += ["--env-file", str(self.env_file)]
        return cmd

    def run(self, *args: str, check: bool = True, timeout: int | None = None) -> subprocess.CompletedProcess:
        cmd = self._base() + list(args)
        result = self._run(cmd, capture_output=True, text=True, timeout=timeout)
        if check and result.returncode != 0:
            raise LabError(
                f"docker compose {' '.join(args)} failed ({result.returncode}): "
                f"{(result.stderr or result.stdout).strip()}"
            )
        return result

    def up(self, *services: str, wait: bool = True) -> None:
        args = ["up", "-d"]
        if wait:
            args.append("--wait")
        self.run(*args, *services, timeout=1800)

    def stop(self, service: str) -> None:
        self.run("stop", service, timeout=120)

    def start(self, service: str) -> None:
        self.run("start", service, timeout=120)

    def down(self, volumes: bool = False) -> None:
        args = ["down", "--remove-orphans"]
        if volumes:
            args.append("-v")
        self.run(*args, timeout=300)

    def run_one_off(self, service: str, *command: str, profile: str | None = None) -> subprocess.CompletedProcess:
        args = []
        if profile:
            args += ["--profile", profile]
        args += ["run", "--rm", service, *command]
        return self.run(*args, timeout=7200)

    def ps_json(self) -> list:
        result = self.run("ps", "--all", "--format", "json", timeout=60)
        rows = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if line:
                rows.append(json.loads(line))
        return rows

    def logs(self, service: str, tail: int = 200) -> str:
        return self.run("logs", "--no-color", "--tail", str(tail), service, check=False, timeout=60).stdout


# ---------------------------------------------------------------------------
# Edge REST / JSON-RPC (Controller.Api.Rest.ReadWrite)
# ---------------------------------------------------------------------------

class EdgeRest:
    """GET/POST /rest/channel and POST /jsonrpc with HTTP Basic auth.

    User "x" with the admin password works because the REST handler falls
    back to a password-only match (see docs/03-architecture.md).
    """

    def __init__(self, base_url: str = "http://127.0.0.1:8084", user: str = "x",
                 password: str = "admin", timeout: float = 10.0, opener=urllib.request.urlopen):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._open = opener
        token = base64.b64encode(f"{user}:{password}".encode()).decode()
        self._headers = {"Authorization": f"Basic {token}", "Content-Type": "application/json"}

    def _request(self, method: str, path: str, payload=None):
        data = None if payload is None else json.dumps(payload).encode()
        request = urllib.request.Request(
            f"{self.base_url}{path}", data=data, headers=self._headers, method=method
        )
        try:
            with self._open(request, timeout=self.timeout) as response:
                body = response.read()
        except urllib.error.HTTPError as exc:
            raise LabError(f"{method} {path} -> HTTP {exc.code}: {exc.read()[:300]!r}") from exc
        except (urllib.error.URLError, OSError) as exc:
            raise LabError(f"{method} {path} failed: {exc}") from exc
        if not body:
            return None
        try:
            return json.loads(body)
        except ValueError as exc:
            raise LabError(f"{method} {path}: non-JSON response {body[:300]!r}") from exc

    def get_channel(self, component: str, channel: str):
        result = self._request("GET", f"/rest/channel/{component}/{channel}")
        if not isinstance(result, dict) or "value" not in result:
            raise LabError(f"GET {component}/{channel}: unexpected payload {result!r}")
        return result["value"]

    def set_channel(self, component: str, channel: str, value) -> None:
        self._request("POST", f"/rest/channel/{component}/{channel}", {"value": value})

    def jsonrpc(self, method: str, params: dict):
        payload = {"jsonrpc": "2.0", "id": str(uuid.uuid4()), "method": method, "params": params}
        result = self._request("POST", "/jsonrpc", payload)
        if not isinstance(result, dict):
            raise LabError(f"jsonrpc {method}: unexpected payload {result!r}")
        if "error" in result:
            raise LabError(f"jsonrpc {method} failed: {json.dumps(result['error'])}")
        return result.get("result")


# ---------------------------------------------------------------------------
# InfluxDB 2.x HTTP API (Flux)
# ---------------------------------------------------------------------------

class InfluxClient:
    def __init__(self, url: str, org: str, token: str, bucket: str, timeout: float = 60.0,
                 opener=urllib.request.urlopen):
        self.url = url.rstrip("/")
        self.org = org
        self.token = token
        self.bucket = bucket
        self.timeout = timeout
        self._open = opener

    def query_csv(self, flux: str) -> str:
        request = urllib.request.Request(
            f"{self.url}/api/v2/query?org={self.org}",
            data=flux.encode(),
            headers={
                "Authorization": f"Token {self.token}",
                "Content-Type": "application/vnd.flux",
                "Accept": "application/csv",
            },
            method="POST",
        )
        try:
            with self._open(request, timeout=self.timeout) as response:
                return response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            raise LabError(f"influx query -> HTTP {exc.code}: {exc.read()[:300]!r}") from exc
        except (urllib.error.URLError, OSError) as exc:
            raise LabError(f"influx query failed: {exc}") from exc

    def channel_samples(self, measurement: str, edge_tag: str, edge_id: str,
                        fields: list, start: str, stop: str) -> list:
        """Raw points for the given fields in [start, stop] as structured rows."""
        field_filter = " or ".join(f'r["_field"] == "{f}"' for f in fields)
        flux = (
            f'from(bucket: "{self.bucket}")\n'
            f'  |> range(start: {start}, stop: {stop})\n'
            f'  |> filter(fn: (r) => r["_measurement"] == "{measurement}")\n'
            f'  |> filter(fn: (r) => r["{edge_tag}"] == "{edge_id}")\n'
            f'  |> filter(fn: (r) => {field_filter})\n'
            f'  |> keep(columns: ["_time", "_field", "_value"])\n'
            f'  |> sort(columns: ["_time"])\n'
        )
        return parse_annotated_csv(self.query_csv(flux)), flux


def parse_annotated_csv(text: str) -> list:
    """Parse Influx annotated CSV into [{"time": ..., "field": ..., "value": ...}]."""
    rows = []
    header = None
    for raw in text.splitlines():
        line = raw.rstrip("\r")
        if not line.strip():
            header = None
            continue
        if line.startswith("#"):
            continue
        cells = line.split(",")
        if header is None:
            header = cells
            continue
        record = dict(zip(header, cells))
        if "_time" not in record or "_field" not in record:
            continue
        raw_value = record.get("_value", "")
        try:
            value = int(raw_value)
        except ValueError:
            try:
                value = float(raw_value)
            except ValueError:
                value = raw_value
        rows.append({"time": record["_time"], "field": record["_field"], "value": value})
    return rows


# ---------------------------------------------------------------------------
# TCP probe (link-state evidence)
# ---------------------------------------------------------------------------

def tcp_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def openems_dir_from_env(default: Path | None = None) -> Path:
    raw = os.environ.get("OPENEMS_DIR")
    if raw:
        return Path(raw)
    return default if default is not None else (ENERGY_DIR.parent.parent / "openems-upstream")
