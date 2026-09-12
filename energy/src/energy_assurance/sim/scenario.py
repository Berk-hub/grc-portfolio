"""Scenarios: master seed + parameters -> concrete runs.

Two scenario kinds exist. Both are frozen dataclasses, picklable, and expose
``run(master_seed, run_index) -> dict`` so the runner does not care which
one it executes.

* ``SiteScenario`` draws one site run: outage timing, reconnection, the
  resend delay, an optional stale-meter fault, an optional second outage,
  an optional grid outage, PV size and load phase, then calls
  ``model.simulate``.
* ``FleetScenario`` answers the "thundering herd" question the upstream
  random delay exists for: N sites reconnect after one regional backend
  outage, each draws its own resend delay, and the result is the backend
  resend-load time series (sites starting and sites actively resending per
  minute).

Resend constants (docs/13-sc06-root-cause.md, pinned source 189ac916):
``DELAY_TRIGGER_TIME`` 300 s, ``MAX_RANDOM_DELAY`` 3600 s,
``MAX_RESEND_TIMESPAN_SECONDS`` 300 s, gap buffer 300 s, RRD4J step 300 s.
The delay draw is ``300 + U[0, 3600)`` s, so it lies in [300, 3900).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from random import Random

from .limits import load_site_limits
from .model import Profile, RunSpec, simulate
from .seeding import run_rng

RESEND_DELAY_FIXED_S = 300
RESEND_DELAY_RANDOM_MAX_S = 3600
RESEND_QUERY_SPAN_S = 300
RESEND_GAP_BUFFER_S = 300


def draw_resend_delay_s(rng: Random) -> float:
    """300 s + Uniform[0, 3600) s, the upstream scheduling delay."""
    return RESEND_DELAY_FIXED_S + rng.random() * RESEND_DELAY_RANDOM_MAX_S


def resend_transfer_s(gap_s: float, query_time_s: float) -> float:
    """Transfer time: one query per started 300 s span of gap plus buffer."""
    n_queries = int(math.ceil((gap_s + RESEND_GAP_BUFFER_S) / RESEND_QUERY_SPAN_S))
    return n_queries * query_time_s


def _uniform_int(rng: Random, bounds: tuple[int, int]) -> int:
    lo, hi = bounds
    if hi < lo:
        raise ValueError(f"bad range {bounds}")
    return lo + int(rng.random() * (hi - lo + 1)) if hi > lo else lo


def _uniform(rng: Random, bounds: tuple[float, float]) -> float:
    lo, hi = bounds
    return lo + rng.random() * (hi - lo)


@dataclass(frozen=True)
class SiteScenario:
    """Parameter ranges for one site run; every draw uses the run's own RNG.

    Draw order is fixed and documented here because it is part of the
    contract that makes results reproducible: (1) initial SoC, (2) PV peak,
    (3) deferrable phase, (4) link outage start, (5) link outage duration,
    (6) link detection delay, (7) resend delay for the first reconnection,
    (8) second outage present?, gap, duration, its resend delay,
    (9) stale-meter fault present?, start, duration,
    (10) grid outage present?, start, duration.
    """

    name: str = "site-default"
    duration_s: int = 600
    initial_soc_pct_range: tuple[float, float] = (45.0, 55.0)
    pv_peak_w_range: tuple[float, float] = (0.0, 6000.0)
    pv_kind: str = "constant"
    pv_period_s: float = 43200.0
    crit_load_w: float | None = None  # None -> LOAD-CRIT-001 from the service model
    def_load_w: float | None = None  # None -> LOAD-DEF-001
    def_kind: str = "square"
    def_period_s: float = 300.0
    link_outage_start_s_range: tuple[int, int] = (60, 120)
    link_outage_duration_s_range: tuple[int, int] = (60, 240)
    link_detect_delay_s_range: tuple[int, int] = (1, 12)
    second_outage_probability: float = 0.0
    second_outage_gap_s_range: tuple[int, int] = (30, 120)
    second_outage_duration_s_range: tuple[int, int] = (30, 120)
    stale_meter_probability: float = 0.0
    stale_meter_start_s_range: tuple[int, int] = (30, 300)
    stale_meter_duration_s_range: tuple[int, int] = (3, 60)
    grid_outage_probability: float = 0.0
    grid_outage_start_s_range: tuple[int, int] = (30, 300)
    grid_outage_duration_s_range: tuple[int, int] = (60, 600)
    resend_query_time_s: float = 1.0  # assumption: seconds per <=300 s query
    operator_ack_delay_s: int = 60  # assumption
    reserve_floor_enforced: bool = False
    record_trace: bool = False
    seed_domain: str = "site"
    fail_on_run_ids: tuple[int, ...] = ()  # test hook: simulated worker failure

    def draw(self, master_seed: int, run_index: int) -> RunSpec:
        lim = load_site_limits()
        rng = run_rng(master_seed, self.seed_domain, run_index)
        initial_soc = _uniform(rng, self.initial_soc_pct_range)
        pv_peak = _uniform(rng, self.pv_peak_w_range)
        def_phase = rng.random() * self.def_period_s
        out_start = _uniform_int(rng, self.link_outage_start_s_range)
        out_len = _uniform_int(rng, self.link_outage_duration_s_range)
        detect = _uniform_int(rng, self.link_detect_delay_s_range)
        delays = [draw_resend_delay_s(rng)]
        link_down = [(out_start, out_start + out_len)]
        if rng.random() < self.second_outage_probability:
            gap = _uniform_int(rng, self.second_outage_gap_s_range)
            length = _uniform_int(rng, self.second_outage_duration_s_range)
            start2 = out_start + out_len + gap
            link_down.append((start2, start2 + length))
            delays.append(draw_resend_delay_s(rng))
        stale = []
        if rng.random() < self.stale_meter_probability:
            start = _uniform_int(rng, self.stale_meter_start_s_range)
            length = _uniform_int(rng, self.stale_meter_duration_s_range)
            stale.append((start, start + length))
        grid_down = []
        if rng.random() < self.grid_outage_probability:
            start = _uniform_int(rng, self.grid_outage_start_s_range)
            length = _uniform_int(rng, self.grid_outage_duration_s_range)
            grid_down.append((start, start + length))

        crit_w = lim.crit_load_w if self.crit_load_w is None else self.crit_load_w
        def_w = lim.def_load_w if self.def_load_w is None else self.def_load_w
        if self.pv_kind == "constant":
            pv = Profile("constant", base_w=pv_peak)
        else:
            pv = Profile(self.pv_kind, amplitude_w=pv_peak, period_s=self.pv_period_s)
        if self.def_kind == "square":
            deferrable = Profile("square", base_w=0.0, amplitude_w=def_w, period_s=self.def_period_s, phase_s=def_phase)
        else:
            deferrable = Profile("constant", base_w=def_w)
        return RunSpec(
            duration_s=self.duration_s,
            pv=pv,
            crit=Profile("constant", base_w=crit_w),
            deferrable=deferrable,
            initial_soc_pct=initial_soc,
            link_down_intervals_s=tuple(link_down),
            grid_down_intervals_s=tuple(grid_down),
            stale_meter_intervals_s=tuple(stale),
            resend_delays_s=tuple(delays),
            resend_query_time_s=self.resend_query_time_s,
            resend_query_span_s=RESEND_QUERY_SPAN_S,
            resend_gap_buffer_s=RESEND_GAP_BUFFER_S,
            link_detect_delay_s=detect,
            operator_ack_delay_s=self.operator_ack_delay_s,
            reserve_floor_enforced=self.reserve_floor_enforced,
            record_trace=self.record_trace,
        )

    def run(self, master_seed: int, run_index: int) -> dict:
        if run_index in self.fail_on_run_ids:
            raise RuntimeError(f"simulated worker failure at run {run_index}")
        spec = self.draw(master_seed, run_index)
        result = simulate(spec)
        result["run_id"] = run_index
        result["master_seed"] = master_seed
        result["scenario"] = self.name
        result["inputs"] = {
            "initial_soc_pct": spec.initial_soc_pct,
            "pv_peak_w": spec.pv.base_w if spec.pv.kind == "constant" else spec.pv.amplitude_w,
            "link_down_intervals_s": [list(x) for x in spec.link_down_intervals_s],
            "grid_down_intervals_s": [list(x) for x in spec.grid_down_intervals_s],
            "stale_meter_intervals_s": [list(x) for x in spec.stale_meter_intervals_s],
            "resend_delays_s": list(spec.resend_delays_s),
            "link_detect_delay_s": spec.link_detect_delay_s,
        }
        return result

    def without_failures(self) -> "SiteScenario":
        return replace(self, fail_on_run_ids=())


def fleet_resend_load(
    master_seed: int,
    n_sites: int,
    gap_s: float,
    query_time_s: float = 1.0,
    bin_s: int = 60,
    domain: str = "fleet",
) -> dict:
    """Backend resend load after one regional outage of ``gap_s`` seconds.

    Time 0 is the common reconnection instant. Site ``i`` draws its delay
    with ``run_rng(master_seed, domain, i)``. Returns per-bin counts of sites
    *starting* a resend and of sites *actively* resending (start to start +
    transfer), the peak concurrency and the delay extremes.
    """
    transfer_s = resend_transfer_s(gap_s, query_time_s)
    horizon_s = RESEND_DELAY_FIXED_S + RESEND_DELAY_RANDOM_MAX_S + transfer_s
    n_bins = int(math.ceil(horizon_s / bin_s)) + 1
    starts = [0] * n_bins
    active = [0] * n_bins
    delay_min = math.inf
    delay_max = -math.inf
    delay_sum = 0.0
    for site in range(n_sites):
        delay = draw_resend_delay_s(run_rng(master_seed, domain, site))
        delay_sum += delay
        if delay < delay_min:
            delay_min = delay
        if delay > delay_max:
            delay_max = delay
        first = int(delay // bin_s)
        last = int((delay + transfer_s) // bin_s)
        starts[first] += 1
        for b in range(first, min(last, n_bins - 1) + 1):
            active[b] += 1
    peak = max(active) if active else 0
    return {
        "n_sites": n_sites,
        "gap_s": gap_s,
        "transfer_s": transfer_s,
        "bin_s": bin_s,
        "starts_per_bin": starts,
        "active_per_bin": active,
        "peak_active": peak,
        "peak_active_bin": active.index(peak) if active else None,
        "resend_delay_min_s": delay_min if n_sites else None,
        "resend_delay_max_s": delay_max if n_sites else None,
        "resend_delay_mean_s": delay_sum / n_sites if n_sites else None,
    }


@dataclass(frozen=True)
class FleetScenario:
    """Monte Carlo over fleet realisations; run_index selects the realisation."""

    name: str = "fleet-default"
    n_sites: int = 500
    gap_s: float = 1800.0
    query_time_s: float = 1.0
    bin_s: int = 60
    seed_domain: str = "fleet"
    fail_on_run_ids: tuple[int, ...] = ()
    extra: dict = field(default_factory=dict)

    def run(self, master_seed: int, run_index: int) -> dict:
        if run_index in self.fail_on_run_ids:
            raise RuntimeError(f"simulated worker failure at run {run_index}")
        result = fleet_resend_load(
            master_seed,
            self.n_sites,
            self.gap_s,
            self.query_time_s,
            self.bin_s,
            domain=f"{self.seed_domain}/{run_index}",
        )
        result["run_id"] = run_index
        result["master_seed"] = master_seed
        result["scenario"] = self.name
        return result

    def without_failures(self) -> "FleetScenario":
        return replace(self, fail_on_run_ids=())
