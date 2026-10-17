#!/usr/bin/env python3
"""Read the documented ICU77 development data format, without loading ICU."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct


class Reader:
    def __init__(self, source: bytes):
        self.source = source
        self.offset = 0

    def take(self, size: int) -> bytes:
        end = self.offset + size
        if size < 0 or end > len(self.source):
            raise ValueError(f"truncated ICU77 data at byte {self.offset}")
        result = self.source[self.offset:end]
        self.offset = end
        return result

    def number(self, fmt: str) -> int:
        return struct.unpack("<" + fmt, self.take(struct.calcsize("<" + fmt)))[0]

    def u32(self) -> int:
        return self.number("I")

    def array(self, fmt: str) -> list[int]:
        count = self.u32()
        size = struct.calcsize("<" + fmt)
        return [item[0] for item in struct.iter_unpack("<" + fmt, self.take(count * size))]

    def ranges(self, fmt: str) -> list[tuple[int, int]]:
        count = self.u32()
        size = struct.calcsize("<I" + fmt)
        result = list(struct.iter_unpack("<I" + fmt, self.take(count * size)))
        previous = -1
        for end, _ in result:
            if not previous < end <= 0x10FFFF:
                raise ValueError("invalid ICU77 range order or end")
            previous = end
        if previous != 0x10FFFF:
            raise ValueError("ICU77 ranges do not cover the complete code-point domain")
        return result


def read_data(path: Path) -> dict:
    source = path.read_bytes()
    reader = Reader(source)
    if reader.take(8) != b"BRSPRI77" or reader.u32() != 1:
        raise ValueError("unrecognized ICU77 data format")
    version = [reader.u32() for _ in range(6)]
    if version != [77, 1, 16, 0, 47, 0]:
        raise ValueError(f"unexpected ICU77 versions: {version}")
    data = {
        "sha256": hashlib.sha256(source).hexdigest(),
        "bytes": len(source),
        "primary_options": reader.u32(),
        "variable_top": reader.u32(),
        "numeric_primary": reader.u32(),
        "ce32_ranges": reader.ranges("I"),
        "ce32s": reader.array("I"),
        "ces": reader.array("Q"),
        "raw_contexts": reader.array("H"),
        "jamo_ce32s": reader.array("I"),
        "compressible": reader.array("B"),
        "fcd16_ranges": reader.ranges("H"),
    }
    contexts = {}
    previous_index = -1
    for _ in range(reader.u32()):
        index = reader.u32()
        if index <= previous_index or index + 2 >= len(data["raw_contexts"]):
            raise ValueError("unordered or out-of-range context index")
        previous_index = index
        default = reader.u32()
        if default != (data["raw_contexts"][index] << 16) | data["raw_contexts"][index + 1]:
            raise ValueError("decoded context default does not match the raw table")
        entries = []
        for _ in range(reader.u32()):
            key = reader.array("H")
            value = reader.u32()
            entries.append({"utf16": key, "ce32": value})
        contexts[index] = {"default_ce32": default, "entries": entries}
    if reader.offset != len(source):
        raise ValueError("trailing ICU77 data")
    if len(data["jamo_ce32s"]) != 67 or len(data["compressible"]) != 256:
        raise ValueError("unexpected ICU77 Jamo or compression table length")
    if any(flag not in (0, 1) for flag in data["compressible"]):
        raise ValueError("invalid compression flag")
    data["contexts"] = contexts
    return data


def codepoints(units: list[int]) -> list[int]:
    """Decode valid UTF-16 pairs, preserving lone surrogates as input units."""
    result = []
    index = 0
    while index < len(units):
        lead = units[index]
        index += 1
        if 0xD800 <= lead <= 0xDBFF and index < len(units):
            trail = units[index]
            if 0xDC00 <= trail <= 0xDFFF:
                result.append(0x10000 + ((lead - 0xD800) << 10) + trail - 0xDC00)
                index += 1
                continue
        result.append(lead)
    return result


def context_report(data: dict) -> dict:
    triggers = []
    start = 0
    for end, ce32 in data["ce32_ranges"]:
        if (ce32 & 0xFF) >= 0xC0 and (ce32 & 15) in (8, 9):
            triggers.extend(
                {
                    "codepoint": cp,
                    "ce32": ce32,
                    "tag": ce32 & 15,
                    "flags": ce32 & 0x1F00,
                    "context_index": ce32 >> 13,
                }
                for cp in range(start, end + 1)
            )
        start = end + 1
    return {
        "schema": 1,
        "binary_sha256": data["sha256"],
        "triggers": triggers,
        "contexts": [
            {
                "index": index,
                "default_ce32": context["default_ce32"],
                "entries": [
                    {**entry, "codepoints": codepoints(entry["utf16"])}
                    for entry in context["entries"]
                ],
            }
            for index, context in data["contexts"].items()
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data", type=Path)
    parser.add_argument("--contexts-output", type=Path, required=True)
    args = parser.parse_args()
    data = read_data(args.data)
    args.contexts_output.parent.mkdir(parents=True, exist_ok=True)
    args.contexts_output.write_text(
        json.dumps(context_report(data), indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    print(f"decoded {len(data['contexts'])} context tries from {data['bytes']} bytes")


if __name__ == "__main__":
    main()
