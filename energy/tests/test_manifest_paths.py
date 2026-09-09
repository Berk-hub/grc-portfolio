import tempfile
import unittest
from pathlib import Path

from energy_assurance.cli import create_manifest, verify_manifest


class EvidenceManifestPathTests(unittest.TestCase):
    def test_relative_evidence_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = root / "evidence/backend-loss"
            evidence.mkdir(parents=True)
            (evidence / "sample.txt").write_text("sample\n", encoding="utf-8")
            output = evidence / "SHA256SUMS"
            count = create_manifest(root, Path("evidence/backend-loss"), output)
            self.assertEqual(count, 1)
            result = verify_manifest(root, output)
            self.assertEqual(result["status"], "VALID")
            self.assertEqual(result["checked"], 1)


if __name__ == "__main__":
    unittest.main()
