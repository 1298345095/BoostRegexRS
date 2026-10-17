Part of #2. **Implementation is paused at the user's request.** This index records the remaining work using `to-tickets`; publishing tickets does not resume implementation.

The backlog contains **145 bounded tickets**, owns all **406 existing capability rows**, and has **794 explicit dependency links**. All tickets reach the final acceptance gate [#147](https://github.com/1298345095/BoostRegexRS/issues/147). Each of the 73 upstream source files has one full-file applicability, port and test owner.

## Contract and current boundary

The complete standalone pure Rust Boost.Regex 1.89.0 contract remains unchanged: ICU4C 77.1 / Unicode 16.0.0 / CLDR 47 data, stable Rust, full default capability, all captures and original positions, ADR errors/resources/sharing, six actual native targets, per-workload time/memory limits, public documentation and clean-checkout acceptance. Only ADR-approved compatibility exceptions apply. Main merge, release publication and librime-rs integration remain outside the work.

Root PRIMARY/IDENTICAL research evidence is retained as an existing prerequisite. The byte engine and locale work are unfinished checkpoints, including two preserved locale full-key differences and an unbuilt/untested FCD repair. Six native research jobs passed 19 tests each; they do not establish whole-library or performance acceptance. Sonar's actual remote quality gate remains an explicit outstanding requirement.

Repository index: [README](https://github.com/1298345095/BoostRegexRS/blob/work/root-primary-cloud/docs/development/tickets/README.md). Full capability ownership: [coverage](https://github.com/1298345095/BoostRegexRS/blob/work/root-primary-cloud/docs/development/tickets/coverage.md). Paused source/evidence: [checkpoint](https://github.com/1298345095/BoostRegexRS/blob/work/root-primary-cloud/docs/development/tickets/checkpoint/README.md). Persistent continuation: [handoff](https://github.com/1298345095/BoostRegexRS/blob/work/root-primary-cloud/docs/development/handoff.md).

## Workstreams

| Workstream | Tickets |
| --- | ---: |
| Delivery prerequisites | 9 |
| Fixed Unicode and ICU locale behavior | 26 |
| Reference and evidence infrastructure | 3 |
| Sonar and code quality | 3 |
| Byte regex and public operations | 40 |
| Input adapters and migration | 10 |
| Resources and delivery semantics | 4 |
| Compatibility and independent testing | 16 |
| Performance and memory acceptance | 10 |
| Native and custom character rules | 12 |
| Native API integration | 1 |
| Six native platform acceptance | 7 |
| Documentation and final package acceptance | 4 |

## Unblocked after the user resumes

`ready-for-agent` describes specification and dependency readiness only; the pause still applies.

- [#3](https://github.com/1298345095/BoostRegexRS/issues/3) `P01` — Verify the installed Sonar connection and project permissions
- [#4](https://github.com/1298345095/BoostRegexRS/issues/4) `P02` — Locate and identify the consumer patch and supplemental corpus
- [#5](https://github.com/1298345095/BoostRegexRS/issues/5) `U01` — Finish the ICU77 UTF-16 FCD cursor and contraction replay repair
- [#6](https://github.com/1298345095/BoostRegexRS/issues/6) `U05` — Implement ICU77 legacy locale-name parsing and keyword syntax
- [#7](https://github.com/1298345095/BoostRegexRS/issues/7) `U15` — Implement callable Unicode simple case and syntax character rules
- [#8](https://github.com/1298345095/BoostRegexRS/issues/8) `V01` — Reproduce the pinned official native reference from a clean checkout
- [#9](https://github.com/1298345095/BoostRegexRS/issues/9) `V02` — Preserve and verify the complete historical evidence ledger
- [#10](https://github.com/1298345095/BoostRegexRS/issues/10) `V38` — Make whole-library format, lint, build and documentation checks reproducible

## Dependency-ordered ticket list

Each ticket contains its current checkpoint, source contracts, public behavior, scope, binary acceptance checklist and `Blocked by` issue links. Blockers were created first. The repository's documented text-link fallback is used because native dependency mutation is not exposed by the connected toolset. Parent #2 is open and unchanged; its older continuation text is superseded by the user's latest pause.

- [ ] [#3](https://github.com/1298345095/BoostRegexRS/issues/3) **P01** — Verify the installed Sonar connection and project permissions
- [ ] [#4](https://github.com/1298345095/BoostRegexRS/issues/4) **P02** — Locate and identify the consumer patch and supplemental corpus
- [ ] [#5](https://github.com/1298345095/BoostRegexRS/issues/5) **U01** — Finish the ICU77 UTF-16 FCD cursor and contraction replay repair
- [ ] [#6](https://github.com/1298345095/BoostRegexRS/issues/6) **U05** — Implement ICU77 legacy locale-name parsing and keyword syntax
- [ ] [#7](https://github.com/1298345095/BoostRegexRS/issues/7) **U15** — Implement callable Unicode simple case and syntax character rules
- [ ] [#8](https://github.com/1298345095/BoostRegexRS/issues/8) **V01** — Reproduce the pinned official native reference from a clean checkout
- [ ] [#9](https://github.com/1298345095/BoostRegexRS/issues/9) **V02** — Preserve and verify the complete historical evidence ledger
- [ ] [#10](https://github.com/1298345095/BoostRegexRS/issues/10) **V38** — Make whole-library format, lint, build and documentation checks reproducible
- [ ] [#11](https://github.com/1298345095/BoostRegexRS/issues/11) **U02** — Accept published tailoring owners through complete CE and key sequences
- [ ] [#12](https://github.com/1298345095/BoostRegexRS/issues/12) **U03** — Accept effective settings, numeric collation and script reordering
- [ ] [#13](https://github.com/1298345095/BoostRegexRS/issues/13) **U06** — Implement ICU77 BCP47 language-tag grammar and legacy-name conversion
- [ ] [#14](https://github.com/1298345095/BoostRegexRS/issues/14) **U16** — Implement Unicode category and special class-mask membership
- [ ] [#15](https://github.com/1298345095/BoostRegexRS/issues/15) **U18** — Implement Unicode digit values and iterator-consuming integer conversion
- [ ] [#16](https://github.com/1298345095/BoostRegexRS/issues/16) **U19** — Implement formal and algorithmic Unicode character-name lookup
- [ ] [#17](https://github.com/1298345095/BoostRegexRS/issues/17) **V03** — Make the differential protocol reject incomplete or misattributed results
- [ ] [#18](https://github.com/1298345095/BoostRegexRS/issues/18) **V37** — Resolve Sonar findings at their actual trust and code boundaries
- [ ] [#19](https://github.com/1298345095/BoostRegexRS/issues/19) **P03** — Run the fixed native reference and a Rust tracer on Ubuntu 24.04 x86-64 / glibc
- [ ] [#20](https://github.com/1298345095/BoostRegexRS/issues/20) **P04** — Run the fixed native reference and a Rust tracer on Ubuntu 24.04 ARM64 / glibc
- [ ] [#21](https://github.com/1298345095/BoostRegexRS/issues/21) **P05** — Run the fixed native reference and a Rust tracer on Windows Server 2025 x86-64 / MSVC
- [ ] [#22](https://github.com/1298345095/BoostRegexRS/issues/22) **P06** — Run the fixed native reference and a Rust tracer on Windows 11 ARM64 / MSVC
- [ ] [#23](https://github.com/1298345095/BoostRegexRS/issues/23) **P07** — Run the fixed native reference and a Rust tracer on macOS 15 Intel
- [ ] [#24](https://github.com/1298345095/BoostRegexRS/issues/24) **P08** — Run the fixed native reference and a Rust tracer on macOS 15 Apple Silicon
- [ ] [#25](https://github.com/1298345095/BoostRegexRS/issues/25) **B01** — Complete Perl and literal lexical grammar with scoped modifiers
- [ ] [#26](https://github.com/1298345095/BoostRegexRS/issues/26) **B02** — Complete basic, grep and sed pattern grammar
- [ ] [#27](https://github.com/1298345095/BoostRegexRS/issues/27) **B04** — Complete extended, egrep and awk grammar variations
- [ ] [#28](https://github.com/1298345095/BoostRegexRS/issues/28) **B05** — Complete classic-C byte escapes, properties and dot behavior
- [ ] [#29](https://github.com/1298345095/BoostRegexRS/issues/29) **B32** — Complete formatter numeric conversion and entrypoint trait routing
- [ ] [#30](https://github.com/1298345095/BoostRegexRS/issues/30) **U04** — Expand the production library with the verified fixed-data collation service
- [ ] [#31](https://github.com/1298345095/BoostRegexRS/issues/31) **U07** — Resolve BCP47 Unicode keyword and type aliases using fixed ICU data
- [ ] [#32](https://github.com/1298345095/BoostRegexRS/issues/32) **U17** — Implement Boost ICU class-name aliases and normalization
- [ ] [#33](https://github.com/1298345095/BoostRegexRS/issues/33) **U20** — Complete extended names, POSIX collating names and single-value fallback
- [ ] [#34](https://github.com/1298345095/BoostRegexRS/issues/34) **I01** — Expand the engine with an input and character-rule seam while preserving byte behavior
- [ ] [#35](https://github.com/1298345095/BoostRegexRS/issues/35) **R01** — Specify and implement independent compile-work and compile-memory limits
- [ ] [#36](https://github.com/1298345095/BoostRegexRS/issues/36) **V13** — Freeze bounded generation, fuzz and minimization execution profiles
- [ ] [#37](https://github.com/1298345095/BoostRegexRS/issues/37) **V27** — Freeze the six-platform performance and memory measurement protocol
- [ ] [#38](https://github.com/1298345095/BoostRegexRS/issues/38) **V39** — Obtain and archive the remote quality gate for the exact candidate
- [ ] [#39](https://github.com/1298345095/BoostRegexRS/issues/39) **B03** — Complete Emacs grammar and its Perl matching mode
- [ ] [#40](https://github.com/1298345095/BoostRegexRS/issues/40) **B06** — Complete ordinary byte bracket-set compilation and matching
- [ ] [#41](https://github.com/1298345095/BoostRegexRS/issues/41) **B08** — Complete capture declaration numbering and named group resolution
- [ ] [#42](https://github.com/1298345095/BoostRegexRS/issues/42) **B10** — Complete generic repeat parsing and counter execution
- [ ] [#43](https://github.com/1298345095/BoostRegexRS/issues/43) **B34** — Complete formatter escapes, sed mode and output case state
- [ ] [#44](https://github.com/1298345095/BoostRegexRS/issues/44) **U08** — Resolve locale resources, aliases, parents and collation-type fallback
- [ ] [#45](https://github.com/1298345095/BoostRegexRS/issues/45) **N01** — Implement custom character rules through compile, sets and matching
- [ ] [#46](https://github.com/1298345095/BoostRegexRS/issues/46) **V12** — Establish the consumer-patched Windows reference relationship
- [ ] [#47](https://github.com/1298345095/BoostRegexRS/issues/47) **B07** — Complete classic-C long bracket sets and collating elements
- [ ] [#48](https://github.com/1298345095/BoostRegexRS/issues/48) **B09** — Expose saved subexpression source locations
- [ ] [#49](https://github.com/1298345095/BoostRegexRS/issues/49) **B11** — Complete ordered alternatives and capture register rollback
- [ ] [#50](https://github.com/1298345095/BoostRegexRS/issues/50) **U09** — Apply arbitrary collation keyword settings and script-name reordering
- [ ] [#51](https://github.com/1298345095/BoostRegexRS/issues/51) **I05** — Expand native-wide input and positions through deterministic character rules
- [ ] [#52](https://github.com/1298345095/BoostRegexRS/issues/52) **N09** — Support custom character-rule locale ownership and lifecycle
- [ ] [#53](https://github.com/1298345095/BoostRegexRS/issues/53) **N10** — Support custom syntax, escape and numeric character-rule extensions
- [ ] [#54](https://github.com/1298345095/BoostRegexRS/issues/54) **B12** — Complete numeric and named backreference matching
- [ ] [#55](https://github.com/1298345095/BoostRegexRS/issues/55) **B15** — Complete lookaround scope execution and fixed-width lookbehind
- [ ] [#56](https://github.com/1298345095/BoostRegexRS/issues/56) **B22** — Complete bounded byte search, previous context and anchor semantics
- [ ] [#57](https://github.com/1298345095/BoostRegexRS/issues/57) **U10** — Expose complete arbitrary-locale construction with reproducible diagnostics
- [ ] [#58](https://github.com/1298345095/BoostRegexRS/issues/58) **N02** — Enforce compiled-regex sharing and per-invocation state ownership
- [ ] [#59](https://github.com/1298345095/BoostRegexRS/issues/59) **N03** — Implement C-locale byte and wide character rules on Linux glibc
- [ ] [#60](https://github.com/1298345095/BoostRegexRS/issues/60) **N05** — Implement Darwin C-locale character rules
- [ ] [#61](https://github.com/1298345095/BoostRegexRS/issues/61) **N06** — Implement Windows MSVC C-locale character rules
- [ ] [#62](https://github.com/1298345095/BoostRegexRS/issues/62) **N07** — Implement Windows NLS wide-character traits and locale lifecycle
- [ ] [#63](https://github.com/1298345095/BoostRegexRS/issues/63) **B13** — Complete compiled start maps, nullability and search restart analysis
- [ ] [#64](https://github.com/1298345095/BoostRegexRS/issues/64) **B16** — Complete atomic groups and possessive repetition
- [ ] [#65](https://github.com/1298345095/BoostRegexRS/issues/65) **U11** — Implement Linux ICU default-locale queries and atomic imbue state
- [ ] [#66](https://github.com/1298345095/BoostRegexRS/issues/66) **U14** — Carry the approved empty-key exception through configured production traits
- [ ] [#67](https://github.com/1298345095/BoostRegexRS/issues/67) **N04** — Implement libstdc++ locale-traits behavior on Linux glibc
- [ ] [#68](https://github.com/1298345095/BoostRegexRS/issues/68) **N08** — Implement Windows NLS byte and codepage behavior
- [ ] [#69](https://github.com/1298345095/BoostRegexRS/issues/69) **N11** — Implement libc++ locale character rules
- [ ] [#70](https://github.com/1298345095/BoostRegexRS/issues/70) **N12** — Implement MSVC C++ locale character rules
- [ ] [#71](https://github.com/1298345095/BoostRegexRS/issues/71) **V04** — Port the basic grammar and matching upstream family
- [ ] [#72](https://github.com/1298345095/BoostRegexRS/issues/72) **B14** — Complete specialized single-state repetition and its unwind
- [ ] [#73](https://github.com/1298345095/BoostRegexRS/issues/73) **B17** — Complete recursive subroutine calls and return backtracking
- [ ] [#74](https://github.com/1298345095/BoostRegexRS/issues/74) **U12** — Complete Windows ICU default-locale and imbue behavior
- [ ] [#75](https://github.com/1298345095/BoostRegexRS/issues/75) **U13** — Complete macOS ICU default-locale and imbue behavior
- [ ] [#76](https://github.com/1298345095/BoostRegexRS/issues/76) **U21** — Expose the callable production Unicode character-rule facade
- [ ] [#77](https://github.com/1298345095/BoostRegexRS/issues/77) **B18** — Complete conditional expressions and DEFINE blocks
- [ ] [#78](https://github.com/1298345095/BoostRegexRS/issues/78) **I02** — Implement the UTF-32 Unicode compile, search and capture adapter
- [ ] [#79](https://github.com/1298345095/BoostRegexRS/issues/79) **B19** — Complete PRUNE, SKIP, COMMIT and THEN unwind semantics
- [ ] [#80](https://github.com/1298345095/BoostRegexRS/issues/80) **I03** — Implement UTF-16 decoding and original-unit regex positions
- [ ] [#81](https://github.com/1298345095/BoostRegexRS/issues/81) **I04** — Implement UTF-8 Unicode regex APIs without losing original byte positions
- [ ] [#82](https://github.com/1298345095/BoostRegexRS/issues/82) **B20** — Complete ACCEPT and FAIL across lexical and recursive scopes
- [ ] [#83](https://github.com/1298345095/BoostRegexRS/issues/83) **B23** — Complete partial-match observation and publication
- [ ] [#84](https://github.com/1298345095/BoostRegexRS/issues/84) **B21** — Complete repeated capture histories on successful unwind
- [ ] [#85](https://github.com/1298345095/BoostRegexRS/issues/85) **B24** — Complete POSIX candidate selection and effective matching modes
- [ ] [#86](https://github.com/1298345095/BoostRegexRS/issues/86) **B25** — Complete compile outcome lifecycle, error mapping and option catalog
- [ ] [#87](https://github.com/1298345095/BoostRegexRS/issues/87) **B26** — Complete native capture and submatch query APIs
- [ ] [#88](https://github.com/1298345095/BoostRegexRS/issues/88) **B27** — Complete compiled byte regex lifecycle APIs
- [ ] [#89](https://github.com/1298345095/BoostRegexRS/issues/89) **B28** — Complete match iteration continuation and terminal behavior
- [ ] [#90](https://github.com/1298345095/BoostRegexRS/issues/90) **B30** — Add byte grep callbacks with source continuation and early stop
- [ ] [#91](https://github.com/1298345095/BoostRegexRS/issues/91) **B33** — Complete formatter dollar placeholders and capture lookup
- [ ] [#92](https://github.com/1298345095/BoostRegexRS/issues/92) **U22** — Integrate Unicode simple case into regex literals and backreferences
- [ ] [#93](https://github.com/1298345095/BoostRegexRS/issues/93) **U23** — Integrate Unicode classes, aliases and word boundaries through regex sets
- [ ] [#94](https://github.com/1298345095/BoostRegexRS/issues/94) **U24** — Implement exact Unicode line and combining-sequence operators
- [ ] [#95](https://github.com/1298345095/BoostRegexRS/issues/95) **U25** — Integrate locale-sensitive collating elements, ranges and equivalence sets
- [ ] [#96](https://github.com/1298345095/BoostRegexRS/issues/96) **R02** — Implement execution-work and engine-memory budget accounting
- [ ] [#97](https://github.com/1298345095/BoostRegexRS/issues/97) **B29** — Add source-compatible byte token iteration
- [ ] [#98](https://github.com/1298345095/BoostRegexRS/issues/98) **B31** — Add byte split results with capture mode and input consumption
- [ ] [#99](https://github.com/1298345095/BoostRegexRS/issues/99) **B35** — Complete format_all grouping and conditional evaluation
- [ ] [#100](https://github.com/1298345095/BoostRegexRS/issues/100) **B37** — Add native byte replacement callbacks
- [ ] [#101](https://github.com/1298345095/BoostRegexRS/issues/101) **B39** — Add a safe byte POSIX compile and error-status API
- [ ] [#102](https://github.com/1298345095/BoostRegexRS/issues/102) **B36** — Complete one-shot byte replacement and copy flags
- [ ] [#103](https://github.com/1298345095/BoostRegexRS/issues/103) **B40** — Add byte POSIX execution flags and bounded capture output
- [ ] [#104](https://github.com/1298345095/BoostRegexRS/issues/104) **P10** — Add the safe native-wide POSIX compile and execution API
- [ ] [#105](https://github.com/1298345095/BoostRegexRS/issues/105) **B38** — Add streaming byte format and replacement output
- [ ] [#106](https://github.com/1298345095/BoostRegexRS/issues/106) **I06** — Migrate replacement and iteration to UTF-32 inputs
- [ ] [#107](https://github.com/1298345095/BoostRegexRS/issues/107) **I07** — Migrate replacement and iteration to UTF-16 inputs
- [ ] [#108](https://github.com/1298345095/BoostRegexRS/issues/108) **I08** — Migrate replacement and iteration to UTF-8 inputs
- [ ] [#109](https://github.com/1298345095/BoostRegexRS/issues/109) **I09** — Migrate replacement and iteration to native-wide inputs
- [ ] [#110](https://github.com/1298345095/BoostRegexRS/issues/110) **R03** — Implement explicit output and match-count budgets for high-level operations
- [ ] [#111](https://github.com/1298345095/BoostRegexRS/issues/111) **I10** — Contract the input migration after byte and Unicode parity
- [ ] [#112](https://github.com/1298345095/BoostRegexRS/issues/112) **R04** — Preserve streaming output and terminal iterator errors on exhaustion
- [ ] [#113](https://github.com/1298345095/BoostRegexRS/issues/113) **U26** — Contract collation probe ownership into the production package
- [ ] [#114](https://github.com/1298345095/BoostRegexRS/issues/114) **V05** — Port advanced matching and malformed-pattern upstream regressions
- [ ] [#115](https://github.com/1298345095/BoostRegexRS/issues/115) **V06** — Port the result, capture and iteration upstream API family
- [ ] [#116](https://github.com/1298345095/BoostRegexRS/issues/116) **V07** — Port formatting, splitting and POSIX semantic upstream tests
- [ ] [#117](https://github.com/1298345095/BoostRegexRS/issues/117) **V09** — Port stress, overflow and resource upstream regressions
- [ ] [#118](https://github.com/1298345095/BoostRegexRS/issues/118) **P09** — Assemble the complete default standalone Rust package
- [ ] [#119](https://github.com/1298345095/BoostRegexRS/issues/119) **V08** — Port Unicode, locale and custom-traits upstream tests
- [ ] [#120](https://github.com/1298345095/BoostRegexRS/issues/120) **V14** — Run the deterministic byte grammar and option-interaction suite
- [ ] [#121](https://github.com/1298345095/BoostRegexRS/issues/121) **V10** — Resolve host-language and build-specific upstream applicability
- [ ] [#122](https://github.com/1298345095/BoostRegexRS/issues/122) **V15** — Run deterministic Unicode and locale behavior through the public regex API
- [ ] [#123](https://github.com/1298345095/BoostRegexRS/issues/123) **V16** — Run parser and diagnostic fuzzing with minimized regressions
- [ ] [#124](https://github.com/1298345095/BoostRegexRS/issues/124) **V17** — Run match and capture fuzzing with minimized regressions
- [ ] [#125](https://github.com/1298345095/BoostRegexRS/issues/125) **V18** — Run replacement and iteration fuzzing with minimized regressions
- [ ] [#126](https://github.com/1298345095/BoostRegexRS/issues/126) **V20** — Add a separate whole-library native-reference CI path
- [ ] [#127](https://github.com/1298345095/BoostRegexRS/issues/127) **V40** — Audit complete public API documentation and execute the assembled examples
- [ ] [#128](https://github.com/1298345095/BoostRegexRS/issues/128) **V41** — Complete source, data and dependency license attribution
- [ ] [#129](https://github.com/1298345095/BoostRegexRS/issues/129) **V11** — Close the upstream applicability and source-completeness audit
- [ ] [#130](https://github.com/1298345095/BoostRegexRS/issues/130) **V19** — Run Unicode, traits and data-boundary fuzzing with minimized regressions
- [ ] [#131](https://github.com/1298345095/BoostRegexRS/issues/131) **V21** — Accept the complete library on Windows Server 2025 x86-64 / MSVC
- [ ] [#132](https://github.com/1298345095/BoostRegexRS/issues/132) **V22** — Accept the complete library on Windows 11 ARM64 / MSVC
- [ ] [#133](https://github.com/1298345095/BoostRegexRS/issues/133) **V23** — Accept the complete library on Ubuntu 24.04 LTS x86-64 / glibc
- [ ] [#134](https://github.com/1298345095/BoostRegexRS/issues/134) **V24** — Accept the complete library on Ubuntu 24.04 LTS ARM64 / glibc
- [ ] [#135](https://github.com/1298345095/BoostRegexRS/issues/135) **V25** — Accept the complete library on macOS 15 Intel
- [ ] [#136](https://github.com/1298345095/BoostRegexRS/issues/136) **V26** — Accept the complete library on macOS 15 Apple Silicon
- [ ] [#137](https://github.com/1298345095/BoostRegexRS/issues/137) **V28** — Calibrate comparable engine working-memory measurement on Windows MSVC
- [ ] [#138](https://github.com/1298345095/BoostRegexRS/issues/138) **V29** — Calibrate comparable engine working-memory measurement on Linux glibc
- [ ] [#139](https://github.com/1298345095/BoostRegexRS/issues/139) **V30** — Calibrate comparable engine working-memory measurement on macOS
- [ ] [#140](https://github.com/1298345095/BoostRegexRS/issues/140) **V31** — Accept compilation time and working memory on all six native baselines
- [ ] [#141](https://github.com/1298345095/BoostRegexRS/issues/141) **V32** — Accept ordinary search time and working memory on all six native baselines
- [ ] [#142](https://github.com/1298345095/BoostRegexRS/issues/142) **V33** — Accept ordinary capture time and working memory on all six native baselines
- [ ] [#143](https://github.com/1298345095/BoostRegexRS/issues/143) **V34** — Accept ordinary replacement time and working memory on all six native baselines
- [ ] [#144](https://github.com/1298345095/BoostRegexRS/issues/144) **V35** — Accept complex syntax time and working memory on all six native baselines
- [ ] [#145](https://github.com/1298345095/BoostRegexRS/issues/145) **V36** — Accept Unicode and locale behavior time and working memory on all six native baselines
- [ ] [#146](https://github.com/1298345095/BoostRegexRS/issues/146) **V42** — Publish the final compatibility and reproduction documentation in the repository
- [ ] [#147](https://github.com/1298345095/BoostRegexRS/issues/147) **V43** — Accept a clean checkout and the assembled standalone package

## Reproduce the backlog audit

```sh
python3 -B tools/dev/assemble_ticket_backlog.py
python3 -B tools/dev/ticket_backlog.py check
python3 -B tools/dev/ticket_backlog.py render
```

The audit rejects missing ownership, unknown/cyclic dependencies, isolated tickets, duplicate publication IDs and any rendered ticket body that differs from its recorded publication hash. Ticket closure alone never promotes a capability to passed. A newly discovered mechanism or optimization needs a bounded linked blocker; the final gate stays open until the complete accepted contract is satisfied.
