"""Deterministic site simulation and Monte Carlo runner (work package P06).

Single-node, standard-library only. The model in ``model.py`` is a 1 Hz
discrete-time classification model of the fictional reference site
REF-ENERGY-001 described in ``data/service-model.json``; it says nothing
about real equipment. ``scenario.py`` turns a master seed and parameters
into concrete runs, ``runner.py`` executes them serially or in a process
pool with checkpointing, ``seeding.py`` derives per-run seeds.
"""

from .limits import SiteLimits, load_site_limits
from .model import RunSpec, Profile, simulate
from .scenario import FleetScenario, SiteScenario, fleet_resend_load
from .seeding import sub_seed
from .runner import run_parallel, run_serial

__all__ = [
    "FleetScenario",
    "Profile",
    "RunSpec",
    "SiteLimits",
    "SiteScenario",
    "fleet_resend_load",
    "load_site_limits",
    "run_parallel",
    "run_serial",
    "simulate",
    "sub_seed",
]
