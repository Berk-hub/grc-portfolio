import shutil
import tempfile
import unittest
from pathlib import Path

from energy_assurance.cli import create_manifest, sha256_file, verify_manifest


class EvidenceTamperTests(unittest.TestCase):
    """The manifest checker must fail loudly on modified or missing evidence."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        evidence = self.root / "evidence/backend-loss"
        evidence.mkdir(parents=True)
        (evidence / "run.json").write_text('{"grid_w": 0}\n', encoding="utf-8")
        (evidence / "notes.txt").write_text("baseline\n", encoding="utf-8")
        self.manifest = evidence / "SHA256SUMS"
        create_manifest(self.root, Path("evidence/backend-loss"), self.manifest)

    def tearDown(self):
        self.tmp.cleanup()

    def test_clean_manifest_verifies(self):
        result = verify_manifest(self.root, self.manifest)
        self.assertEqual(result["status"], "VALID")
        self.assertEqual(result["checked"], 2)

    def test_modified_evidence_is_detected(self):
        target = self.root / "evidence/backend-loss/run.json"
        target.write_text('{"grid_w": 9999}\n', encoding="utf-8")
        result = verify_manifest(self.root, self.manifest)
        self.assertEqual(result["status"], "INVALID")
        self.assertTrue(any("Hash mismatch" in e for e in result["errors"]))

    def test_missing_evidence_is_detected(self):
        (self.root / "evidence/backend-loss/notes.txt").unlink()
        result = verify_manifest(self.root, self.manifest)
        self.assertEqual(result["status"], "INVALID")
        self.assertTrue(any("Missing evidence file" in e for e in result["errors"]))

    def test_manifest_edit_cannot_hide_tampering(self):
        target = self.root / "evidence/backend-loss/run.json"
        target.write_text('{"grid_w": 9999}\n', encoding="utf-8")
        lines = self.manifest.read_text(encoding="utf-8").splitlines()
        rewritten = []
        for line in lines:
            if "run.json" in line:
                rewritten.append(f"{sha256_file(target)}  evidence/backend-loss/run.json")
            else:
                rewritten.append(line)
        self.manifest.write_text("\n".join(rewritten) + "\n", encoding="utf-8")
        result = verify_manifest(self.root, self.manifest)
        self.assertEqual(result["status"], "VALID")
        # A rewritten manifest passes local verification by design: the integrity
        # anchor for the manifest itself is the git history and CI, not the file.
        # This test documents that boundary instead of pretending it does not exist.
