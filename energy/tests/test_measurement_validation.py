import copy
import json
import tempfile
import unittest
from pathlib import Path

from energy_assurance.cli import (
    EvidenceError, assess_backend_loss, balanced, load_backend_loss_run,
    measurement_problems, ordered_timestamps, required_measurements,
)

ROOT = Path(__file__).resolve().parents[1]


class MeasurementValidationTests(unittest.TestCase):
    def setUp(self):
        _, self.run = load_backend_loss_run(ROOT)
        self.snapshot = copy.deepcopy(self.run['outage_discharge'])

    def test_rejects_invalid_channel_values(self):
        for field in ('consumption_w', 'production_w', 'ess_w', 'grid_w', 'ess_soc_pct'):
            for value in (None, True, '100', float('nan'), float('inf'), -float('inf')):
                with self.subTest(field=field, value=value):
                    snapshot = dict(self.snapshot, **{field: value})
                    self.assertFalse(required_measurements(snapshot))
                    self.assertFalse(balanced(snapshot))

    def test_documented_physical_limits(self):
        for field, value in (
            ('consumption_w', -1), ('production_w', -1),
            ('ess_soc_pct', 900), ('ess_soc_pct', -1),
            ('ess_w', 10001), ('ess_w', -10001),
        ):
            with self.subTest(field=field, value=value):
                snapshot = dict(self.snapshot, **{field: value})
                self.assertFalse(required_measurements(snapshot))
                problems = measurement_problems(snapshot)
                self.assertEqual(len(problems), 1)
                self.assertIn(field, problems[0])

    def test_forged_residual_cannot_hide_unbalanced_load(self):
        self.snapshot['consumption_w'] = 10**12
        self.snapshot['power_balance_residual_w'] = 0
        self.assertFalse(balanced(self.snapshot))

    def test_positive_grid_import_supplies_load(self):
        # +40 W import balances a 40 W supply deficit. Opposite sign would
        # produce an 80 W residual and fail the 50 W consistency tolerance.
        self.snapshot.update(consumption_w=5240, grid_w=40)
        self.assertTrue(balanced(self.snapshot))
        self.snapshot['grid_w'] = -40
        self.assertFalse(balanced(self.snapshot))

    def _assess_with(self, field, value, evaluator="v2"):
        with tempfile.TemporaryDirectory() as tmp:
            run = copy.deepcopy(self.run)
            run['outage_discharge'][field] = value
            root = Path(tmp)
            evidence = root / 'evidence/backend-loss'
            evidence.mkdir(parents=True)
            (evidence / '11-final-reconciliation-run.json').write_text(json.dumps(run))
            return assess_backend_loss(root, evaluator=evaluator)

    def test_out_of_range_inputs_produce_failed_assessment_without_crashing(self):
        for field, value, failing in (
            ('ess_soc_pct', 900, 'SC-01'),
            ('consumption_w', 10**12, 'SC-02'),
        ):
            for evaluator in ("v1", "v2"):
                with self.subTest(field=field, evaluator=evaluator):
                    result = self._assess_with(field, value, evaluator)
                    self.assertEqual(result['overall_result'], 'NOT SUPPORTED')
                    self.assertEqual(result['criteria'][failing], 'NOT SUPPORTED')
                    self.assertNotEqual(result['criteria']['SC-03'], 'SUPPORTED')

    def test_malformed_inputs_are_evidence_errors(self):
        # Wrong type, boolean and null are schema problems: the assessment
        # refuses to run rather than reporting a criterion result.
        for field, value in (('ess_w', 'bad'), ('grid_w', True), ('ess_soc_pct', None)):
            with self.subTest(field=field, value=value):
                with self.assertRaises(EvidenceError):
                    self._assess_with(field, value)


class TimestampValidationTests(unittest.TestCase):
    def test_requires_strict_aware_order(self):
        for times in (
            [], ['2026-09-08T12:00:00Z'],
            ['2026-09-08T12:00:00Z', '2026-09-08T12:00:00Z'],
            ['2026-09-08T12:00:01Z', '2026-09-08T12:00:00Z'],
            ['2026-09-08T12:00:00', '2026-09-08T12:00:01Z'],
            [100, '2026-09-08T12:00:01Z'],
        ):
            with self.subTest(times=times):
                self.assertFalse(ordered_timestamps([{'captured_at_utc': t} for t in times]))
        self.assertTrue(ordered_timestamps([
            {'captured_at_utc': '2026-09-08T12:00:00Z'},
            {'captured_at_utc': '2026-09-08T13:00:01+01:00'},
        ]))


if __name__ == '__main__':
    unittest.main()
