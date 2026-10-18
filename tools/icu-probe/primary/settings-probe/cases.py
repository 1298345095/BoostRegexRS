"""Source-derived ICU77 public reorder lists and representative input scalars.

No reference keys or host Unicode database participate in input selection.
Script groups and their primary boundaries come from the fixed export. CE32
inspection selects witnesses; it does not provide the expected sorting keys.
"""

from bisect import bisect_right
from collections import Counter, defaultdict

from generate_cases import Random


SEED = 0x554F3352454F5244
OTHERS = 103
DEFAULT = -1
SPECIALS = list(range(4096, 4101))


def index_for(scripts, code):
    if 0 <= code < scripts["num_scripts"]:
        return scripts["scripts_index"][code]
    if 4096 <= code < 4112:
        return scripts["scripts_index"][scripts["num_scripts"] + code - 4096]
    return 0


def primary_groups(root, ce32, codepoint, depth=0):
    """Select groups from exported CE32 payloads, including algorithmic tags."""
    if depth > 8:
        raise ValueError("Unexpected recursive CE32 data while choosing witnesses")
    if ce32 & 0xFF < 0xC0:
        return [ce32 & 0xFFFF0000]
    tag, index, length = ce32 & 15, ce32 >> 13, (ce32 >> 8) & 31
    if tag == 1:
        return [ce32 & 0xFFFFFF00]
    if tag == 4:
        return [ce32 & 0xFF000000]
    if tag == 5:
        return [primary for child in root["ce32s"][index:index + length]
                for primary in primary_groups(root, child, codepoint, depth + 1)]
    if tag == 6:
        return [ce >> 32 for ce in root["ces"][index:index + length]]
    if tag in (8, 9):
        return primary_groups(root, root["contexts"][index]["default_ce32"], codepoint, depth + 1)
    if tag in (10, 11):
        return primary_groups(root, root["ce32s"][index if tag == 10 else 0], codepoint, depth + 1)
    if tag == 12 and 0xAC00 <= codepoint <= 0xD7A3:
        leading, trailing = divmod(codepoint - 0xAC00, 28)
        leading, vowel = divmod(leading, 21)
        indices = [leading, 19 + vowel] + ([39 + trailing] if trailing else [])
        return [primary for item in indices
                for primary in primary_groups(root, root["jamo_ce32s"][item], codepoint, depth + 1)]
    if tag == 14:
        # The offset CE stores the three-byte base primary in its high word;
        # its scalar offset stays within that script's range.
        return [root["ces"][index] >> 32]
    if tag == 15:
        return [0xFE000000]  # ICU77 unassigned implicit primary lead.
    return []


def representatives(root, scripts):
    witnesses = defaultdict(list)
    start = 0
    for end, ce32 in root["ce32_ranges"]:
        for cp in sorted({start, end}):
            if not 0xD800 <= cp <= 0xDFFF:
                for primary in primary_groups(root, ce32, cp):
                    if primary:
                        index = bisect_right(scripts["script_starts"], primary >> 16) - 1
                        if 0 < index < len(scripts["script_starts"]) - 1:
                            witnesses[index].append((primary, cp, ce32))
        start = end + 1
    public = list(range(scripts["num_scripts"])) + SPECIALS
    needed = {index_for(scripts, code) for code in public} - {0}
    missing = sorted(needed - witnesses.keys())
    if missing:
        raise ValueError(f"No source primary witness for public script groups: {missing}")
    result = {}
    for index in sorted(needed):
        selected = sorted({min(witnesses[index]), max(witnesses[index])})
        result[index] = [{"primary_payload": f"{primary:08x}", "scalar": cp,
                          "ce32": f"{ce32:08x}"} for primary, cp, ce32 in selected]
    return result


def reordered_cases(root, scripts, smoke=False):
    witnesses = representatives(root, scripts)
    public = list(range(scripts["num_scripts"])) + SPECIALS
    palette = [DEFAULT, *public]
    equivalent = defaultdict(list)
    for code in public:
        if index := index_for(scripts, code):
            equivalent[index].append(code)
    canonical = [values[0] for _, values in sorted(equivalent.items()) if values[0] != OTHERS]
    control = " aA\u03b1\u0410\u4e00\uac00\u0378\0a\u0327\u0301\ufffe"
    all_text = "".join(chr(w["scalar"]) for group in witnesses.values() for w in group) + control
    setups = [None, [14, 25], [OTHERS, 25]]
    values = []

    def add(name, requested, setup=None, complete=False):
        if complete:
            text = all_text
        else:
            groups = dict.fromkeys(index_for(scripts, code) for code in requested or [])
            text = "".join(chr(w["scalar"]) for index in groups for w in witnesses.get(index, [])) + control
        values.append({"case_id": name, "setup": setup, "requested": requested, "text": text})

    for setup_id, setup in enumerate(setups):
        for name, requested in (("retain", None), ("reset", []), ("default", [DEFAULT]),
                                ("none", [OTHERS]), ("others_first", [OTHERS, 25, 14]),
                                ("others_middle", [25, OTHERS, 14]), ("others_last", [25, 14, OTHERS])):
            add(f"control/{setup_id}/{name}", requested, setup, True)
    for code in palette:
        add(f"singleton/{code}", [code], [14, 25], True)
    for left in palette:
        for right in palette:
            add(f"pair/{left}/{right}", [left, right], setups[(left + right) % len(setups)])
    # Values outside the public enum, including reserved range slots, exercise
    # the documented ignored/illegal behavior. INT32_MIN is deliberately absent:
    # ICU77's code-FIRST prepass would overflow signed int32 outside its domain.
    for value in (-2, scripts["num_scripts"], 4095, 4101, 4110, 4111, 4112, 0x7FFFFFFF):
        for suffix, requested in (("single", [value]), ("duplicate", [value, value]),
                                  ("before", [value, 25]), ("after", [25, value]),
                                  ("others", [OTHERS, value]), ("default", [value, DEFAULT])):
            add(f"outside/{value}/{suffix}", requested, [14, 25], True)
    random = Random(SEED)
    lengths = [0, 1, 2, 3, 4, 8, 16, 31, 32, 64, 128, len(canonical)]
    for trial in range(384):
        codes = canonical.copy()
        for index in range(len(codes) - 1, 0, -1):
            other = random.next() % (index + 1)
            codes[index], codes[other] = codes[other], codes[index]
        length = lengths[trial % len(lengths)] if trial < 192 else len(codes)
        codes = codes[:length]
        if trial % 3 == 1:
            codes.insert(random.next() % (len(codes) + 1), OTHERS)
        if trial % 11 == 1 and codes:
            codes.insert(random.next() % (len(codes) + 1), codes[0])
        if trial % 17 == 1:
            codes.append(DEFAULT)
        add(f"long/{trial:04d}", codes, setups[trial % len(setups)], True)
    if smoke:
        wanted_pairs = {(-1, 25), (25, -1), (103, 103), (25, 25), (20, 22),
                        (25, 14), (14, 25), (0, 0), (4096, 4096), (103, 25), (25, 103)}
        values = [item for item in values if item["case_id"].startswith("control/")
                  or item["case_id"] in {f"pair/{left}/{right}" for left, right in wanted_pairs}
                  or item["case_id"].startswith("outside/")
                  or item["case_id"] in {"singleton/0", "singleton/103", "singleton/4096",
                                         "long/0011", "long/0192", "long/0383"}]
    manifest = {
        "schema": "boostregexrs.icu77-reorder-inputs.v1", "scope": "diagnostic_smoke" if smoke else "complete_public_code_matrix",
        "seed": f"0x{SEED:016x}", "random_algorithm": "SplitMix64", "public_scripts": list(range(scripts["num_scripts"])),
        "public_special_groups": SPECIALS, "ordered_pair_palette": palette,
        "ordered_pair_count": sum(item["case_id"].startswith("pair/") for item in values),
        "expected_complete_ordered_pair_count": len(palette) ** 2,
        "equivalent_groups": dict(equivalent), "primary_witnesses_by_group": witnesses,
        "split_group_indices": [i for i in equivalent if (scripts["script_starts"][i] | scripts["script_starts"][i + 1]) & 255],
        "case_categories": dict(Counter(item["case_id"].split("/")[0] for item in values)),
        "case_count": len(values), "host_unicode_database_used": False,
        "reference_keys_used_to_choose_inputs": False, "unicode_normalization_performed": False,
        "not_covered": ["INT32_MIN outside ICU77's safe reorder-code arithmetic domain",
                        "locale ID resolution (profiles select explicit exported settings)"]}
    return values, manifest


def write_inputs(path, values):
    with path.open("w", encoding="utf-8", newline="") as stream:
        stream.write("case_id\tsetup_codes\trequest_codes\tu16_hex\n")
        for item in values:
            lists = ["~" if item[field] is None else ",".join(map(str, item[field])) for field in ("setup", "requested")]
            encoded = item["text"].encode("utf-16-le")
            units = ",".join(f"{int.from_bytes(encoded[i:i + 2], 'little'):04x}" for i in range(0, len(encoded), 2))
            stream.write(f"{item['case_id']}\t{lists[0]}\t{lists[1]}\t{units}\n")
