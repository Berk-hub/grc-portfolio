import tempfile
import unittest
from pathlib import Path

from energy_assurance.cli import create_manifest, reconciliation_evidence, verify_manifest


class ReconciliationSafetyTests(unittest.TestCase):
    def test_unstructured_markers_cannot_prove_backfill(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = root / "evidence/backend-loss"
            evidence.mkdir(parents=True)
            (evidence / "13-historic-resend-monitor.jsonl").write_text(
                '{"last_successful_resend": "stale value"}\n', encoding="utf-8"
            )
            for text in (
                "Not telemetry: 15200 1700 14500 11800 14300 -25000",
                "5200 700 4500 1800 4300 -2500",
            ):
                with self.subTest(text=text):
                    (evidence / "14-influx-post-resend.txt").write_text(text, encoding="utf-8")
                    result = reconciliation_evidence(root)
                    self.assertEqual(result["status"], "INCONCLUSIVE")
                    self.assertFalse(result["central_backfill_verified"])

    def test_frozen_monitor_is_included_and_tampering_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = root / "evidence/backend-loss"
            evidence.mkdir(parents=True)
            monitor = evidence / "13-historic-resend-monitor.jsonl"
            monitor.write_text('{"last_successful_resend": null}\n', encoding="utf-8")
            manifest = evidence / "SHA256SUMS"
            create_manifest(root, evidence, manifest)
            self.assertEqual(verify_manifest(root, manifest)["checked"], 1)
            monitor.write_text('{"last_successful_resend": 123}\n', encoding="utf-8")
            self.assertEqual(verify_manifest(root, manifest)["status"], "INVALID")
