#!/usr/bin/env python3
"""Validate the fixed ICU77 owner, settings, and script metadata formats."""

import hashlib
from pathlib import Path

from data_format import Reader


def begin(path: Path, magic: bytes):
    source = path.read_bytes()
    reader = Reader(source)
    if reader.take(8) != magic or reader.u32() != 1:
        raise ValueError(f"unrecognized locale data format: {path}")
    if [reader.u32() for _ in range(6)] != [77, 1, 16, 0, 47, 0]:
        raise ValueError("locale data does not have the fixed ICU77 versions")
    return reader, {"bytes": len(source), "sha256": hashlib.sha256(source).hexdigest()}


def finish(reader):
    if reader.offset != len(reader.source):
        raise ValueError("trailing ICU77 locale data")


def read_owner(path: Path):
    reader, data = begin(path, b"BRSOWN77")
    data.update(numeric_primary=reader.u32(), ce32_ranges=reader.ranges("I"),
                ce32s=reader.array("I"), ces=reader.array("Q"),
                raw_contexts=reader.array("H"), jamo_ce32s=reader.array("I"),
                compressible=reader.array("B"))
    if len(data["jamo_ce32s"]) != 67 or len(data["compressible"]) != 256:
        raise ValueError("invalid owner Jamo/compressible table lengths")
    if any(value not in (0, 1) for value in data["compressible"]):
        raise ValueError("invalid owner compression flag")
    contexts = {}
    previous = -1
    for _ in range(reader.u32()):
        index, default = reader.u32(), reader.u32()
        if index <= previous or index + 2 >= len(data["raw_contexts"]):
            raise ValueError("unordered or out-of-range owner context index")
        if default != (data["raw_contexts"][index] << 16) | data["raw_contexts"][index + 1]:
            raise ValueError("decoded owner context differs from raw table")
        previous = index
        entries = [{"utf16": reader.array("H"), "ce32": reader.u32()} for _ in range(reader.u32())]
        if not entries:
            raise ValueError("empty referenced owner context")
        contexts[index] = {"default_ce32": default, "entries": entries}
    data["contexts"] = contexts
    finish(reader)
    return data


def read_settings(path: Path):
    reader, data = begin(path, b"BRSSET77")
    data.update(options=reader.u32(), variable_top=reader.u32(),
                reorder_codes=reader.array("i"), reorder_table=reader.array("B"),
                min_high_no_reorder=reader.u32(), reorder_ranges=reader.array("I"))
    if len(data["reorder_table"]) not in (0, 256):
        raise ValueError("invalid settings reorder table length")
    data["reorder_table"] = data["reorder_table"] or None
    finish(reader)
    return data


def read_scripts(path: Path):
    reader, data = begin(path, b"BRSSCR77")
    data.update(num_scripts=reader.u32(), scripts_index=reader.array("H"),
                script_starts=reader.array("H"))
    if len(data["scripts_index"]) != data["num_scripts"] + 16:
        raise ValueError("invalid script index table length")
    starts = data["script_starts"]
    if len(starts) < 3 or starts[:2] != [0, 0x300] or starts[-1] != 0xFF00:
        raise ValueError("invalid script boundary sentinels")
    if any(left >= right for left, right in zip(starts, starts[1:])):
        raise ValueError("non-increasing script boundaries")
    if any(index >= len(starts) - 1 for index in data["scripts_index"]):
        raise ValueError("script range index outside boundaries")
    finish(reader)
    return data
