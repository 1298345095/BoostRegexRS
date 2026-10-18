# V37 source review of the 115-issue observation

This ledger reconciles `raw.zip` / `sonar-issues.json` with the previous
[91-issue ledger](../v37-triage-fb159eeb/ledger.md). The source baseline inspected
for this delta is `70e9ac1a945d5f2c81f31e3f856e0ec268c5a2a0`; it is not asserted to
be Sonar's analyzed revision. The [observation report](README.md) records the
check timing and unpinned analysis. GitHub issue #18 owns task state.

There are **86 issue objects unchanged after JSON decoding**, **3 changed retained
objects**, **26 added keys** and **2 absent historical keys**. The 86 unchanged
objects use their existing individual source rows. Between the earlier source
baseline and this one, only the collector and its redirect test changed under
`tools/`; the reviewed source of those retained findings did not change. This
delta records all changed/new findings and the absent keys without copying 86
descriptions again. All recorded security flow locations for the new and changed
issues were read; the raw flows stay in the original ZIP.

**FP proposal** means a source-supported recommendation for an individual
service review. No remote disposition has been submitted. Paths below are
relative to the repository; line numbers are the server's reported locations.

## Changed retained objects

| Issue | Rule | Updated source review |
| --- | --- | --- |
| `AaFJiPGXCiUwZk3hyg9M` | python:S1192 | `tools/icu-probe/cloud/prepare.py:113`: relocated repeated `SHASUM512.txt` literal; keep the existing constant-extraction recommendation and exact source filenames. |
| `AaFJiPGXCiUwZk3hyg9N` | python:S1192 | `prepare.py:111`: relocated repeated `.json` literal; retain every generated metadata filename when naming it. |
| `AaFJiPGXCiUwZk3hyg9O` | pythonsecurity:S2083 | `prepare.py:72`, `write_json`: all three updated flows include explicit cache/output selections through `tools/regex-oracle/build_reference.py` and `smoke.py`. Internal names choose manifest/log metadata files; serialized contents do not choose those paths. FP proposal for this metadata-write flow. External caller-selected cache/output paths remain supported. |

## Added security findings

| Issue | Rule | Actual source → sink and caller authority | Source assessment |
| --- | --- | --- | --- |
| `AaFLmrSUrsxYeD3k5M-w` | pythonsecurity:S8701 | `prepare.py:88`, `command_output`; three flows from explicit `--cc`/`--cxx` through prepare/reference build/version commands | The developer deliberately selects the compiler executable. Arguments are a list; no shell evaluates them and no pattern/corpus value selects the executable. FP proposal for these three command-injection flows; retain custom compiler paths and finite process deadlines. |
| `AaFLmrSUrsxYeD3k5M-x` | pythonsecurity:S8701 | `prepare.py:227`, `run_logged` / `Popen`; three compiler-selection flows | The same explicit compiler-execution authority reaches `Popen(..., shell=False)`. A compiler allowlist would remove supported behavior without repairing a demonstrated lower-trust input boundary. FP proposal for the recorded flows. |
| `AaFLmrSUrsxYeD3k5M-y` | pythonsecurity:S8701 | `prepare.py:216`, `subprocess.list2cmdline`; three argv flows | This call formats the command for display; it does not launch a process. The actual launch preserves argv with `shell=False`. FP proposal for the reported display-formatting sink. |
| `AaFLmrSUrsxYeD3k5M-z` | pythonsecurity:S8707 | `prepare.py:72`, `write_json`; four cache/output/log metadata flows | The CLI caller explicitly selects destinations; fixed internal names choose the JSON files. Metadata values are serialized content. FP proposal; preserve output support outside the checkout and evidence-retention behavior. |
| `AaFMLQKFnwwNvcZNUGTD` | pythonsecurity:S6549 | `tools/regex-oracle/build_reference.py:163`; the selected compiler's `-print-prog-name=ld` log → `shutil.which` / resolved linker path; one six-location flow | The caller has already authorized execution of that compiler. Its linker query identifies a tool that is resolved, versioned and hashed; the script exposes no HTTP endpoint or lower-privileged filesystem-query caller. FP proposal based on this actual authority. The S6549 full rule definition remains unavailable in this observation; no final service review is claimed. |

## Added code-quality findings

| Issue | Rule | Source assessment / required behavior |
| --- | --- | --- |
| `AaFLmrSUrsxYeD3k5M-s` | python:S7504 | `prepare.py:49`: keep the `list(ACTIVE_PROCESSES.values())` snapshot. Download worker threads register/remove children; termination iterates while process operations allow concurrent changes. Replacing the snapshot with a live dictionary iterator can invalidate cleanup. Individual FP proposal; no blanket annotation suppression. |
| `AaFLmrSUrsxYeD3k5M-t` | python:S3776 | `prepare.py:197`, `run_logged`: separate launch, deadline/cancellation, child reaping and metadata phases while retaining all lifecycle semantics. Existing timeout/signal regressions must remain. |
| `AaFLmrSUrsxYeD3k5M-u` | python:S3358 | `prepare.py:252`: expand exit-status selection into statements without changing signal, timeout, launch-error and native-return precedence. |
| `AaFLmrSUrsxYeD3k5M-v` | python:S3358 | `prepare.py:253`: apply the same explicit status selection while preserving the stored failure status and diagnostic record. |
| `AaFMLQIfnwwNvcZNUGS-` | cpp:S1181 | `tools/regex-oracle/oracle.cpp:192`, `std::runtime_error` catch: the source audit found a separate real defect before this catch. Matcher complexity/stack failures are `boost::regex_error` and are wrongly classified as compile errors. Repair phase/code classification and add a native regression; do not narrow catches merely to satisfy this style finding. See the upstream evidence below. |
| `AaFMLQIfnwwNvcZNUGS0` | cpp:S6022 | `oracle.cpp:49`: byte-to-hex encoding uses unsigned arithmetic to avoid sign extension. Any `std::byte` conversion must preserve all 256 byte values and the `std::string` transport boundary. |
| `AaFMLQIfnwwNvcZNUGS1` | cpp:S6022 | `oracle.cpp:50`: retain the low-nibble conversion and exact hex case/width when changing byte representation. |
| `AaFMLQIfnwwNvcZNUGS2` | cpp:S6009 | `oracle.cpp:66`, `fields`: a string view must retain the caller's storage lifetime, embedded tabs and trailing empty fields. |
| `AaFMLQIfnwwNvcZNUGS3` | cpp:S134 | `oracle.cpp:97`, `match_json`: extract capture-history serialization while preserving every capture, original range, unmatched flag and history order. |
| `AaFMLQIfnwwNvcZNUGS4` | cpp:S1659 | `oracle.cpp:111`: split the `Request` string declarations without changing field order or default initialization. |
| `AaFMLQIfnwwNvcZNUGS5` | cpp:S1659 | `oracle.cpp:112`: split the unsigned flag declarations while preserving zero defaults and exact flag values. |
| `AaFMLQIfnwwNvcZNUGS6` | cpp:S3628 | `oracle.cpp:140`: a raw replacement-result JSON literal must produce identical bytes. |
| `AaFMLQIfnwwNvcZNUGS7` | cpp:S1659 | `oracle.cpp:146`: declare the iterator and end sentinel separately without changing lifetime or iteration behavior. |
| `AaFMLQIfnwwNvcZNUGS8` | cpp:S3628 | `oracle.cpp:160`: keep the complete format-result JSON transport unchanged when adopting a raw literal. |
| `AaFMLQIfnwwNvcZNUGS9` | cpp:S1181 | `oracle.cpp:187`, `std::logic_error` catch: Boost directly throws this type for incompatible match policies. Preserve its `invalid_match_options` mapping after the earlier `invalid_argument` catch; a narrower catch would miss the actual upstream type. Individual FP proposal for this catch, subject to the complete exception-phase regression. |
| `AaFMLQIfnwwNvcZNUGS_` | cpp:S3628 | `oracle.cpp:200`: preserve metadata JSON keys, version values and punctuation when using a raw literal. |
| `AaFMLQIfnwwNvcZNUGTA` | cpp:S3628 | `oracle.cpp:201`: preserve the coupled metadata JSON continuation and final newline. |
| `AaFMLQJ_nwwNvcZNUGTB` | python:S3776 | `tools/regex-oracle/source_identity.py:15`, `verify_source_tree`: extract member verification while retaining complete archive/member identity, path-set equality, file/link mode rules and duplicate rejection. |
| `AaFMLQKFnwwNvcZNUGTC` | python:S1192 | `tools/regex-oracle/build_reference.py:107`: name `reference-manifest.json`; retain all three current write/read/identity roles. |
| `AaFMLQKNnwwNvcZNUGTE` | python:S6353 | `tools/regex-oracle/protocol.py:11`: replacing `[0-9]` with `\d` is equivalent only while retaining `re.ASCII`; non-ASCII decimal digits must remain rejected. |
| `AaFMLQKNnwwNvcZNUGTF` | python:S3776 | `protocol.py:126`, `result_value`: extract typed status-family validation without loosening exact key sets, bool-versus-int rejection, input ranges, capture data or error payloads. |

### Upstream exception evidence and correction

The first triage assumption was that matcher resource failures directly threw
`std::runtime_error`. Direct reading of the verified official Boost 1.89.0
source disproved that assumption:

| Official archive path | Source fact |
| --- | --- |
| `boost/regex/v5/perl_matcher_non_recursive.hpp:206,216,247` | Matcher complexity and stack limits call `raise_error` with `error_complexity` or `error_stack`. |
| `boost/regex/v5/pattern_except.hpp:82–97` | The helper constructs `regex_error` with the original code and position zero; the templated throw helper preserves that exception type. |
| `boost/regex/v5/perl_matcher.hpp:63,71` | Incompatible Perl/POSIX policies and capture-history/POSIX policies throw `std::logic_error`. |
| `boost/regex/v5/perl_matcher_common.hpp:98` | A regex unsuitable for POSIX matching also throws `std::logic_error`. |

These files were read from the complete, identity-verified Boost source tree of
the [fresh V01 reference build](../../regex-engine/v01-20261017T233138Z/README.md),
whose official archive and complete member manifests establish the source
identity. No upstream source was changed. At the inspected baseline,
`oracle.cpp` catches `boost::regex_error` before `std::runtime_error`, without a
compilation/execution distinction. Consequently the source shows that a matcher
limit takes the `compile_error` branch. This requires a separate source repair
and actual bounded matcher-limit regression; this ledger does not invent that
execution result or count the repair as completed. The correct remedy must
preserve upstream phase, code, position and failure category.

## Historical keys absent from this response

| Issue | Prior flow | Interpretation |
| --- | --- | --- |
| `AaFJiPGXCiUwZk3hyg9Q` | S8701, selected compiler → `prepare.command_output` | Absent from this response. The new three compiler-related keys above are reviewed independently; neither disappearance nor replacement implies remote resolution. |
| `AaFJufvkdzrnai1Efwls` | S8701, selected compiler → `prepare.run_logged` | Absent from this response. Preserve the historical raw issue and its earlier source assessment. |

The retained staged-filename finding is still present in this 115-key
observation. Its later source repair and isolated 11-case test are recorded in
the [observation report](README.md); this older snapshot proves no later Sonar
disposition. All other retained rows preserve their earlier source assessments.

## Verify complete reconciliation

Run from the repository root. This checks every key exactly once in the original
ledger or the changed/new delta, with the two absent keys kept separately. It
does not validate a proposed service disposition or an analysis identity.

```sh
timeout --signal=TERM --kill-after=2s 20s python3 -B - <<'PY'
import json
from pathlib import Path
import re
from zipfile import ZipFile

root = Path('docs/research/assets/sonarcloud')
def issues(directory):
    with ZipFile(root / directory / 'raw.zip') as archive:
        response = json.loads(archive.read('sonar-issues.json'))
    items = response['payload']['issues']
    result = {item['key']: item for item in items}
    assert len(items) == len(result) == response['payload']['paging']['total']
    return result

old = issues('actions-39066906674')
new = issues('actions-39081773775')
unchanged = {key for key in old.keys() & new.keys() if old[key] == new[key]}
changed = old.keys() & new.keys() - unchanged
added = new.keys() - old.keys()
removed = old.keys() - new.keys()
assert (len(old), len(new), len(unchanged), len(changed), len(added), len(removed)) == (91, 115, 86, 3, 26, 2)
original_rows = re.findall(r'^\| `(Aa[^`]+)` \|', (root / 'v37-triage-fb159eeb/ledger.md').read_text(), re.MULTILINE)
delta_rows = re.findall(r'^\| `(Aa[^`]+)` \|', (root / 'actions-39081773775/triage-delta.md').read_text(), re.MULTILINE)
assert len(original_rows) == len(set(original_rows)) == 91
assert set(original_rows) == old.keys()
assert len(delta_rows) == len(set(delta_rows)) == 31
assert set(delta_rows) == changed | added | removed
assert unchanged | (set(delta_rows) - removed) == new.keys()
assert sum(item['rule'].startswith('pythonsecurity:') for item in new.values()) == 23
print('115 keys reconciled: 86 unchanged, 3 updated, 26 added; 2 historical keys absent; all 23 security issues accounted for')
PY
```
