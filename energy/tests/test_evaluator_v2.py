"""SC-03 semantics of the v2 evaluator and the assess exit-code policy."""
import contextlib
import io
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from energy_assurance.cli import (
    EvidenceError, assess_backend_loss, evaluate_state_trace, main,
)

from evidence_fixtures import (
    BASELINE, CHARGE, DISCHARGE, consistent_trace, recorded_run, sample,
    v2_run, write_evidence,
)


class StateTraceCriterionTests(unittest.TestCase):
    def setUp(self):
        self.run = recorded_run()
        self.trace = consistent_trace(self.run)

    def test_consistent_trace_is_supported(self):
        status, reason, details = evaluate_state_trace(self.run, self.trace)
        self.assertEqual(status, "SUPPORTED", reason)
        self.assertEqual(details["problems"], [])
        self.assertEqual(details["gaps"], [])
        self.assertEqual(details["window_selection"], "run outage window")
        self.assertGreater(details["samples_in_window"], 20)

    def test_unexplained_ess_jump_is_not_supported(self):
        # The load does not change but the ESS steps by 2 kW: a transition
        # nobody asked for. Grid absorbs it so every sample still balances.
        victim = self.trace[15]
        victim["ess_w"] += 2000
        victim["grid_w"] -= 2000
        status, reason, _ = evaluate_state_trace(self.run, self.trace)
        self.assertEqual(status, "NOT SUPPORTED")
        self.assertIn("ess_w changed +2000 W", reason)

    def test_small_change_within_tolerance_is_explained(self):
        self.trace[15]["ess_w"] += 60
        self.trace[15]["grid_w"] -= 60
        status, _, _ = evaluate_state_trace(self.run, self.trace)
        self.assertEqual(status, "SUPPORTED")

    def test_sampling_gap_is_inconclusive(self):
        del self.trace[12:20]
        status, reason, details = evaluate_state_trace(self.run, self.trace)
        self.assertEqual(status, "INCONCLUSIVE")
        self.assertIn("gap of", reason)
        self.assertEqual(len(details["gaps"]), 1)

    def test_gap_measured_on_monotonic_counter_when_present(self):
        for index, record in enumerate(self.trace):
            record["monotonic_s"] = 100.0 + index
        # Wall clock jumps by a minute (NTP step) but the monotonic counter
        # shows the samples were 1 s apart, so there is no gap.
        for record in self.trace[20:]:
            moment = datetime.fromisoformat(record["captured_at_utc"])
            record["captured_at_utc"] = (moment + timedelta(seconds=60)).isoformat()
        run = dict(self.run, reconnected_at_utc="2026-09-08T21:45:00+00:00")
        status, reason, _ = evaluate_state_trace(run, self.trace)
        self.assertEqual(status, "SUPPORTED", reason)

    def test_unbalanced_sample_is_not_supported(self):
        self.trace[5]["consumption_w"] += 500
        status, reason, _ = evaluate_state_trace(self.run, self.trace)
        self.assertEqual(status, "NOT SUPPORTED")
        self.assertIn("residual", reason)

    def test_out_of_range_sample_is_not_supported(self):
        self.trace[5]["ess_soc_pct"] = 900
        status, reason, _ = evaluate_state_trace(self.run, self.trace)
        self.assertEqual(status, "NOT SUPPORTED")
        self.assertIn("ess_soc_pct=900", reason)

    def test_missed_setpoint_is_not_supported(self):
        trace = consistent_trace(self.run, setpoint=0)
        trace[15]["grid_w"] = 800
        trace[15]["ess_w"] -= 800
        status, reason, _ = evaluate_state_trace(self.run, trace)
        self.assertEqual(status, "NOT SUPPORTED")
        self.assertIn("missed set-point", reason)

    def test_curtailment_at_soc_ceiling_is_explained_by_limit(self):
        # Battery full: the controller cannot charge, so surplus PV exports to
        # the grid. Grid target 0 W is missed and ess_w does not follow the
        # load change, but the dictionary records this as correct behaviour.
        trace = consistent_trace(self.run, setpoint=0)
        for record in trace[20:]:
            record["ess_soc_pct"] = 100
            record["ess_w"] = 0
            record["grid_w"] = CHARGE[0] - CHARGE[1]
        status, reason, details = evaluate_state_trace(self.run, trace)
        self.assertEqual(status, "SUPPORTED", reason)
        self.assertGreater(details["limit_explained_transitions"], 0)

    def test_curtailment_at_soc_floor_is_explained_by_limit(self):
        trace = consistent_trace(self.run, setpoint=0)
        for record in trace[10:20]:
            record["ess_soc_pct"] = 0
            record["ess_w"] = 0
            record["grid_w"] = DISCHARGE[0] - DISCHARGE[1]
        status, reason, _ = evaluate_state_trace(self.run, trace)
        self.assertEqual(status, "SUPPORTED", reason)

    def test_limit_excuse_requires_balance_and_a_real_limit(self):
        # SOC in the middle of the range: a 0 W ESS with grid import is a
        # controller fault, not a limit.
        trace = consistent_trace(self.run, setpoint=0)
        for record in trace[10:20]:
            record["ess_w"] = 0
            record["grid_w"] = DISCHARGE[0] - DISCHARGE[1]
        status, _, _ = evaluate_state_trace(self.run, trace)
        self.assertEqual(status, "NOT SUPPORTED")

    def test_too_few_samples_in_window_is_inconclusive(self):
        early = sample(datetime.fromisoformat(
            "2026-09-08T21:30:00+00:00"), *BASELINE)
        later = sample(datetime.fromisoformat(
            "2026-09-08T21:30:01+00:00"), *BASELINE)
        status, reason, _ = evaluate_state_trace(self.run, [early, later])
        self.assertEqual(status, "INCONCLUSIVE")
        self.assertIn("fewer than two", reason)


class AssessmentFormatTests(unittest.TestCase):
    def test_v1_snapshots_are_inconclusive_for_sc03(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_evidence(root, recorded_run())
            result = assess_backend_loss(root)
        self.assertEqual(result["evidence_format"], 1)
        self.assertEqual(result["criteria"]["SC-03"], "INCONCLUSIVE")
        self.assertIsNone(result["state_trace"])

    def test_v2_consistent_trace_is_supported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_evidence(root, v2_run())
            result = assess_backend_loss(root)
        self.assertEqual(result["evidence_format"], 2)
        self.assertEqual(result["evaluator_version"], "v2")
        self.assertEqual(result["criteria"]["SC-03"], "SUPPORTED")
        self.assertEqual(result["overall_result"], "INCONCLUSIVE")  # SC-06

    def test_v2_trace_with_jump_is_not_supported(self):
        run = v2_run()
        run["state_trace"][15]["ess_w"] += 3000
        run["state_trace"][15]["grid_w"] -= 3000
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_evidence(root, run)
            result = assess_backend_loss(root)
        self.assertEqual(result["criteria"]["SC-03"], "NOT SUPPORTED")
        self.assertEqual(result["overall_result"], "NOT SUPPORTED")

    def test_v2_trace_from_jsonl_file(self):
        import json
        run = v2_run()
        lines = [json.dumps(record) for record in run.pop("state_trace")]
        run["state_trace_file"] = "state-trace.jsonl"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_evidence(root, run, trace_lines=lines)
            result = assess_backend_loss(root)
        self.assertEqual(result["criteria"]["SC-03"], "SUPPORTED")

    def test_format_2_without_trace_is_an_error(self):
        run = recorded_run()
        run["evidence_format"] = 2
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_evidence(root, run)
            with self.assertRaises(EvidenceError):
                assess_backend_loss(root)

    def test_v1_evaluator_ignores_trace_and_keeps_old_semantics(self):
        run = v2_run()
        run["state_trace"][15]["ess_w"] += 3000
        run["state_trace"][15]["grid_w"] -= 3000
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_evidence(root, run)
            result = assess_backend_loss(root, evaluator="v1")
        self.assertEqual(result["criteria"]["SC-03"], "SUPPORTED")


class ExitCodeTests(unittest.TestCase):
    """See assess_exit_code in cli.py for the policy."""

    def run_cli(self, root, *argv):
        cwd = os.getcwd()
        out, err = io.StringIO(), io.StringIO()
        try:
            os.chdir(root)
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = main(list(argv))
        finally:
            os.chdir(cwd)
        return code, out.getvalue(), err.getvalue()

    def test_completed_assessment_exits_zero_without_expectation(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_evidence(Path(tmp), recorded_run())
            code, out, _ = self.run_cli(tmp, "assess")
        self.assertEqual(code, 0)
        self.assertIn("SC-03: INCONCLUSIVE", out)

    def test_expectation_match_and_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_evidence(Path(tmp), recorded_run())
            self.assertEqual(self.run_cli(tmp, "assess", "--expect", "INCONCLUSIVE")[0], 0)
            self.assertEqual(self.run_cli(tmp, "assess", "--expect", "SUPPORTED")[0], 1)

    def test_v1_flag_reproduces_supported_sc03(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_evidence(Path(tmp), recorded_run())
            code, out, _ = self.run_cli(tmp, "assess", "--evaluator", "v1")
        self.assertEqual(code, 0)
        self.assertIn("SC-03: SUPPORTED", out)
        self.assertIn("EVALUATOR: v1", out)

    def test_evidence_error_exits_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = root / "evidence/backend-loss"
            evidence.mkdir(parents=True)
            (evidence / "11-final-reconciliation-run.json").write_text("{not json", encoding="utf-8")
            code, _, err = self.run_cli(tmp, "assess", "--expect", "INCONCLUSIVE")
        self.assertEqual(code, 2)
        self.assertIn("ERROR:", err)

    def test_help_documents_evaluator_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = io.StringIO()
            with contextlib.redirect_stdout(out), self.assertRaises(SystemExit):
                main(["assess", "--help"])
        self.assertIn("--evaluator", out.getvalue())
        self.assertIn("v1", out.getvalue())
        self.assertIn("--expect", out.getvalue())


if __name__ == "__main__":
    unittest.main()
