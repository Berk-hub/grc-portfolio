"""Manifest scope: regular files inside the evidence directory, nothing else."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from energy_assurance.cli import EvidenceError, create_manifest, verify_manifest


class ManifestHygieneTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.evidence = self.root / "evidence/backend-loss"
        self.evidence.mkdir(parents=True)
        (self.evidence / "run.json").write_text('{"grid_w": 0}\n', encoding="utf-8")
        (self.evidence / "sub").mkdir()
        (self.evidence / "sub/notes.txt").write_text("baseline\n", encoding="utf-8")
        self.manifest = self.evidence / "SHA256SUMS"

    def tearDown(self):
        self.tmp.cleanup()

    def make_symlink(self, link: Path, target: Path):
        try:
            os.symlink(target, link, target_is_directory=target.is_dir())
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlinks not available here: {exc}")

    def test_manifest_uses_posix_paths_and_excludes_itself(self):
        count = create_manifest(self.root, Path("evidence/backend-loss"), self.manifest)
        self.assertEqual(count, 2)
        text = self.manifest.read_text(encoding="utf-8")
        self.assertIn("  evidence/backend-loss/sub/notes.txt", text)
        self.assertNotIn("\\", text)
        self.assertNotIn("SHA256SUMS", text)

    def test_file_added_after_manifest_is_reported(self):
        create_manifest(self.root, Path("evidence/backend-loss"), self.manifest)
        (self.evidence / "late-addition.log").write_text("x\n", encoding="utf-8")
        result = verify_manifest(self.root, self.manifest)
        self.assertEqual(result["status"], "INVALID")
        self.assertEqual(result["checked"], 2)
        self.assertEqual(
            result["errors"],
            ["Unlisted evidence file: evidence/backend-loss/late-addition.log"],
        )

    def test_manifest_line_removed_is_reported_as_unlisted(self):
        create_manifest(self.root, Path("evidence/backend-loss"), self.manifest)
        lines = [
            line for line in self.manifest.read_text(encoding="utf-8").splitlines()
            if "notes.txt" not in line
        ]
        self.manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
        result = verify_manifest(self.root, self.manifest)
        self.assertEqual(result["status"], "INVALID")
        self.assertTrue(any("Unlisted" in e and "notes.txt" in e for e in result["errors"]))

    def test_symlink_in_evidence_dir_is_rejected_on_create(self):
        outside = self.root / "outside.txt"
        outside.write_text("secret\n", encoding="utf-8")
        self.make_symlink(self.evidence / "link.txt", outside)
        with self.assertRaises(EvidenceError) as ctx:
            create_manifest(self.root, Path("evidence/backend-loss"), self.manifest)
        self.assertIn("Symbolic link", str(ctx.exception))

    def test_symlinked_directory_escaping_evidence_is_rejected(self):
        elsewhere = self.root / "elsewhere"
        elsewhere.mkdir()
        (elsewhere / "leak.txt").write_text("x\n", encoding="utf-8")
        self.make_symlink(self.evidence / "escape", elsewhere)
        with self.assertRaises(EvidenceError):
            create_manifest(self.root, Path("evidence/backend-loss"), self.manifest)

    def test_symlink_appearing_after_manifest_fails_verification(self):
        create_manifest(self.root, Path("evidence/backend-loss"), self.manifest)
        self.make_symlink(self.evidence / "link.json", self.evidence / "run.json")
        result = verify_manifest(self.root, self.manifest)
        self.assertEqual(result["status"], "INVALID")
        self.assertTrue(any("Symbolic link" in e for e in result["errors"]))

    def test_symlink_detection_without_symlink_privilege(self):
        # Windows may refuse to create symlinks; simulate one so the check
        # itself is exercised on every platform.
        original = Path.is_symlink

        def fake_is_symlink(path):
            return path.name == "run.json" or original(path)

        with mock.patch.object(Path, "is_symlink", fake_is_symlink):
            with self.assertRaises(EvidenceError) as ctx:
                create_manifest(self.root, Path("evidence/backend-loss"), self.manifest)
            self.assertIn("Symbolic link", str(ctx.exception))
        create_manifest(self.root, Path("evidence/backend-loss"), self.manifest)
        with mock.patch.object(Path, "is_symlink", fake_is_symlink):
            result = verify_manifest(self.root, self.manifest)
        self.assertEqual(result["status"], "INVALID")
        self.assertTrue(any("Symbolic link" in e or "symbolic link" in e for e in result["errors"]))

    def test_evidence_dir_outside_root_is_rejected(self):
        with tempfile.TemporaryDirectory() as other:
            with self.assertRaises(EvidenceError):
                create_manifest(self.root, Path(other).resolve(), self.manifest)

    def test_manifest_entries_escaping_the_repository_are_rejected(self):
        create_manifest(self.root, Path("evidence/backend-loss"), self.manifest)
        secret = self.root.parent / "hygiene-secret.txt"
        secret.write_text("x\n", encoding="utf-8")
        try:
            digest = "0" * 64
            with self.manifest.open("a", encoding="utf-8") as handle:
                handle.write(f"{digest}  ../hygiene-secret.txt\n")
                handle.write(f"{digest}  {secret}\n")
            result = verify_manifest(self.root, self.manifest)
        finally:
            secret.unlink()
        self.assertEqual(result["status"], "INVALID")
        escapes = [e for e in result["errors"] if "escapes repository" in e]
        self.assertEqual(len(escapes), 2)
        # Escaping entries are never hashed.
        self.assertEqual(result["checked"], 2)


if __name__ == "__main__":
    unittest.main()
