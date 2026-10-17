"""Regressions for native-reference build evidence."""

from pathlib import Path
import unittest

from build_reference import runtime_library_paths


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


if __name__ == "__main__":
    unittest.main()
