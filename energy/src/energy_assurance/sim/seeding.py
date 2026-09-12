"""Deterministic seed derivation.

A master seed and a run index determine every random draw of that run.
The derivation is

    sub_seed(master, domain, index) = int.from_bytes(
        sha256(f"{master}|{domain}|{index}".encode("ascii")).digest()[:8], "big")

so the per-run seed depends only on (master, domain, index), never on the
worker that executes the run, the chunk it lands in or the order in which
runs complete. ``domain`` separates independent streams that share an
index (for example the site runs and the fleet sites of one study).
"""

from __future__ import annotations

import hashlib
import random


def sub_seed(master_seed: int, domain: str, index: int) -> int:
    """64-bit sub-seed for (master_seed, domain, index); see module docstring."""
    if not isinstance(master_seed, int) or isinstance(master_seed, bool):
        raise TypeError("master_seed must be an int")
    if not isinstance(index, int) or isinstance(index, bool):
        raise TypeError("index must be an int")
    if "|" in domain:
        raise ValueError("domain must not contain '|'")
    payload = f"{master_seed}|{domain}|{index}".encode("ascii")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def run_rng(master_seed: int, domain: str, index: int) -> random.Random:
    """A ``random.Random`` seeded with ``sub_seed``; one per run, never shared."""
    return random.Random(sub_seed(master_seed, domain, index))
