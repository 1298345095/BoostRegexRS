# V03 native reference error classification

This is a verified, limited correction to the development reference and its
independent comparator. It does not complete V03 or claim complete library,
platform, resource-threshold, or performance compatibility.

The subsequent [no-except flow correction](../v03-no-except-flow-20261018T015213Z/README.md)
retains a returned invalid compiled object's status alongside its later operation
error. That independent follow-up preserves this report's original rows and
105-member archive and supplies the original collector's missing generator
dependency separately.

## Finding and source mechanism

Official Boost 1.89.0's `boost/regex/v5/pattern_except.hpp` defines
`boost::regex_error` as a `std::runtime_error` subclass. Its templated
`raise_runtime_error` preserves the derived type. In
`perl_matcher_non_recursive.hpp`, both the recursion/state guards
(`error_complexity`, lines 206/216) and the stack-block guard (`error_stack`,
line 247) therefore reach the old oracle's `regex_error` handler, which labeled
every such exception `compile_error`.

The same error family can occur during compilation. The fixed parser's
`parse_all` rejects nesting beyond 400 with `error_complexity`; the creator's
`create_startmap` also has a complexity guard. Conversely, ordinary
`std::runtime_error` in `cpp_regex_traits.hpp` can mean a message-catalog
failure. An exception-type-only classification is insufficient.

The repaired oracle tracks the actual native API phase and distinguishes it
from result serialization. A new `reference_failure` record has exactly:

```json
{
  "schema": "boostregexrs.reference-failure.v1",
  "phase": "search",
  "kind": "regex_resource",
  "code": 18,
  "position": 0,
  "message_hex": "426f6f7374"
}
```

The illustrative message above encodes `Boost`; the raw records retain the
complete original message. `code` and `position` come directly from
`boost::regex_error`. Allocation,
capacity, and plain C++ runtime exceptions retain null fields because those
types do not expose a Boost code or pattern position. Ordinary compile syntax
errors retain the existing `compile_error` record. Historical message-only
`reference_resource_error` records remain recognizable and cannot pass.

The comparator treats native resource codes 12, 15, 18, and 19 as unavailable
reference observations. This also applies to `no_except` compiled objects whose
actual `compile_status` reports a resource limit: their full original payload
is retained. Matching resource failures on both sides cannot establish
compatibility; ADR-0003 gives the Rust library its own limits.

## Actual observations

The fixed `resource_cases.py` generator produced 12 inputs. No expected output
was obtained from the candidate. `verify_resource_errors.py` independently
checked the retained original and corrected native rows.

| Observation | Original reference | Corrected reference |
| --- | --- | --- |
| Ordinary invalid pattern | `compile_error`, code 8, position 1 | Unchanged |
| Nesting limit during compilation | `compile_error`, code 18, position 400 | `reference_failure`, phase `compile`, kind `regex_resource` |
| State limit during search | `compile_error`, code 18, position 0 | `reference_failure`, phase `search` |
| State limit during full match | `compile_error`, code 18, position 0 | `reference_failure`, phase `match` |
| State limit during iteration | `compile_error`, code 18, position 0 | `reference_failure`, phase `iterate` |
| State limit before formatting | `compile_error`, code 18, position 0 | `reference_failure`, phase `search` |
| State limit inside replacement | `compile_error`, code 18, position 0 | `reference_failure`, phase `replace` |
| Separate linear stack-block limit | `compile_error`, code 19, position 0 | `reference_failure`, phase `match`, kind `regex_resource` |
| Normal/no-except compiled objects and invalid-operation results | Original complete fields | Unchanged |

In the original 12-case corpus, six classifications were corrected and six
other result records were unchanged. The new native run retained all 12 rows:
1 ordinary compile error, 3 compiled
object observations, 2 operation errors, and 6 explicit reference failures.
The collector returned **1**, with `complete_with_errors`, as required for
these deliberately failing inputs.

A deliberately identical-result comparison returned **1** and independently
counted 7 reference resource observations: the 6 exceptions plus the no-except
compile status. Its other outcomes were 2 ordinary passes, 1 matching compile
rejection, and 2 matching operation rejections. It did not mark the corpus as
passed merely because both supplied output files were identical.

A separate input, `^(((a)))*$` over 60,000 ASCII `a` bytes, reached the unchanged
native stack-block budget. The original binary returned `compile_error` with
code 19 and position 0. The corrected binary returned `reference_failure` with
phase `match`, kind `regex_resource`, and the same code and position. Its
collector also returned **1**, preserving the failure. The independent stack
verification passed. These two runs contain 13 distinct source-defined probes;
seven thrown-error classifications were corrected overall. The stack result
was obtained using the already-built correction, without changing resource
macros or modifying the native implementation after the complexity probes.

The normal V01 byte corpus was separately replayed through the new native
binary. Full comparison with the previously measured Rust adapter produced
12 ordinary passes and 1 matching compile rejection, covering compile, search,
full match, captures/history, iteration, formatting, and replacement.

Eight focused reference-failure tests and nine existing complete-result
comparison tests passed. The scoped `git diff --check` passed. No tests were
removed, weakened, or skipped to obtain these results.

## Environment and retained evidence

This run reused the verified official Boost sources from the clean V01 build
at `fb159eeb4583727cc70db4b9e53f8329fd25d8b8`; it rebuilt only the native byte
oracle. It is not a second claim of downloading/building Boost and ICU from an
empty cache. The byte oracle uses the classic C locale and does not use ICU
collation at runtime. V01's independent ICU/Unicode/CLDR identity remains in
the [published source evidence](../v01-20261017T233138Z/).

The compiler was GCC 13.3.0 (`Ubuntu 13.3.0-6ubuntu2~24.04`) on Linux x86-64.
Compilation used C++17, `-O2 -g0 -Wall -Wextra -Werror -pthread`, with the
official Boost include directory and no resource-macro overrides. Compiler,
ELF, linker, metadata, raw process output, command argv, and deadlines are
retained with the run. Full original and corrected native binaries are also
retained in `retained/raw.tar.xz` so this failure does not depend on future cache
survival.

The old byte binary SHA-256 is
`4ee12d76046bfd6da2dd58defdd33b3368386f61a5a2f3e31f15f14c111e3a30`.
The corrected byte binary SHA-256 is
`6d765d61e1bd6441b8b75510bfdadb2a1233cc53382c631a1222f250cdc26ca7`.

Compact reports are [verification.json](verification.json),
[stack-verification.json](stack-verification.json),
[normal-comparison/summary.json](normal-comparison/summary.json), and
[resource-non-pass/summary.json](resource-non-pass/summary.json).
The immutable original and corrected raw observations are under `before/`
and `after/` in the archive. Archive/member identities are recorded separately
in [retained/manifest.json](retained/manifest.json); expanded local working
copies are not an additional publication requirement. The existing
`tools/icu-probe/primary/archive_evidence.py` creates and independently verifies
the archive. Its [verification record](retained/verification.json) includes
the actual member count and archive digest. Archive paths use `run/` for raw
observations, `native-before/` and `native-after/` for both binaries and their
native sources, and `validation-source/` for the exact validation scripts.

## Reproduce

From the repository root, use a verified Boost 1.89.0 cache produced by the
committed V01 recipe. Build products belong under `target`; generators and
verification scripts remain under `tools/regex-oracle`.

```bash
timeout --signal=TERM --kill-after=5s 20s python3 -B tools/regex-oracle/resource_cases.py --output NEW_EVIDENCE/cases.tsv
timeout --signal=TERM --kill-after=10s 120s c++ -std=c++17 -O2 -g0 -Wall -Wextra -Werror -I/VERIFIED_CACHE/deps/boost_1_89_0 tools/regex-oracle/oracle.cpp -pthread -o target/research/byte-reference
timeout --signal=TERM --kill-after=5s 45s python3 -B tools/regex-oracle/run.py --program target/research/byte-reference --role reference --cases NEW_EVIDENCE/cases.tsv --output NEW_EVIDENCE/after --batch-size 16 --timeout 5 --source tools/regex-oracle/oracle.cpp
timeout --signal=TERM --kill-after=5s 20s python3 -B tools/regex-oracle/verify_resource_errors.py --cases NEW_EVIDENCE/cases.tsv --before ORIGINAL_EVIDENCE/before/results.tsv --after NEW_EVIDENCE/after/results.tsv --output NEW_EVIDENCE/verification.json
timeout --signal=TERM --kill-after=5s 20s python3 -B tools/regex-oracle/resource_cases.py --stack-only --output NEW_EVIDENCE/stack-cases.tsv
timeout --signal=TERM --kill-after=5s 45s python3 -B tools/regex-oracle/run.py --program target/research/byte-reference --role reference --cases NEW_EVIDENCE/stack-cases.tsv --output NEW_EVIDENCE/stack-after --batch-size 1 --timeout 5 --source tools/regex-oracle/oracle.cpp
timeout --signal=TERM --kill-after=5s 20s python3 -B tools/regex-oracle/verify_resource_errors.py --stack-only --cases NEW_EVIDENCE/stack-cases.tsv --before ORIGINAL_EVIDENCE/stack-before/results.tsv --after NEW_EVIDENCE/stack-after/results.tsv --output NEW_EVIDENCE/stack-verification.json
timeout --signal=TERM --kill-after=5s 30s python3 -B tools/icu-probe/primary/archive_evidence.py --verify docs/research/assets/regex-engine/v03-reference-errors-20261018T005707Z/retained
timeout --signal=TERM --kill-after=5s 20s python3 -B -m unittest discover -s tools/regex-oracle -p 'test_*failures.py' -v
timeout --signal=TERM --kill-after=5s 20s python3 -B -m unittest discover -s tools/regex-oracle -p test_comparison.py -v
```

The error-corpus collector's nonzero exit is expected and must be preserved.
The verifier succeeds only when the complete original/new rows and native
phase/code changes match this documented source mechanism: 12 base probes or
the separate single stack probe. Use a new evidence
directory for every observation. Exact commands used for this run are in its
process records; the uppercase placeholders above identify caller-selected
new paths.

## Remaining coverage

Allocator exhaustion, container capacity exhaustion, and catalog failure were not
induced in the native run. Their distinct envelope shapes and classifications
were validated by bounded protocol tests; that is not native execution proof.
Creator start-map complexity was inspected in source but not separately
induced from parser nesting complexity.

V03's wider work remains open: explicit named queries, complete versioned
result coverage, immutable run contracts and independent artifact attribution,
retained iteration observations before errors, and attribution-aware byte and
collation comparison. The legacy collector used here preserves raw commands,
binary/source hashes and process results, but it is not the planned complete
V03 identity-binding gate. The Rust byte API adapter is a separate pending
publication group and no root engine source was changed by this correction.
