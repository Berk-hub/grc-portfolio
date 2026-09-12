"""Malformed evidence must raise EvidenceError, never produce a result."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from energy_assurance.cli import (
    EvidenceError, assess_backend_loss, freshness_error, load_jsonl,
    load_strict_json, validate_state_trace,
)

from evidence_fixtures import (
    BASELINE, consistent_trace, recorded_run, sample, utc, v2_run,
    write_evidence,
)


class RunFileSchemaTests(unittest.TestCase):
    def assess(self, text):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = root / "evidence/backend-loss"
            evidence.mkdir(parents=True)
            (evidence / "11-final-reconciliation-run.json").write_text(text, encoding="utf-8")
            return assess_backend_loss(root)

    def test_broken_json(self):
        with self.assertRaises(EvidenceError):
            self.assess("{\n  \"phases\": ")

    def test_list_instead_of_object(self):
        with self.assertRaises(EvidenceError):
            self.assess(json.dumps([recorded_run()]))

    def test_missing_phase(self):
        run = recorded_run()
        del run["outage_charge"]
        with self.assertRaises(EvidenceError) as ctx:
            self.assess(json.dumps(run))
        self.assertIn("outage_charge", str(ctx.exception))

    def test_missing_field(self):
        run = recorded_run()
        del run["recovery"]["grid_w"]
        with self.assertRaises(EvidenceError) as ctx:
            self.assess(json.dumps(run))
        self.assertIn("grid_w", str(ctx.exception))

    def test_nan_literal_is_rejected_at_parse_time(self):
        run = recorded_run()
        text = json.dumps(run).replace('"ess_w": 4500', '"ess_w": NaN')
        self.assertIn("NaN", text)
        with self.assertRaises(EvidenceError):
            self.assess(text)

    def test_boolean_measurement(self):
        run = recorded_run()
        run["outage_discharge"]["grid_w"] = False
        with self.assertRaises(EvidenceError):
            self.assess(json.dumps(run))

    def test_unknown_format_number(self):
        run = recorded_run()
        run["evidence_format"] = 3
        with self.assertRaises(EvidenceError):
            self.assess(json.dumps(run))

    def test_missing_run_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(EvidenceError):
                assess_backend_loss(Path(tmp))


class JsonlTests(unittest.TestCase):
    def write(self, tmp, text):
        path = Path(tmp) / "trace.jsonl"
        path.write_text(text, encoding="utf-8")
        return path

    def test_clean_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                load_jsonl(self.write(tmp, '{"a": 1}\n{"a": 2}\n')),
                [{"a": 1}, {"a": 2}],
            )

    def test_broken_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(EvidenceError) as ctx:
                load_jsonl(self.write(tmp, '{"a": 1}\n{"a": \n'))
        self.assertIn("line 2", str(ctx.exception))

    def test_list_line_and_nan_line(self):
        for text in ('[1, 2]\n', '{"a": NaN}\n', '{"a": 1}\n\n{"a": 2}\n'):
            with self.subTest(text=text), tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises(EvidenceError):
                    load_jsonl(self.write(tmp, text))

    def test_altered_jsonl_line_changes_the_verdict(self):
        run = v2_run()
        lines = [json.dumps(record) for record in run.pop("state_trace")]
        run["state_trace_file"] = "state-trace.jsonl"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_evidence(root, run, trace_lines=lines)
            self.assertEqual(assess_backend_loss(root)["criteria"]["SC-03"], "SUPPORTED")
            # An editor truncates one line: the whole trace is refused.
            lines[15] = lines[15][:-3]
            write_evidence(root, run, trace_lines=lines)
            with self.assertRaises(EvidenceError):
                assess_backend_loss(root)

    def test_trace_file_must_sit_next_to_run(self):
        run = v2_run()
        run.pop("state_trace")
        run["state_trace_file"] = "../state-trace.jsonl"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_evidence(root, run)
            (root / "evidence/state-trace.jsonl").write_text("{}\n", encoding="utf-8")
            with self.assertRaises(EvidenceError) as ctx:
                assess_backend_loss(root)
        self.assertIn("next to", str(ctx.exception))


class StateTraceSchemaTests(unittest.TestCase):
    def setUp(self):
        self.trace = consistent_trace(recorded_run())

    def assert_rejected(self, samples, fragment):
        with self.assertRaises(EvidenceError) as ctx:
            validate_state_trace(samples)
        self.assertIn(fragment, str(ctx.exception))

    def test_object_instead_of_list(self):
        self.assert_rejected({"samples": self.trace}, "list")

    def test_single_sample(self):
        self.assert_rejected(self.trace[:1], "at least two")

    def test_non_object_sample(self):
        self.trace[3] = [1, 2, 3]
        self.assert_rejected(self.trace, "not an object")

    def test_missing_field(self):
        del self.trace[3]["ess_soc_pct"]
        self.assert_rejected(self.trace, "ess_soc_pct")

    def test_nan_bool_and_string_values(self):
        for value in (float("nan"), True, "4500"):
            with self.subTest(value=value):
                trace = copy.deepcopy(self.trace)
                trace[3]["ess_w"] = value
                self.assert_rejected(trace, "ess_w")

    def test_duplicate_sample(self):
        self.trace.insert(4, dict(self.trace[3]))
        self.assert_rejected(self.trace, "duplicate")

    def test_equal_clocks_are_duplicates(self):
        self.trace[4]["captured_at_utc"] = self.trace[3]["captured_at_utc"]
        self.assert_rejected(self.trace, "duplicate")

    def test_reversed_clocks(self):
        self.trace[3], self.trace[4] = self.trace[4], self.trace[3]
        self.assert_rejected(self.trace, "not after")

    def test_naive_timestamp(self):
        self.trace[3]["captured_at_utc"] = "2026-09-08T21:39:00"
        self.assert_rejected(self.trace, "aware")

    def test_missing_time(self):
        del self.trace[3]["captured_at_utc"]
        self.assert_rejected(self.trace, "aware")

    def test_monotonic_counter_must_increase(self):
        for index, record in enumerate(self.trace):
            record["monotonic_s"] = 10.0 + index
        self.trace[5]["monotonic_s"] = 10.0
        self.assert_rejected(self.trace, "monotonic_s")

    def test_monotonic_counter_on_some_samples_only(self):
        self.trace[0]["monotonic_s"] = 1.0
        self.assert_rejected(self.trace, "only some")

    def test_stale_sample(self):
        # Captured 30 s after the source stamped it: beyond stale_after_s.
        record = self.trace[3]
        record["source_timestamp"] = record["captured_at_utc"]
        record["captured_at_utc"] = utc(30, record["captured_at_utc"]).isoformat()
        self.assert_rejected(self.trace, "stale")

    def test_source_after_capture(self):
        record = self.trace[3]
        record["source_timestamp"] = utc(2, record["captured_at_utc"]).isoformat()
        self.assert_rejected(self.trace, "later than captured_at_utc")

    def test_fresh_sample_with_both_timestamps_passes(self):
        for record in self.trace:
            record["source_timestamp"] = record["captured_at_utc"]
            record["captured_at_utc"] = utc(1, record["captured_at_utc"]).isoformat()
        self.assertEqual(len(validate_state_trace(self.trace)), len(self.trace))


class FreshnessRuleTests(unittest.TestCase):
    def test_not_judged_when_one_timestamp_is_absent(self):
        self.assertIsNone(freshness_error({"captured_at_utc": "2026-09-08T21:39:00+00:00"}))
        self.assertIsNone(freshness_error({"source_timestamp": "2026-09-08T21:39:00+00:00"}))
        self.assertIsNone(freshness_error({}))

    def test_stale_phase_snapshot_is_an_evidence_error_in_v2_only(self):
        run = recorded_run()
        phase = run["outage_discharge"]
        phase["source_timestamp"] = utc(-60, phase["captured_at_utc"]).isoformat()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_evidence(root, run)
            with self.assertRaises(EvidenceError):
                assess_backend_loss(root)
            # v1 reproduces the recorded verdict and never judged freshness.
            self.assertEqual(assess_backend_loss(root, evaluator="v1")["criteria"]["SC-03"], "SUPPORTED")


class StrictJsonTests(unittest.TestCase):
    def test_infinity_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.json"
            path.write_text('{"a": Infinity}', encoding="utf-8")
            with self.assertRaises(EvidenceError):
                load_strict_json(path)


if __name__ == "__main__":
    unittest.main()
