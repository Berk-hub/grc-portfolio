import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DataGovernanceTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.model = json.loads(
            (ROOT / "data/data-governance.json").read_text()
        )

    def test_data_class_ids_unique(self):
        ids = [x["id"] for x in self.model["data_classes"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_flow_ids_unique(self):
        ids = [x["id"] for x in self.model["flows"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_flow_references_exist(self):
        valid = {x["id"] for x in self.model["data_classes"]}

        for flow in self.model["flows"]:
            for ref in flow["data_classes"]:
                self.assertIn(ref, valid)

    def test_secret_policy(self):
        secret = next(
            x for x in self.model["data_classes"]
            if x["id"] == "DG-SEC-004"
        )

        self.assertEqual(
            secret["repository_policy"],
            "MUST_NOT_BE_COMMITTED"
        )


class AiGovernanceTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.model = json.loads(
            (ROOT / "data/ai-governance.json").read_text()
        )

    def test_current_system_has_no_ai(self):
        current = self.model["current_configuration"]

        self.assertFalse(current["ai_or_ml_component_present"])
        self.assertFalse(current["ai_in_local_control_loop"])
        self.assertFalse(current["ai_in_backend_decision_path"])

    def test_no_false_high_risk_claim(self):
        for item in self.model["future_use_cases"]:
            self.assertFalse(
                item["automatic_high_risk_conclusion"]
            )

    def test_ai_controls_not_falsely_tested(self):
        self.assertFalse(
            self.model["current_test_status"]["ai_controls_tested"]
        )


if __name__ == "__main__":
    unittest.main()
