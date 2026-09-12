"""Serial and parallel Monte Carlo runners with JSONL checkpointing.

Design rules
------------
* A run is ``scenario.run(master_seed, run_id)``; the per-run RNG is derived
  from (master_seed, run_id) inside the scenario, so no RNG is shared and
  the worker count cannot change any result.
* The parallel runner is a single-node ``ProcessPoolExecutor``. Run ids
  are grouped into chunks; each worker returns ``[(run_id, result), ...]``
  for its chunk; the parent merges into a dict keyed by run_id and returns
  the results sorted by run_id. Nothing is written by workers.
* Checkpointing: the parent appends one JSON line ``{"run_id", "result"}``
  per completed run to ``checkpoint_path`` as chunks complete. A restart
  reads the file, skips completed run ids and only submits the rest. A
  run id that appears twice in the file (a crash between write and flush
  cannot cause this, but a manual concatenation could) is detected and
  rejected on load.
* A failing chunk does not stop the other chunks: their results are still
  checkpointed, and the first failure is re-raised as ``RunFailure`` after
  every submitted future has finished, so partial progress survives.

Equivalence contract: serial and parallel results for the same master seed
are identical for every integer, string and boolean field, and floats are
identical in practice (same interpreter, same code path, no reduction
across runs). Tests assert exact integer equality and
``math.isclose(rel_tol=1e-9, abs_tol=1e-9)`` for floats; the tolerance is
declared so that a future change of summation order inside a run (for
example a vectorised profile) has a stated budget instead of an implicit
"bit-identical" claim.
"""

from __future__ import annotations

import json
import math
import os
from concurrent.futures import Future, ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Iterable, Sequence

FLOAT_REL_TOL = 1e-9
FLOAT_ABS_TOL = 1e-9


class RunFailure(RuntimeError):
    """One or more chunks failed; ``completed`` results were checkpointed."""

    def __init__(self, message: str, failed_run_ids: list[int], completed: int):
        super().__init__(message)
        self.failed_run_ids = failed_run_ids
        self.completed = completed


class Checkpoint:
    """Append-only JSONL of completed runs."""

    def __init__(self, path: Path | str | None):
        self.path = Path(path) if path is not None else None
        self._handle = None

    def load(self) -> dict[int, dict]:
        results: dict[int, dict] = {}
        if self.path is None or not self.path.exists():
            return results
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                run_id = int(record["run_id"])
                if run_id in results:
                    raise ValueError(f"{self.path}: run_id {run_id} recorded twice (line {line_number})")
                results[run_id] = record["result"]
        return results

    def append(self, run_id: int, result: dict) -> None:
        if self.path is None:
            return
        if self._handle is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._handle = self.path.open("a", encoding="utf-8", newline="\n")
        self._handle.write(json.dumps({"run_id": run_id, "result": result}, sort_keys=True))
        self._handle.write("\n")
        self._handle.flush()
        os.fsync(self._handle.fileno())

    def close(self) -> None:
        if self._handle is not None:
            self._handle.close()
            self._handle = None


def chunked(run_ids: Sequence[int], chunk_size: int) -> list[list[int]]:
    if chunk_size < 1:
        raise ValueError("chunk_size must be >= 1")
    return [list(run_ids[i:i + chunk_size]) for i in range(0, len(run_ids), chunk_size)]


def default_chunk_size(n_runs: int, workers: int) -> int:
    """About four chunks per worker, at least one run per chunk."""
    return max(1, math.ceil(n_runs / (4 * max(1, workers))))


def _run_chunk(scenario, master_seed: int, run_ids: list[int]) -> list[tuple[int, dict]]:
    """Worker entry point: executes a chunk and returns results keyed by run_id."""
    return [(run_id, scenario.run(master_seed, run_id)) for run_id in run_ids]


def _merge(results: dict[int, dict]) -> list[dict]:
    return [results[run_id] for run_id in sorted(results)]


def run_serial(
    scenario,
    master_seed: int,
    run_ids: Iterable[int],
    checkpoint_path: Path | str | None = None,
) -> list[dict]:
    """Reference runner: one run after another in this process."""
    checkpoint = Checkpoint(checkpoint_path)
    results = checkpoint.load()
    try:
        for run_id in run_ids:
            if run_id in results:
                continue
            result = scenario.run(master_seed, run_id)
            checkpoint.append(run_id, result)
            results[run_id] = result
    finally:
        checkpoint.close()
    return _merge(results)


def run_parallel(
    scenario,
    master_seed: int,
    run_ids: Iterable[int],
    workers: int | None = None,
    chunk_size: int | None = None,
    checkpoint_path: Path | str | None = None,
    executor: ProcessPoolExecutor | None = None,
    on_chunk: Callable[[list[int]], None] | None = None,
) -> list[dict]:
    """Process-pool runner; same results as ``run_serial`` for the same seed.

    ``executor`` lets a caller (the benchmark) reuse a warm pool so that
    pool start-up is measured separately from compute.
    """
    run_ids = list(run_ids)
    workers = workers or os.cpu_count() or 1
    checkpoint = Checkpoint(checkpoint_path)
    results = checkpoint.load()
    pending = [run_id for run_id in run_ids if run_id not in results]
    if not pending:
        checkpoint.close()
        return _merge(results)
    size = chunk_size or default_chunk_size(len(pending), workers)
    chunks = chunked(pending, size)

    own_executor = executor is None
    pool = executor if executor is not None else ProcessPoolExecutor(max_workers=workers)
    failures: list[tuple[list[int], BaseException]] = []
    try:
        futures: dict[Future, list[int]] = {
            pool.submit(_run_chunk, scenario, master_seed, chunk): chunk for chunk in chunks
        }
        for future in as_completed(futures):
            chunk = futures[future]
            try:
                chunk_results = future.result()
            except BaseException as error:  # noqa: BLE001 - recorded and re-raised below
                failures.append((chunk, error))
                continue
            for run_id, result in chunk_results:
                checkpoint.append(run_id, result)
                results[run_id] = result
            if on_chunk is not None:
                on_chunk(chunk)
    finally:
        checkpoint.close()
        if own_executor:
            pool.shutdown(wait=True)
    if failures:
        failed_ids = sorted(run_id for chunk, _ in failures for run_id in chunk)
        first = failures[0][1]
        raise RunFailure(
            f"{len(failures)} chunk(s) failed ({len(failed_ids)} runs); first error: {first!r}",
            failed_ids,
            len(results),
        ) from first
    return _merge(results)


def results_equivalent(left, right, rel_tol: float = FLOAT_REL_TOL, abs_tol: float = FLOAT_ABS_TOL) -> bool:
    """Structural equality: exact for ints/str/bool/None, isclose for floats."""
    if isinstance(left, bool) or isinstance(right, bool):
        return left is right
    if isinstance(left, float) or isinstance(right, float):
        if not isinstance(left, (int, float)) or not isinstance(right, (int, float)):
            return False
        return math.isclose(left, right, rel_tol=rel_tol, abs_tol=abs_tol)
    if isinstance(left, int) and isinstance(right, int):
        return left == right
    if isinstance(left, dict) and isinstance(right, dict):
        if left.keys() != right.keys():
            return False
        return all(results_equivalent(left[k], right[k], rel_tol, abs_tol) for k in left)
    if isinstance(left, (list, tuple)) and isinstance(right, (list, tuple)):
        if len(left) != len(right):
            return False
        return all(results_equivalent(a, b, rel_tol, abs_tol) for a, b in zip(left, right))
    return left == right
