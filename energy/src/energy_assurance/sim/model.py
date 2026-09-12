"""Deterministic 1 Hz discrete-time model of the reference site.

What is modelled
----------------
* PV production, a critical load and a deferrable load, each as a
  parameterised profile evaluated once per cycle (``Profile``).
* A balancing controller that targets grid power 0 W (``grid_setpoint_w``)
  by requesting ESS power equal to the *measured* consumption minus PV.
  The ESS is clamped to the power limits and to the physical SoC bounds of
  ``data/measurement-dictionary.json`` (0 to 100 %). The 40 % reserve floor
  of ``LIM-SOC-FLOOR`` is a classification rule by default
  (``reserve_floor_enforced=False``); with the flag set, the controller
  holds the floor while the grid is available and non-zero grid import is
  the expected outcome (ST-CAP-LIMIT), while off-grid the reserve serves
  the load.
* The SoC equation of the service model:
  ``SoC(t+dt) = SoC(t) - 100 * (P_ess * dt / 3600) / C``.
* Grid outage (DEP-ELEC): grid power is 0; the ESS is the only balance. A
  shortfall sheds the deferrable load first and the critical load last; a
  surplus curtails PV. Power balance ``P_prod + P_ess + P_grid - P_cons``
  is exactly zero in every cycle by construction (tested).
* Backend link outage (DEP-NET) with a detection delay (UnableToSend rises
  ``link_detect_delay_s`` cycles after the link drops), a resend schedule
  drawn per reconnection (``resend_delays_s`` are supplied by the scenario,
  300 s + U[0, 3600) s per docs/13-sc06-root-cause.md), a transfer time of
  one query per 300 s span of gap and the 66 min backfill window.
* A stale consumption meter fault: the reported consumption freezes, its
  age grows, and the controller acts on the frozen value.
* The service-model states with the priority rule: ST-SAFE-CURTAIL (1),
  ST-MEAS-UNRELIABLE (2), ST-CAP-LIMIT (3), ST-CENTRAL-LOST (4),
  ST-RECOVERY (5), ST-NORMAL (6). The lowest number is reported; the
  others are kept as concurrent flags. ST-SAFE-CURTAIL sets the deferrable
  load to 0 W from the next cycle (curtail latency one cycle).
* KPIs: KPI-CSF-001 (whole run and minimum over any 60 s window),
  KPI-ENS-001, KPI-LIM-001/002, KPI-TRL-001 per transition, KPI-REC-001
  per reconnection, KPI-SOC-001 at the end of the run.

What is NOT modelled (state these when reporting results)
---------------------------------------------------------
* Charge and discharge efficiency (100 %), inverter ramp rate, apparent
  power and reactive power.
* BMS protection, temperature, ageing; the physical 0 and 100 % bounds are
  the only energy limits.
* Grid protection, islanding transients, the fuse limit LIM-GRID-IMPORT
  (recorded but not enforced by any controller), phase imbalance.
* Controller latency other than the one-cycle curtailment; the balancing
  request is met within the same cycle.
* Backend transfer failures other than the timeout; RRD4J gaps; clock
  error (all channels share the model clock, as in the laboratory).
* Operator behaviour beyond a fixed acknowledgement delay.
* Any physical claim: this reproduces the *classification rules* of
  docs/18-service-model.md applied to a simulator-like time series.

Units are in the names: ``_w`` W, ``_wh`` Wh, ``_s`` s, ``_pct`` %.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .limits import SiteLimits, load_site_limits

ST_SAFE_CURTAIL = "ST-SAFE-CURTAIL"
ST_MEAS_UNRELIABLE = "ST-MEAS-UNRELIABLE"
ST_CAP_LIMIT = "ST-CAP-LIMIT"
ST_CENTRAL_LOST = "ST-CENTRAL-LOST"
ST_RECOVERY = "ST-RECOVERY"
ST_NORMAL = "ST-NORMAL"

STATE_PRIORITY = {
    ST_SAFE_CURTAIL: 1,
    ST_MEAS_UNRELIABLE: 2,
    ST_CAP_LIMIT: 3,
    ST_CENTRAL_LOST: 4,
    ST_RECOVERY: 5,
    ST_NORMAL: 6,
}

# Transition ids of data/service-model.json keyed by (from, to).
TRANSITION_IDS = {
    (ST_NORMAL, ST_CENTRAL_LOST): "TR-01",
    (ST_CENTRAL_LOST, ST_RECOVERY): "TR-02",
    (ST_RECOVERY, ST_NORMAL): "TR-03",
    (ST_NORMAL, ST_MEAS_UNRELIABLE): "TR-04",
    (ST_MEAS_UNRELIABLE, ST_NORMAL): "TR-05",
    (ST_NORMAL, ST_CAP_LIMIT): "TR-06",
    (ST_CAP_LIMIT, ST_NORMAL): "TR-07",
    (ST_CAP_LIMIT, ST_SAFE_CURTAIL): "TR-08",
    (ST_MEAS_UNRELIABLE, ST_SAFE_CURTAIL): "TR-09",
    (ST_SAFE_CURTAIL, ST_RECOVERY): "TR-10",
    (ST_CENTRAL_LOST, ST_CAP_LIMIT): "TR-11",
}


@dataclass(frozen=True)
class Profile:
    """Power profile in W evaluated at cycle time ``t_s``.

    kind: "constant" -> base_w
          "sine"     -> base_w + amplitude_w * sin(2*pi*(t+phase_s)/period_s)
          "square"   -> base_w + amplitude_w in the first half of each period
          "halfsine" -> amplitude_w * max(0, sin(pi*(t+phase_s)/period_s)),
                        a daylight-shaped PV curve with period_s = day length
    Values are clipped at 0 W.
    """

    kind: str = "constant"
    base_w: float = 0.0
    amplitude_w: float = 0.0
    period_s: float = 86400.0
    phase_s: float = 0.0

    def values(self, steps: int, dt_s: float) -> list[float]:
        kind = self.kind
        base = self.base_w
        amp = self.amplitude_w
        period = self.period_s
        phase = self.phase_s
        if kind == "constant":
            return [max(0.0, base)] * steps
        if kind == "sine":
            two_pi = 2.0 * math.pi
            return [max(0.0, base + amp * math.sin(two_pi * (i * dt_s + phase) / period)) for i in range(steps)]
        if kind == "square":
            half = period / 2.0
            return [max(0.0, base + (amp if ((i * dt_s + phase) % period) < half else 0.0)) for i in range(steps)]
        if kind == "halfsine":
            return [max(0.0, amp * math.sin(math.pi * (((i * dt_s + phase) % (2.0 * period)) / period))) for i in range(steps)]
        raise ValueError(f"unknown profile kind {kind!r}")


@dataclass(frozen=True)
class RunSpec:
    """Concrete, fully determined inputs for one simulation run."""

    duration_s: int
    pv: Profile
    crit: Profile
    deferrable: Profile
    initial_soc_pct: float
    link_down_intervals_s: tuple[tuple[int, int], ...] = ()
    grid_down_intervals_s: tuple[tuple[int, int], ...] = ()
    stale_meter_intervals_s: tuple[tuple[int, int], ...] = ()
    resend_delays_s: tuple[float, ...] = ()
    resend_query_time_s: float = 1.0
    resend_query_span_s: int = 300
    resend_gap_buffer_s: int = 300
    link_detect_delay_s: int = 1
    operator_ack_delay_s: int = 60
    reserve_floor_enforced: bool = False
    dt_s: int = 1
    record_trace: bool = False
    extra: dict = field(default_factory=dict)


def _interval_mask(intervals, steps: int, dt_s: int) -> list[bool]:
    mask = [False] * steps
    for start, end in intervals:
        lo = max(0, int(start // dt_s))
        hi = min(steps, int(math.ceil(end / dt_s)))
        for i in range(lo, hi):
            mask[i] = True
    return mask


def simulate(spec: RunSpec, limits: SiteLimits | None = None) -> dict:
    """Run the model and return a JSON-serialisable result dictionary."""
    lim = limits if limits is not None else load_site_limits()
    dt = spec.dt_s
    steps = int(spec.duration_s // dt)
    cap_wh = lim.ess_capacity_wh
    max_chg_w = lim.ess_max_charge_w
    max_dis_w = lim.ess_max_discharge_w
    soc_min = lim.soc_physical_min_pct
    soc_max = lim.soc_physical_max_pct
    floor = lim.reserve_floor_pct
    hyst = lim.reserve_hysteresis_pct
    tol_w = lim.balance_tolerance_w
    setpoint_w = lim.grid_setpoint_w
    stale_power_s = lim.stale_after_power_s
    hold_s = lim.meas_unreliable_hold_s
    consistent_needed = lim.consistent_cycles_to_exit
    backfill_window_s = lim.backfill_window_s
    csf_window = lim.csf_window_s
    # W per 1 % of SoC over one cycle: (1/100) * C * 3600 / dt
    w_per_pct = cap_wh * 36.0 / dt
    pct_per_w = 1.0 / w_per_pct
    dt_h = dt / 3600.0

    pv_w = spec.pv.values(steps, dt)
    crit_w = spec.crit.values(steps, dt)
    def_w = spec.deferrable.values(steps, dt)
    link_down = _interval_mask(spec.link_down_intervals_s, steps, dt)
    grid_down = _interval_mask(spec.grid_down_intervals_s, steps, dt)
    stale = _interval_mask(spec.stale_meter_intervals_s, steps, dt)
    resend_delays = list(spec.resend_delays_s)
    ack_delay = spec.operator_ack_delay_s
    detect_delay = spec.link_detect_delay_s
    query_time = spec.resend_query_time_s
    query_span = spec.resend_query_span_s
    gap_buffer = spec.resend_gap_buffer_s
    reserve_enforced = spec.reserve_floor_enforced

    soc = float(spec.initial_soc_pct)
    if not (soc_min <= soc <= soc_max):
        raise ValueError("initial SoC outside physical bounds")

    # --- latched classification state ---
    curtail_active = False
    curtail_applied = False  # takes effect one cycle after the state
    curtail_cleared_for = 0
    unreliable = False
    unreliable_since = -1
    consistent_count = 0
    cap_active = False
    cap_reason = ""
    recovery_active = False
    recovery_entered_at = -1
    backfill_pending = False
    resend_done_at = -1.0
    backfill_deadline = -1
    recovery_start = -1
    link_down_age = 0
    link_down_since = -1
    prev_link_up = True
    frozen_cons_w = 0.0
    freeze_start = -1
    prev_state = ST_NORMAL
    prev_cons_w = 0.0

    # --- accumulators ---
    ens_wh = 0.0
    crit_demand_wh = 0.0
    def_curtailed_wh = 0.0
    pv_curtailed_wh = 0.0
    grid_import_wh = 0.0
    grid_export_wh = 0.0
    ess_discharge_wh = 0.0
    ess_charge_wh = 0.0
    soc_lo = soc
    soc_hi = soc
    residual_max_abs_w = 0.0
    viol_grid = 0
    viol_ess = 0
    viol_floor = 0
    viol_samples = 0
    state_time = {name: 0 for name in STATE_PRIORITY}
    flag_time = {name: 0 for name in STATE_PRIORITY}
    transitions: list[list] = []
    latency: dict[str, list[int]] = {}
    reconnections: list[dict] = []
    shortfall_per_step: list[float] = []
    any_shortfall = False
    trace = [] if spec.record_trace else None
    outage_index = -1

    for i in range(steps):
        t = i * dt
        link_up = not link_down[i]
        grid_avail = not grid_down[i]
        frozen = stale[i]

        # ---- backend link detection and resend scheduling ----
        if link_up:
            if not prev_link_up:
                # reconnection: schedule resend for the gap just closed
                outage_index += 1
                if outage_index < len(resend_delays):
                    delay = float(resend_delays[outage_index])
                else:
                    raise ValueError("scenario supplied fewer resend delays than reconnections")
                gap_s = t - link_down_since
                n_queries = int(math.ceil((gap_s + gap_buffer) / query_span))
                transfer_s = n_queries * query_time
                resend_done_at = t + delay + transfer_s
                backfill_deadline = t + backfill_window_s
                backfill_pending = True
                recovery_start = t
                recovery_active = True
                recovery_entered_at = t
                reconnections.append({
                    "reconnected_at_s": t,
                    "gap_s": gap_s,
                    "resend_delay_s": delay,
                    "resend_scheduled_at_s": t + delay,
                    "resend_queries": n_queries,
                    "transfer_s": transfer_s,
                    "resend_done_at_s": None,
                    "recovery_time_s": None,
                    "timed_out": False,
                    "cancelled": False,
                })
            link_down_age = 0
            link_detected_down = False
        else:
            if prev_link_up:
                link_down_since = t
                if backfill_pending:
                    backfill_pending = False
                    reconnections[-1]["cancelled"] = True
            link_down_age += 1
            link_detected_down = link_down_age > detect_delay
        prev_link_up = link_up

        if backfill_pending:
            if t >= resend_done_at:
                backfill_pending = False
                record = reconnections[-1]
                record["resend_done_at_s"] = t
                record["recovery_time_s"] = t - recovery_start
            elif t >= backfill_deadline:
                backfill_pending = False
                reconnections[-1]["timed_out"] = True

        # ---- loads and controller ----
        crit_demand = crit_w[i]
        def_demand = def_w[i]
        pv = pv_w[i]
        def_request = 0.0 if curtail_applied else def_demand
        cons_true = crit_demand + def_request
        if frozen:
            if freeze_start < 0:
                freeze_start = t
                frozen_cons_w = prev_cons_w
            cons_meas = frozen_cons_w
            cons_age = t - freeze_start
        else:
            freeze_start = -1
            cons_meas = cons_true
            cons_age = 0

        if grid_avail:
            ess_req = cons_meas - pv - setpoint_w
        else:
            ess_req = cons_true - pv

        ess = ess_req
        if ess > max_dis_w:
            ess = max_dis_w
        elif ess < -max_chg_w:
            ess = -max_chg_w
        energy_floor = floor if (reserve_enforced and grid_avail) else soc_min
        dis_cap_w = (soc - energy_floor) * w_per_pct
        if dis_cap_w < 0.0:
            dis_cap_w = 0.0
        chg_cap_w = (soc_max - soc) * w_per_pct
        if chg_cap_w < 0.0:
            chg_cap_w = 0.0
        if ess > dis_cap_w:
            ess = dis_cap_w
        elif ess < -chg_cap_w:
            ess = -chg_cap_w

        crit_served = crit_demand
        def_served = def_request
        pv_used = pv
        if grid_avail:
            grid = cons_true - pv - ess
        else:
            grid = 0.0
            balance = pv + ess - cons_true
            if balance < 0.0:
                shortfall = -balance
                shed_def = def_request if def_request < shortfall else shortfall
                def_served = def_request - shed_def
                shortfall -= shed_def
                crit_served = crit_demand - shortfall
                if crit_served < 0.0:
                    crit_served = 0.0
            elif balance > 0.0:
                pv_used = pv - balance
        cons_served = crit_served + def_served
        residual_true = pv_used + ess + grid - cons_served
        residual_meas = pv_used + ess + grid - (cons_meas if frozen else cons_served)
        prev_cons_w = cons_served

        # ---- energy bookkeeping ----
        short_w = crit_demand - crit_served
        if short_w > 0.0:
            any_shortfall = True
            ens_wh += short_w * dt_h
        shortfall_per_step.append(short_w)
        crit_demand_wh += crit_demand * dt_h
        def_curtailed_wh += (def_demand - def_served) * dt_h
        pv_curtailed_wh += (pv - pv_used) * dt_h
        if grid > 0.0:
            grid_import_wh += grid * dt_h
        else:
            grid_export_wh -= grid * dt_h
        if ess > 0.0:
            ess_discharge_wh += ess * dt_h
        else:
            ess_charge_wh -= ess * dt_h
        abs_res = residual_true if residual_true >= 0.0 else -residual_true
        if abs_res > residual_max_abs_w:
            residual_max_abs_w = abs_res

        # ---- classification (on this cycle's measured values) ----
        soc_meas = soc
        stale_now = cons_age > stale_power_s
        abs_res_meas = residual_meas if residual_meas >= 0.0 else -residual_meas
        bounds_ok = soc_min <= soc_meas <= soc_max and -max_chg_w <= ess <= max_dis_w
        consistent = (not stale_now) and abs_res_meas <= tol_w and bounds_ok
        if not consistent:
            if not unreliable:
                unreliable = True
                unreliable_since = t
            consistent_count = 0
        elif unreliable:
            consistent_count += 1
            if consistent_count >= consistent_needed:
                unreliable = False
                consistent_count = 0

        cap_cond_floor = soc_meas <= floor and ess_req > 0.0
        cap_cond_ceiling = soc_meas >= soc_max and ess_req < 0.0
        cap_cond_power = ess_req > max_dis_w or ess_req < -max_chg_w
        if cap_cond_floor or cap_cond_ceiling or cap_cond_power:
            if not cap_active:
                cap_active = True
            cap_reason = "floor" if cap_cond_floor else ("ceiling" if cap_cond_ceiling else "power")
        elif cap_active:
            if cap_reason == "floor":
                if soc_meas > floor + hyst:
                    cap_active = False
            elif cap_reason == "ceiling":
                if soc_meas < soc_max - hyst:
                    cap_active = False
            else:
                cap_active = False

        curtail_cond = (cap_active and not grid_avail) or (unreliable and (t - unreliable_since) > hold_s)
        if curtail_cond:
            curtail_active = True
            curtail_cleared_for = 0
        elif curtail_active:
            curtail_cleared_for += dt
            if curtail_cleared_for >= ack_delay:
                curtail_active = False
                recovery_active = True
                recovery_entered_at = t

        if recovery_active and not backfill_pending and t > recovery_entered_at:
            recovery_active = False

        if curtail_active:
            state = ST_SAFE_CURTAIL
        elif unreliable:
            state = ST_MEAS_UNRELIABLE
        elif cap_active:
            state = ST_CAP_LIMIT
        elif link_detected_down:
            state = ST_CENTRAL_LOST
        elif recovery_active:
            state = ST_RECOVERY
        else:
            state = ST_NORMAL
        state_time[state] += dt
        if unreliable and state != ST_MEAS_UNRELIABLE:
            flag_time[ST_MEAS_UNRELIABLE] += dt
        if cap_active and state != ST_CAP_LIMIT:
            flag_time[ST_CAP_LIMIT] += dt
        if link_detected_down and state != ST_CENTRAL_LOST:
            flag_time[ST_CENTRAL_LOST] += dt
        if recovery_active and state != ST_RECOVERY:
            flag_time[ST_RECOVERY] += dt

        if state != prev_state:
            transition_id = TRANSITION_IDS.get((prev_state, state), f"{prev_state}->{state}")
            transitions.append([t, prev_state, state, transition_id])
            if state == ST_CENTRAL_LOST:
                lat = t - link_down_since
            else:
                lat = 0
            latency.setdefault(transition_id, []).append(lat)
            prev_state = state

        # ---- limit violations (KPI-LIM-001) ----
        violated = False
        if grid_avail and not cap_active:
            dev = grid - setpoint_w
            if dev > tol_w or dev < -tol_w:
                viol_grid += 1
                violated = True
        if ess > max_dis_w or ess < -max_chg_w:
            viol_ess += 1
            violated = True
        if soc_meas < floor and not cap_active:
            viol_floor += 1
            violated = True
        if violated:
            viol_samples += 1

        if trace is not None:
            trace.append({
                "t_s": t,
                "production_w": pv_used,
                "consumption_w": cons_served,
                "consumption_measured_w": cons_meas,
                "ess_w": ess,
                "grid_w": grid,
                "ess_soc_pct": soc_meas,
                "crit_served_w": crit_served,
                "def_served_w": def_served,
                "residual_w": residual_true,
                "state": state,
                "link_up": link_up,
                "grid_available": grid_avail,
            })

        # ---- SoC update (service-model equation) ----
        soc = soc - ess * pct_per_w
        if soc < soc_min:
            if soc_min - soc > 1e-9:
                raise AssertionError("SoC fell below the physical floor")
            soc = soc_min
        elif soc > soc_max:
            if soc - soc_max > 1e-9:
                raise AssertionError("SoC rose above the physical ceiling")
            soc = soc_max
        if soc < soc_lo:
            soc_lo = soc
        elif soc > soc_hi:
            soc_hi = soc
        curtail_applied = curtail_active

    csf_ratio = 1.0 - ens_wh / crit_demand_wh if crit_demand_wh > 0.0 else 1.0
    csf_min_window = 1.0
    if any_shortfall:
        csf_min_window = _min_window_csf(shortfall_per_step, crit_w, csf_window, dt)

    recovery_times = [r["recovery_time_s"] for r in reconnections if r["recovery_time_s"] is not None]
    result = {
        "duration_s": steps * dt,
        "dt_s": dt,
        "soc_initial_pct": float(spec.initial_soc_pct),
        "soc_final_pct": soc,
        "soc_min_pct": soc_lo,
        "soc_max_pct": soc_hi,
        "reserve_margin_final_wh": (soc - floor) / 100.0 * cap_wh,
        "ens_wh": ens_wh,
        "crit_demand_wh": crit_demand_wh,
        "csf_ratio": csf_ratio,
        "csf_min_window_ratio": csf_min_window,
        "csf_window_s": csf_window,
        "def_curtailed_wh": def_curtailed_wh,
        "pv_curtailed_wh": pv_curtailed_wh,
        "grid_import_wh": grid_import_wh,
        "grid_export_wh": grid_export_wh,
        "ess_discharge_wh": ess_discharge_wh,
        "ess_charge_wh": ess_charge_wh,
        "residual_max_abs_w": residual_max_abs_w,
        "limit_violations": {
            "grid_balance": viol_grid,
            "ess_power": viol_ess,
            "soc_floor": viol_floor,
            "samples": viol_samples,
        },
        "limit_violation_s": viol_samples * dt,
        "state_time_s": state_time,
        "flag_time_s": flag_time,
        "transitions": transitions,
        "transition_count": len(transitions),
        "transition_latency_s": latency,
        "reconnections": reconnections,
        "recovery_time_s": recovery_times,
        "recovery_timeouts": sum(1 for r in reconnections if r["timed_out"]),
        "recovery_cancelled": sum(1 for r in reconnections if r["cancelled"]),
        "final_state": prev_state,
    }
    if trace is not None:
        result["trace"] = trace
    return result


def _min_window_csf(shortfall_w: list[float], demand_w: list[float], window_s: int, dt: int) -> float:
    """Minimum critical-service fulfilment ratio over any window of window_s."""
    n = len(shortfall_w)
    width = max(1, int(window_s // dt))
    if n == 0:
        return 1.0
    width = min(width, n)
    short_sum = sum(shortfall_w[:width])
    demand_sum = sum(demand_w[:width])
    best = 1.0 - short_sum / demand_sum if demand_sum > 0 else 1.0
    for i in range(width, n):
        short_sum += shortfall_w[i] - shortfall_w[i - width]
        demand_sum += demand_w[i] - demand_w[i - width]
        ratio = 1.0 - short_sum / demand_sum if demand_sum > 0 else 1.0
        if ratio < best:
            best = ratio
    return max(0.0, best)
