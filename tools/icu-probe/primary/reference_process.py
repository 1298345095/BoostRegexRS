"""Run the PRIMARY oracle once, isolating native signals only when necessary.

The normal path streams one whole corpus through one subprocess. A signal is
not a valid key and must not erase the remaining coverage: failed ranges are
bisected until individual crashing inputs can be recorded as reference errors.
Ordinary process exits, launch failures and malformed output remain execution
errors, with no recursive retry. Failed batches retain their exact output.
"""

from __future__ import annotations

import itertools
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile


KEY_HEADER = b"case_id\traw_icu_hex\tboost_u32_hex"
INPUT_HEADERS = {b"case_id\tutf8_hex", b"case_id\tu16_hex", b"case_id\tu32_hex"}


class ReferenceExecutionError(RuntimeError):
    """The oracle could not supply a complete, well-formed reference result."""

    def __init__(self, message: str, kind: str = "protocol_error"):
        super().__init__(message)
        self.kind = kind


def _input_header(stream) -> bytes:
    header = stream.readline()
    if header.rstrip(b"\r\n") not in INPUT_HEADERS:
        raise ReferenceExecutionError("Unexpected oracle input header")
    return header


def _input_id(line: bytes) -> bytes:
    fields = line.rstrip(b"\r\n").split(b"\t")
    if len(fields) != 2 or not fields[0]:
        raise ReferenceExecutionError("Malformed oracle input row")
    return fields[0]


def _validate_output(source: Path, output: Path) -> int:
    """Check protocol and exact row coverage; key semantics belong to compare."""
    count = 0
    with source.open("rb") as inputs, output.open("rb") as results:
        _input_header(inputs)
        if results.readline().rstrip(b"\r\n") != KEY_HEADER:
            raise ReferenceExecutionError(f"Unexpected oracle output header: {output}")
        for original, result in itertools.zip_longest(inputs, results):
            if original is None or result is None:
                raise ReferenceExecutionError(f"Missing or extra oracle output rows: {output}")
            fields = result.rstrip(b"\r\n").split(b"\t")
            if len(fields) != 3 or fields[0] != _input_id(original):
                raise ReferenceExecutionError(f"Malformed or reordered oracle output row {count}: {output}")
            if not fields[1] or not fields[2]:
                raise ReferenceExecutionError(f"Empty oracle key field at row {count}: {output}")
            count += 1
    if count == 0:
        raise ReferenceExecutionError("Empty oracle input corpus")
    return count


def _input_offsets(source: Path) -> tuple[bytes, list[int]]:
    """Index byte ranges only on failure, without retaining all input strings."""
    offsets = []
    with source.open("rb") as stream:
        header = _input_header(stream)
        while True:
            offset = stream.tell()
            line = stream.readline()
            if not line:
                offsets.append(offset)
                break
            _input_id(line)
            offsets.append(offset)
    if len(offsets) == 1:
        raise ReferenceExecutionError("The oracle signalled for an empty input corpus")
    return header, offsets


def _copy_range(source: Path, output: Path, header: bytes, begin: int, end: int) -> None:
    with source.open("rb") as original, output.open("wb") as destination:
        destination.write(header)
        original.seek(begin)
        remaining = end - begin
        while remaining:
            block = original.read(min(remaining, 1 << 20))
            if not block:
                raise ReferenceExecutionError("Oracle input changed while isolating a failure")
            destination.write(block)
            remaining -= len(block)


def run_reference(command, source: Path, output: Path, env, cwd) -> dict:
    """Return run metadata and write a complete TSV, including signal markers.

    ``reference_error_count`` counts individual failing inputs, whereas
    ``signal_failures`` counts all signalled batches during isolation. Exact
    stdout/stderr for every attempted failed range remain in the evidence
    directory. ``unresolved_signal_ranges`` preserves batch-only/intermittent
    failures that disappear when split; recovered keys do not turn the failed
    original call into a pass. The initial batch's stderr also keeps the
    conventional sibling ``.stderr.log`` path. Metadata is written even for
    ordinary execution errors.
    """
    source, output = Path(source).resolve(), Path(output).resolve()
    if source == output or (output.exists() and os.path.samefile(source, output)):
        raise ValueError("Oracle input and output must be different files")
    output.parent.mkdir(parents=True, exist_ok=True)
    stderr_path = output.with_suffix(".stderr.log")
    metadata_path = output.with_suffix(".reference-process.json")
    arguments = [str(value) for value in command]
    metadata = {
        "schema": "boostregexrs.primary-reference-process.v1",
        "status": "running", "command": arguments, "cwd": str(Path(cwd).resolve()),
        "source": str(source), "output": str(output), "metadata_path": str(metadata_path),
        "input_rows": None, "output_rows": None, "subprocess_runs": 0,
        "successful_batches": 0, "signal_failures": 0, "reference_error_count": 0,
        "reference_error_free": False, "unresolved_signal_ranges": [],
        "isolation_used": False, "range_convention": "zero-based input rows; end is exclusive; header is excluded",
        "attempts": [],
    }
    evidence = None
    initial_preserved = False

    def save_metadata() -> None:
        temporary = metadata_path.with_suffix(metadata_path.suffix + ".tmp")
        temporary.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(metadata_path)

    def evidence_directory() -> Path:
        nonlocal evidence
        if evidence is None:
            evidence = Path(tempfile.mkdtemp(prefix=output.name + ".reference-attempts-", dir=output.parent))
            metadata["evidence_directory"] = str(evidence)
        return evidence

    def preserve_initial() -> None:
        nonlocal initial_preserved
        if initial_preserved or not metadata["attempts"]:
            return
        initial = metadata["attempts"][0]
        directory = evidence_directory()
        if output.exists():
            original_stdout = directory / "attempt-000000.stdout.tsv"
            output.replace(original_stdout)
            initial["stdout"] = str(original_stdout)
        if stderr_path.exists():
            original_stderr = directory / "attempt-000000.stderr.log"
            shutil.copyfile(stderr_path, original_stderr)
            initial["stderr"] = str(original_stderr)
        initial_preserved = True

    def launch(input_path: Path, stdout_path: Path, error_path: Path, begin: int, end: int | None) -> dict:
        attempt = {
            "attempt": metadata["subprocess_runs"], "begin": begin, "end": end,
            "input": str(input_path), "stdout": str(stdout_path), "stderr": str(error_path),
            "returncode": None,
        }
        metadata["subprocess_runs"] += 1
        metadata["attempts"].append(attempt)
        try:
            with input_path.open("rb") as stdin, stdout_path.open("wb") as stdout, error_path.open("wb") as stderr:
                process = subprocess.run(arguments, stdin=stdin, stdout=stdout, stderr=stderr, env=env, cwd=cwd)
        except OSError as error:
            attempt["launch_error"] = str(error)
            raise ReferenceExecutionError(f"Could not launch oracle: {error}", "launch_error") from error
        attempt["returncode"] = process.returncode
        if process.returncode < 0:
            metadata["signal_failures"] += 1
            attempt["signal_number"] = -process.returncode
            try:
                attempt["signal_name"] = signal.Signals(-process.returncode).name
            except ValueError:
                attempt["signal_name"] = f"SIGNAL_{-process.returncode}"
        return attempt

    def ordinary_failure(attempt: dict) -> None:
        raise ReferenceExecutionError(
            f"Oracle exited with status {attempt['returncode']}; see {attempt['stderr']}", "nonzero_exit")

    save_metadata()
    try:
        initial = launch(source, output, stderr_path, 0, None)
        if initial["returncode"] == 0:
            count = _validate_output(source, output)
            initial["end"] = count
            metadata.update(input_rows=count, output_rows=count, successful_batches=1,
                            reference_error_free=True, status="completed")
        else:
            preserve_initial()
            if initial["returncode"] > 0:
                ordinary_failure(initial)
            header, offsets = _input_offsets(source)
            count = len(offsets) - 1
            initial["end"] = count
            metadata.update(input_rows=count, isolation_used=True)
            segments = []

            def isolate_failed(begin: int, end: int, failed: dict) -> None:
                if end - begin == 1:
                    with source.open("rb") as stream:
                        stream.seek(offsets[begin])
                        identity = _input_id(stream.readline())
                    marker = f"ERROR:SIGNAL_{-failed['returncode']}".encode("ascii")
                    synthetic = evidence_directory() / f"row-{begin:09d}.signal.tsv"
                    synthetic.write_bytes(KEY_HEADER + b"\n" + identity + b"\t" + marker + b"\t" + marker + b"\n")
                    failed["isolated_input_id"] = identity.decode("utf-8")
                    failed["reference_error_row"] = str(synthetic)
                    metadata["reference_error_count"] += 1
                    segments.append((begin, end, synthetic))
                    return
                midpoint = begin + (end - begin) // 2
                errors_before = metadata["reference_error_count"]
                unresolved_before = len(metadata["unresolved_signal_ranges"])
                execute_range(begin, midpoint)
                execute_range(midpoint, end)
                if (metadata["reference_error_count"] == errors_before and
                        len(metadata["unresolved_signal_ranges"]) == unresolved_before):
                    metadata["unresolved_signal_ranges"].append({
                        "begin": begin, "end": end, "failed_attempt": failed["attempt"],
                        "signal_number": -failed["returncode"],
                        "outcome": "reference_error_not_reproduced_by_subranges",
                    })

            def execute_range(begin: int, end: int) -> None:
                index = metadata["subprocess_runs"]
                directory = evidence_directory()
                subset = directory / f"attempt-{index:06d}.input.tsv"
                result = directory / f"attempt-{index:06d}.stdout.tsv"
                errors = directory / f"attempt-{index:06d}.stderr.log"
                _copy_range(source, subset, header, offsets[begin], offsets[end])
                attempt = launch(subset, result, errors, begin, end)
                if attempt["returncode"] == 0:
                    if _validate_output(subset, result) != end - begin:
                        raise ReferenceExecutionError("Isolated oracle range has incorrect coverage")
                    metadata["successful_batches"] += 1
                    segments.append((begin, end, result))
                elif attempt["returncode"] > 0:
                    ordinary_failure(attempt)
                else:
                    isolate_failed(begin, end, attempt)

            isolate_failed(0, count, initial)
            merged = evidence_directory() / "merged.tsv"
            next_row = 0
            with merged.open("wb") as destination:
                destination.write(KEY_HEADER + b"\n")
                for begin, end, segment in segments:
                    if begin != next_row:
                        raise ReferenceExecutionError("Isolated oracle segments do not cover the original row order")
                    with segment.open("rb") as stream:
                        if stream.readline().rstrip(b"\r\n") != KEY_HEADER:
                            raise ReferenceExecutionError("Isolated oracle segment has an invalid header")
                        for line in stream:
                            destination.write(line.rstrip(b"\r\n") + b"\n")
                    next_row = end
            if next_row != count or _validate_output(source, merged) != count:
                raise ReferenceExecutionError("Merged oracle output has incomplete coverage")
            merged.replace(output)
            metadata.update(output_rows=count, status="completed")
    except Exception as error:
        preserve_initial()
        metadata["status"] = "execution_error"
        metadata["execution_error"] = {"kind": getattr(error, "kind", type(error).__name__), "message": str(error)}
        save_metadata()
        raise
    save_metadata()
    return metadata
