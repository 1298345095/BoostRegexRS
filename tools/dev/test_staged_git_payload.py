"""Exercise exact staged-file publication in isolated Git repositories."""

import base64
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


SCRIPT = Path(__file__).with_name("staged_git_payload.py").resolve()


class StagedPayloadTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory(dir=SCRIPT.parents[3])
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name)
        self.env = os.environ.copy()
        for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR"):
            self.env.pop(name, None)
        self.git("init", "-q")

    def git(self, *arguments, input=None):
        return subprocess.run(["git", *arguments], cwd=self.repo, env=self.env,
                              input=input, capture_output=True, check=True, timeout=5).stdout

    def stage(self, path, content=b"staged bytes", mode="100644"):
        digest = self.git("hash-object", "-w", "--stdin", input=content).decode().strip()
        self.git("update-index", "--add", "--cacheinfo", f"{mode},{digest},{path}")
        return digest

    def invoke(self, *arguments, cwd=None):
        return subprocess.run([sys.executable, "-B", str(SCRIPT), *arguments],
                              cwd=cwd or self.repo, env=self.env,
                              capture_output=True, text=True, timeout=5)

    def payload(self, *arguments, cwd=None):
        result = self.invoke(*arguments, cwd=cwd)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def rejected(self, path, message):
        result = self.invoke(f"--path={path}")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertIn(message, result.stderr)

    def test_glob_characters_and_pathspec_magic_are_literal_filenames(self):
        for literal, decoy in (("item?.txt", "item1.txt"),
                               ("other*.txt", "other0.txt"),
                               ("number[1].txt", "number1.txt"),
                               (":(glob)magic*.txt", "magic1.txt")):
            with self.subTest(path=literal):
                content = f"literal {literal}\n".encode()
                self.stage(decoy, b"different file")
                digest = self.stage(literal, content)
                result = self.payload(f"--path={literal}")
                self.assertEqual(result["path"], literal)
                self.assertEqual(result["sha"], digest)
                self.assertEqual(base64.b64decode(result["content"]), content)

    def test_unmatched_and_empty_paths_are_deliberately_rejected(self):
        (self.repo / "untracked.txt").write_text("not indexed", encoding="utf-8")
        self.rejected("untracked.txt", "No staged entry matches")
        self.rejected("", "--path must name one exact staged file")

    def test_directory_with_one_entry_is_rejected(self):
        self.stage("single/child.txt")
        self.rejected("single", "selects a directory")

    def test_directory_with_multiple_entries_is_rejected(self):
        self.stage("multiple/first.txt")
        self.stage("multiple/second.txt")
        self.rejected("multiple", "selects multiple staged entries")

    def test_single_and_multiple_conflict_stages_are_rejected(self):
        digest = self.git("hash-object", "-w", "--stdin", input=b"conflict").decode().strip()
        for stages in ((2,), (1, 2, 3)):
            with self.subTest(stages=stages):
                path = f"conflict-{len(stages)}.txt"
                records = "".join(f"100644 {digest} {stage}\t{path}\n" for stage in stages)
                self.git("update-index", "--index-info", input=records.encode())
                self.rejected(path, "Resolve the staged merge conflict")

    def test_chunks_preserve_indexed_bytes_and_executable_mode(self):
        content = b"0123456789\x00indexed"
        digest = self.stage("program", content, mode="100755")
        (self.repo / "program").write_bytes(b"unstaged replacement")
        for offset, length in ((0, 0), (3, 4), (len(content) + 5, 2)):
            with self.subTest(offset=offset, length=length):
                result = self.payload("--path=program", "--offset", str(offset),
                                      "--length", str(length))
                self.assertEqual(result, {
                    "path": "program", "mode": "100755", "sha": digest,
                    "total_bytes": len(content), "offset": offset,
                    "chunk_bytes": len(content[offset:offset + length]),
                    "content": base64.b64encode(content[offset:offset + length]).decode(),
                    "encoding": "base64",
                })
        (self.repo / "program").unlink()
        self.assertEqual(base64.b64decode(self.payload("--path=program")["content"]), content)

    def test_symlink_entry_keeps_its_blob_and_mode(self):
        target = b"../outside-target"
        digest = self.stage("link", target, mode="120000")
        result = self.payload("--path=link")
        self.assertEqual((result["mode"], result["sha"]), ("120000", digest))
        self.assertEqual(base64.b64decode(result["content"]), target)

    def test_gitlink_is_rejected_as_a_non_blob(self):
        self.git("update-index", "--add", "--cacheinfo", "160000," + "1" * 40 + ",submodule")
        self.rejected("submodule", "must name a staged blob")

    def test_absolute_and_subdirectory_relative_paths_keep_git_output_names(self):
        self.stage("parent.txt", b"parent")
        self.stage("nested/child.txt", b"child")
        nested = self.repo / "nested"
        nested.mkdir()
        result = self.payload(f"--path={nested / 'child.txt'}")
        self.assertEqual(result["path"], "nested/child.txt")
        result = self.payload("--path=../parent.txt", cwd=nested)
        self.assertEqual(result["path"], "../parent.txt")
        result = self.payload("--path=./child.txt", cwd=nested)
        self.assertEqual(result["path"], "child.txt")

    def test_tab_and_newline_in_filename_survive_nul_separated_index_output(self):
        path = "space \tline\nname.txt"
        self.stage(path)
        self.assertEqual(self.payload(f"--path={path}")["path"], path)

    def test_no_path_retains_parent_tree_and_changed_path_interface(self):
        self.stage("base.txt")
        tree = self.git("write-tree").decode().strip()
        parent = self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                          "commit-tree", tree, input=b"fixture\n").decode().strip()
        self.git("update-ref", "HEAD", parent)
        self.stage("next?.txt")
        result = self.payload()
        self.assertEqual(result, {"parent": parent,
                                  "tree": self.git("write-tree").decode().strip(),
                                  "paths": ["next?.txt"]})


if __name__ == "__main__":
    unittest.main()
