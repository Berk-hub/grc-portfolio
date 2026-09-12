"""Site limits read from the repository data files.

Every number the model needs comes from ``data/measurement-dictionary.json``
(physical channel bounds, power limits, capacity, balance tolerance) or
``data/service-model.json`` (reserve floor, hysteresis, load split,
thresholds, backfill window). The code carries no copies of those values;
tests assert that the loaded limits agree with the files.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[3] / "data"
DICTIONARY_PATH = DATA_DIR / "measurement-dictionary.json"
SERVICE_MODEL_PATH = DATA_DIR / "service-model.json"


@dataclass(frozen=True)
class SiteLimits:
    """Numbers used by the model; units in the field names."""

    ess_capacity_wh: float
    ess_max_charge_w: float
    ess_max_discharge_w: float
    soc_physical_min_pct: float
    soc_physical_max_pct: float
    reserve_floor_pct: float
    reserve_hysteresis_pct: float
    balance_tolerance_w: float
    grid_setpoint_w: float
    initial_soc_pct: float
    crit_load_w: float
    def_load_w: float
    stale_after_power_s: int
    stale_after_soc_s: int
    meas_unreliable_hold_s: int
    consistent_cycles_to_exit: int
    backfill_window_s: int
    control_reaction_objective_s: int
    csf_window_s: int


_CACHE: dict[str, SiteLimits] = {}


def _limit(model: dict, limit_id: str) -> dict:
    for entry in model["limits"]:
        if entry["id"] == limit_id:
            return entry
    raise KeyError(limit_id)


def _load(model: dict, load_id: str) -> dict:
    for entry in model["loads"]:
        if entry["id"] == load_id:
            return entry
    raise KeyError(load_id)


def _stale_after(dictionary: dict, field: str) -> int:
    for channel in dictionary["channels"]:
        if channel.get("field") == field:
            return int(channel["stale_after_s"])
    raise KeyError(field)


def load_site_limits(data_dir: Path | None = None) -> SiteLimits:
    """Load and cache the limits. Loaded once per process (workers included)."""
    directory = Path(data_dir) if data_dir is not None else DATA_DIR
    key = str(directory)
    if key in _CACHE:
        return _CACHE[key]

    with (directory / "measurement-dictionary.json").open("r", encoding="utf-8") as handle:
        dictionary = json.load(handle)
    with (directory / "service-model.json").open("r", encoding="utf-8") as handle:
        model = json.load(handle)

    operating = dictionary["operating_limits"]
    facts = model["context"]["simulator_facts"]
    floor = _limit(model, "LIM-SOC-FLOOR")
    hysteresis = _limit(model, "LIM-SOC-HYST")
    recovery = model["data_loss_and_recovery"]
    # "two consecutive cycles fresh and consistent (assumption)" and
    # "held longer than 30 s (assumption)" are stated in the ST-MEAS-UNRELIABLE
    # exit text; the service model carries them as prose, so they are parsed
    # from the transition/state text here rather than duplicated.
    unreliable = next(s for s in model["states"] if s["id"] == "ST-MEAS-UNRELIABLE")
    hold_s = _parse_leading_int(unreliable["exit"], "held longer than ")
    consistent_cycles = 2 if "two consecutive" in unreliable["exit"] else _parse_leading_int(unreliable["exit"], "")
    crit = next(s for s in model["services"] if s["id"] == "SVC-CRIT-001")
    csf_window_s = _parse_leading_int(crit["minimum_service_level"]["statement"], "over any ")

    limits = SiteLimits(
        ess_capacity_wh=float(operating["ess_capacity_wh"]),
        ess_max_charge_w=float(operating["ess_max_charge_w"]),
        ess_max_discharge_w=float(operating["ess_max_discharge_w"]),
        soc_physical_min_pct=float(operating["soc_floor_pct"]),
        soc_physical_max_pct=float(operating["soc_ceiling_pct"]),
        reserve_floor_pct=float(floor["min"]),
        reserve_hysteresis_pct=float(hysteresis["value"]),
        balance_tolerance_w=float(dictionary["balance_tolerance_w"]),
        grid_setpoint_w=float(facts["grid_setpoint_w"]["value"]),
        initial_soc_pct=float(facts["ess_initial_soc_pct"]["value"]),
        crit_load_w=float(_load(model, "LOAD-CRIT-001")["power_w"]["value"]),
        def_load_w=float(_load(model, "LOAD-DEF-001")["power_w"]["value"]),
        stale_after_power_s=_stale_after(dictionary, "consumption_w"),
        stale_after_soc_s=_stale_after(dictionary, "ess_soc_pct"),
        meas_unreliable_hold_s=hold_s,
        consistent_cycles_to_exit=consistent_cycles,
        backfill_window_s=int(recovery["central_backfill_window_min"]["value"]) * 60,
        control_reaction_objective_s=int(recovery["control_reaction_objective_s"]["value"]),
        csf_window_s=csf_window_s,
    )
    _CACHE[key] = limits
    return limits


def _parse_leading_int(text: str, marker: str) -> int:
    position = text.index(marker) + len(marker)
    digits = ""
    for char in text[position:]:
        if char.isdigit():
            digits += char
        elif digits:
            break
    if not digits:
        raise ValueError(f"no integer after {marker!r} in {text!r}")
    return int(digits)
