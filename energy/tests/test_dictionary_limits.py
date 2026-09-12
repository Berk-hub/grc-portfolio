"""The measurement dictionary is the only place limits are written down."""
import json
import re
import unittest
from pathlib import Path

from energy_assurance.cli import (
    DICTIONARY_PATH, balance_tolerance_w, channel_limits, operating_limits,
    required_fields, validation_rules,
)

ROOT = Path(__file__).resolve().parents[1]


class DictionaryLimitTests(unittest.TestCase):
    def test_dictionary_path_is_the_repository_file(self):
        self.assertEqual(DICTIONARY_PATH, ROOT / "data/measurement-dictionary.json")

    def test_every_required_field_has_unit_and_finite_flag(self):
        limits = channel_limits()
        self.assertEqual(
            set(required_fields()),
            {"consumption_w", "production_w", "ess_w", "grid_w", "ess_soc_pct"},
        )
        for field, channel in limits.items():
            self.assertIn(channel["unit"], ("W", "%"), field)
            self.assertTrue(channel["finite"], field)
            self.assertIn("stale_after_s", channel, field)

    def test_channel_limits_agree_with_operating_limits(self):
        limits = channel_limits()
        operating = operating_limits()
        self.assertEqual(limits["ess_w"]["min"], -operating["ess_max_charge_w"])
        self.assertEqual(limits["ess_w"]["max"], operating["ess_max_discharge_w"])
        self.assertEqual(limits["ess_soc_pct"]["min"], operating["soc_floor_pct"])
        self.assertEqual(limits["ess_soc_pct"]["max"], operating["soc_ceiling_pct"])

    def test_tolerances_are_positive_and_consistent(self):
        rules = validation_rules()
        self.assertGreater(balance_tolerance_w(), 0)
        self.assertGreaterEqual(rules["transition_tolerance_w"], balance_tolerance_w())
        self.assertGreater(rules["max_gap_s"], 0)

    def test_cli_source_carries_no_numeric_limit_copies(self):
        source = (ROOT / "src/energy_assurance/cli.py").read_text(encoding="utf-8")
        # Former hard-coded copies: +-10 kW ESS range, 50 W tolerance,
        # 0..100 % SOC. Any numeric literal beside a channel field name is
        # a copy of a dictionary value.
        for literal in ("10000", "10200", "tolerance=50", "<= 100", "= 50"):
            self.assertNotIn(literal, source, literal)
        for field in ("consumption_w", "production_w", "ess_w", "grid_w", "ess_soc_pct"):
            # Comparisons against 0 are sign checks, not limits.
            pattern = rf'\["{field}"\]\s*(<=|>=|<|>)\s*-?[1-9]'
            self.assertIsNone(re.search(pattern, source), field)

    def test_dictionary_json_is_well_formed(self):
        document = json.loads(DICTIONARY_PATH.read_text(encoding="utf-8"))
        self.assertIn("time_semantics", document)
        self.assertIn("freshness_rule", document["time_semantics"])
        self.assertIn("clock_uncertainty_s", document["time_semantics"])


if __name__ == "__main__":
    unittest.main()
