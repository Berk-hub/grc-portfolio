import json
import tempfile
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
    def test_core_resilience_criteria(self):
        result = assess_backend_loss(ROOT)

        for criterion in (
            "SC-01",
            "SC-02",
            "SC-03",
            "SC-04",
            "SC-05",
        ):
            self.assertEqual(
                result["criteria"][criterion],
                "SUPPORTED",
                msg=json.dumps(result, indent=2),
            )

        self.assertIn(
            result["criteria"]["SC-06"],
            {
                "SUPPORTED",
                "INCONCLUSIVE",
            },
        )

        self.assertNotEqual(
            result["overall_result"],
            "NOT SUPPORTED",
        )


if __name__ == "__main__":
    unittest.main()
