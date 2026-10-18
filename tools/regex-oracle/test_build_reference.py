"""Regressions for native-reference build evidence."""

import json
from pathlib import Path
import tempfile
import unittest

from build_reference import runtime_library_paths, write_verified_environment


class RuntimeLibraryPathsTests(unittest.TestCase):
    def test_preserves_spaces_in_dependency_and_direct_loader_paths(self):
        output = """\
\tlinux-vdso.so.1 (0x00007fff12340000)
\tlibicui18n.so.77 => /tmp/reference cache (fresh)/install/icu/lib/libicui18n.so.77 (0x00007fab12340000)
\tlibicuuc.so.77 => /tmp/reference cache (fresh)/install/icu/lib/libicuuc.so.77 (0x00007fab22340000)
\tlibicudata.so.77 => /tmp/reference cache (fresh)/install/icu/lib/libicudata.so.77 (0x00007fab32340000)
\tlibc.so.6 => /lib/x86_64-linux-gnu/libc.so.6 (0x00007fab42340000)
\t/tmp/native loader/ld-linux-x86-64.so.2 (0x00007fab52340000)
"""
        expected = [
            "/tmp/reference cache (fresh)/install/icu/lib/libicui18n.so.77",
            "/tmp/reference cache (fresh)/install/icu/lib/libicuuc.so.77",
            "/tmp/reference cache (fresh)/install/icu/lib/libicudata.so.77",
            "/lib/x86_64-linux-gnu/libc.so.6",
            "/tmp/native loader/ld-linux-x86-64.so.2",
        ]
        self.assertEqual(runtime_library_paths(output), sorted(map(Path, expected)))


class EnvironmentMetadataTests(unittest.TestCase):
    def test_emits_paths_to_verified_records_and_rejects_changed_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            cache = Path(temporary)
            (cache / "smoke").mkdir()
            smoke = {"keys": {}}
            for strength in ("primary", "identical"):
                metadata = {"boost": "1.89.0", "icu": "77.1", "unicode": "16.0.0",
                            "cldr": "47.0", "locale": "root", "strength": strength}
                (cache / "smoke" / (strength + "-metadata.json")).write_text(json.dumps(metadata))
                smoke["keys"][strength] = {"metadata": metadata}
            original = {"data": {"runtime_versions_verified_by": "reference/metadata.json"}}
            output = cache / "reports/environment.json"
            returned = write_verified_environment(cache, original, smoke, output)
            emitted = json.loads(output.read_text())
            self.assertEqual(emitted, returned)
            self.assertEqual(set(emitted["data"]["runtime_versions_verified_by"]), {"primary", "identical"})
            for strength, relative in emitted["data"]["runtime_versions_verified_by"].items():
                path = cache / relative
                self.assertTrue(path.is_file())
                self.assertEqual(json.loads(path.read_text()), smoke["keys"][strength]["metadata"])
            self.assertEqual(original["data"]["runtime_versions_verified_by"], "reference/metadata.json")
            (cache / "smoke/primary-metadata.json").write_text("{}")
            rejected = cache / "reports/rejected.json"
            with self.assertRaisesRegex(ValueError, "differs from the verified primary smoke"):
                write_verified_environment(cache, original, smoke, rejected)
            self.assertFalse(rejected.exists())


if __name__ == "__main__":
    unittest.main()
