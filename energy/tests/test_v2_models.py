import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    return json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))


class CrossReferenceTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.controls = {c["control_id"] for c in load("controls.json")}
        cls.risks = {r["risk_id"] for r in load("risks.json")}
        cls.sources = {s["source_id"] for s in load("regulatory-register.json")}
        cls.profiles = {p["profile_id"] for p in load("entity-profiles.json")["profiles"]}
        cls.obligations = load("obligations.json")["obligations"]
        cls.findings = load("findings.json")["findings"]
        cls.treatments = load("risk-treatments.json")["treatments"]
        cls.workpapers = load("audit-program.json")["workpapers"]
        cls.finding_ids = {f["id"] for f in cls.findings}

    def test_obligation_references_resolve(self):
        vocab = set(load("obligations.json")["status_vocabulary"])
        for ob in self.obligations:
            self.assertIn(ob["source_id"], self.sources, ob["id"])
            self.assertIn(ob["entity_profile_id"], self.profiles, ob["id"])
            self.assertIn(ob["applicability_status"], vocab, ob["id"])
            for cid in ob["control_ids"]:
                self.assertIn(cid, self.controls, ob["id"])
            for gid in ob["gap_ids"]:
                self.assertIn(gid, self.finding_ids, ob["id"])

    def test_not_applicable_requires_rationale(self):
        for ob in self.obligations:
            if ob["applicability_status"] == "NOT_APPLICABLE":
                self.assertTrue(ob["rationale"].strip(), ob["id"])

    def test_finding_references_resolve(self):
        for f in self.findings:
            if f["control_id"]:
                self.assertIn(f["control_id"], self.controls, f["id"])
            if f["risk_id"]:
                self.assertIn(f["risk_id"], self.risks, f["id"])

    def test_every_risk_has_exactly_one_treatment(self):
        treated = [t["risk_id"] for t in self.treatments]
        self.assertEqual(sorted(treated), sorted(self.risks))

    def test_treatment_references_and_honesty(self):
        for t in self.treatments:
            for cid in t["controls"]:
                self.assertIn(cid, self.controls, t["risk_id"])
            if t["control_evidence"] in ("NOT_TESTED", "INCONCLUSIVE"):
                self.assertIn(
                    t["residual_status"],
                    ("UNASSESSED",),
                    f"{t['risk_id']}: no effectiveness evidence cannot reduce residual risk",
                )
            self.assertIsNone(t["acceptance"], t["risk_id"])

    def test_workpaper_references_resolve(self):
        ids = [w["audit_id"] for w in self.workpapers]
        self.assertEqual(len(ids), len(set(ids)))
        covered = {w["control_id"] for w in self.workpapers}
        self.assertEqual(covered, self.controls)


if __name__ == "__main__":
    unittest.main()
