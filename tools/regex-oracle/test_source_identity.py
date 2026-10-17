"""Check whole-source identity and reject edited or additional source files."""

import hashlib
import lzma
from pathlib import Path
import tarfile
import tempfile
import unittest

from source_identity import verify_source_tree


class SourceIdentityTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.source = root / "source"
        (self.source / "include").mkdir(parents=True)
        self.files = {"LICENSE": b"upstream license\n", "include/header.h": b"source header\n"}
        for name, content in self.files.items():
            (self.source / name).write_bytes(content)
        self.archive = root / "source.tar.gz"
        with tarfile.open(self.archive, "w:gz") as archive:
            archive.add(self.source, arcname=self.source.name)
        self.output = root / "evidence/source.tsv.xz"

    def test_records_every_extracted_file(self):
        (self.source / ".boostregexrs-source-archive.json").write_text("{}\n")
        result = verify_source_tree(self.archive, self.source, self.output)
        self.assertEqual(result["entries"], 2)
        self.assertTrue(result["all_extracted_contents_match_archive"])
        self.assertEqual(result["patch_set"], [])
        manifest = lzma.decompress(self.output.read_bytes()).decode()
        expected = "path\tkind\tbytes\tsha256\n" + "".join(
            f"{name}\tfile\t{len(content)}\t{hashlib.sha256(content).hexdigest()}\n"
            for name, content in sorted(self.files.items())
        )
        self.assertEqual(manifest, expected)

    def test_rejects_modified_source_content(self):
        (self.source / "include/header.h").write_bytes(b"modified source\n")
        with self.assertRaisesRegex(ValueError, "Extracted source content differs"):
            verify_source_tree(self.archive, self.source, self.output)
        self.assertFalse(self.output.exists())

    def test_rejects_additional_source_file(self):
        (self.source / "unexpected.h").write_bytes(b"extra source\n")
        with self.assertRaisesRegex(ValueError, "Unexpected extracted source paths"):
            verify_source_tree(self.archive, self.source, self.output)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
