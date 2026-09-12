import json
import unittest
from pathlib import Path

from energy_assurance.cli import (
    assess_backend_loss,
    rating_for_score,
    validate_repository,
)


ROOT = Path(__file__).resolve().parents[1]


class RiskRatingTests(unittest.TestCase):
    def test_rating_boundaries(self):
        self.assertEqual(rating_for_score(1), "LOW")
        self.assertEqual(rating_for_score(4), "LOW")
        self.assertEqual(rating_for_score(5), "MEDIUM")
        self.assertEqual(rating_for_score(9), "MEDIUM")
        self.assertEqual(rating_for_score(10), "HIGH")
        self.assertEqual(rating_for_score(16), "HIGH")
        self.assertEqual(rating_for_score(17), "CRITICAL")
        self.assertEqual(rating_for_score(25), "CRITICAL")


class RepositoryValidationTests(unittest.TestCase):
    def test_repository_model_is_valid(self):
        result = validate_repository(ROOT)

        self.assertEqual(
            result["errors"],
            [],
            msg=json.dumps(result, indent=2),
        )

        self.assertEqual(
            result["status"],
            "VALID",
        )

        self.assertEqual(
            result["warnings"],
            [],
            msg=json.dumps(result, indent=2),
        )

        self.assertEqual(
            result["counts"]["dependencies"],
            3,
        )


class BackendLossEvidenceTests(unittest.TestCase):
    def test_core_resilience_criteria_v2(self):
        """The recorded four-snapshot evidence supports SC-01/02/04/05 only."""
        result = assess_backend_loss(ROOT)

        self.assertEqual(result["evaluator_version"], "v2")
        self.assertEqual(result["evidence_format"], 1)

        for criterion in ("SC-01", "SC-02", "SC-04", "SC-05"):
            self.assertEqual(
                result["criteria"][criterion],
                "SUPPORTED",
                msg=json.dumps(result, indent=2),
            )

        self.assertEqual(result["criteria"]["SC-03"], "INCONCLUSIVE")
        self.assertIn("state trace", result["reasons"]["SC-03"])
        self.assertEqual(result["criteria"]["SC-06"], "INCONCLUSIVE")
        self.assertEqual(result["overall_result"], "INCONCLUSIVE")

    def test_v1_evaluator_reproduces_recorded_assessment(self):
        recorded = json.loads(
            (ROOT / "evidence/backend-loss/assessment-latest.json").read_text(
                encoding="utf-8"
            )
        )
        result = assess_backend_loss(ROOT, evaluator="v1")

        self.assertEqual(result["evaluator_version"], "v1")
        self.assertEqual(result["criteria"], recorded["criteria"])
        self.assertEqual(result["overall_result"], recorded["overall_result"])
        self.assertEqual(result["evidence_file"], recorded["evidence_file"])
        self.assertEqual(result["observations"], recorded["observations"])

    def test_unknown_evaluator_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_backend_loss(ROOT, evaluator="v3")


if __name__ == "__main__":
    unittest.main()
