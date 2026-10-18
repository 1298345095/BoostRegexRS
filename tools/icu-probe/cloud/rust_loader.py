"""Run a verified project-local compiler without generating wrapper source."""

import os
from pathlib import Path
import sys


def exec_tool(name):
    """Preserve Cargo's complete environment, including hyphenated keys."""
    prefix = Path(os.environ["BOOSTREGEXRS_RUST_PREFIX"])
    loader = "/lib64/ld-linux-x86-64.so.2"
    arguments = [loader, "--library-path", str(prefix / "lib"),
                 str(prefix / "bin" / name), *sys.argv[1:]]
    os.execve(loader, arguments, os.environ)
